"""Esquema y acceso a datos.

Decisión deliberada (ver PLAN.md §4): lat/lon como columnas double + índices,
sin tipos PostGIS, para que el mismo código corra en sqlite (dev/tests),
Supabase free y Postgres en la VM. Las operaciones espaciales finas
(buffers, clipping) viven en los jobs de ingesta con shapely, no en la DB.
"""

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    func,
    select,
)

from .config import settings

metadata = MetaData()

# Última posición conocida + histórico corto de posiciones AIS
positions = Table(
    "positions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("mmsi", String(16), nullable=False),
    Column("ts", DateTime(timezone=True), nullable=False),
    Column("lat", Float, nullable=False),
    Column("lon", Float, nullable=False),
    Column("sog", Float),       # velocidad (nudos)
    Column("cog", Float),       # rumbo
    Column("src", String(32), default="aisstream"),
    Index("ix_positions_mmsi_ts", "mmsi", "ts"),
    Index("ix_positions_ts", "ts"),
)

# Identidad de buques (de mensajes AIS tipo 5 y de la API de vessels de GFW)
vessels = Table(
    "vessels",
    metadata,
    Column("mmsi", String(16), primary_key=True),
    Column("name", String(128)),
    Column("callsign", String(16)),
    Column("flag", String(8)),
    Column("ship_type", String(64)),
    Column("updated_at", DateTime(timezone=True)),
)

# Log de eventos: la memoria del proyecto. Nunca se borra.
events = Table(
    "events",
    metadata,
    Column("id", String(64), primary_key=True),  # id estable => ingesta idempotente
    Column("type", String(32), nullable=False),  # ais_gap_gfw | ais_gap_local | encounter | loitering | reaparicion
    Column("src", String(32), nullable=False),   # gfw | soberana
    Column("confidence", String(16), nullable=False),  # alta | media | baja
    Column("mmsi", String(16)),
    Column("vessel_name", String(128)),
    Column("flag", String(8)),
    Column("lat", Float),
    Column("lon", Float),
    Column("started_at", DateTime(timezone=True)),
    Column("ended_at", DateTime(timezone=True)),
    Column("zone", String(64)),                  # ZEE | milla_201 | FICZ | hidrovia | costero
    Column("demo", Boolean, default=False),
    Column("raw", JSON),
    Index("ix_events_started", "started_at"),
    Index("ix_events_type", "type"),
)

# Snapshot del tráfico aéreo (se pisa en cada poll; el histórico aéreo no se retiene en MVP)
aircraft = Table(
    "aircraft",
    metadata,
    Column("hex", String(8), primary_key=True),
    Column("ts", DateTime(timezone=True), nullable=False),
    Column("lat", Float),
    Column("lon", Float),
    Column("alt_ft", Float),
    Column("gs_kt", Float),
    Column("track", Float),
    Column("callsign", String(16)),
    Column("reg", String(16)),
    Column("type", String(8)),
    Column("mil", Boolean, default=False),
)

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        url = settings.database_url
        kwargs = {}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(url, pool_pre_ping=True, **kwargs)
    return _engine


def init_db() -> None:
    metadata.create_all(get_engine())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def latest_positions(bbox=None, max_age_min: int = 60, at: datetime | None = None) -> list[dict]:
    """Última posición de cada buque en la ventana de `max_age_min` minutos.

    `at` permite viajar en el tiempo: posiciones "como se veían" a ese
    instante (dentro de la retención hot de la DB). None = ahora.
    """
    eng = get_engine()
    fin = at or utcnow()
    cutoff = fin - timedelta(minutes=max_age_min)
    with eng.connect() as conn:
        sub = (
            select(positions.c.mmsi, func.max(positions.c.ts).label("ts"))
            .where(positions.c.ts >= cutoff, positions.c.ts <= fin)
            .group_by(positions.c.mmsi)
            .subquery()
        )
        q = (
            select(positions, vessels.c.name, vessels.c.flag, vessels.c.ship_type)
            .join(sub, (positions.c.mmsi == sub.c.mmsi) & (positions.c.ts == sub.c.ts))
            .outerjoin(vessels, vessels.c.mmsi == positions.c.mmsi)
        )
        rows = conn.execute(q).mappings().all()
    out = []
    for r in rows:
        if bbox and not (bbox[0] <= r["lon"] <= bbox[2] and bbox[1] <= r["lat"] <= bbox[3]):
            continue
        out.append(dict(r))
    return out


def vessel_track(mmsi: str, hours: int = 48) -> list[dict]:
    eng = get_engine()
    cutoff = utcnow() - timedelta(hours=hours)
    with eng.connect() as conn:
        q = (
            select(positions)
            .where(positions.c.mmsi == mmsi, positions.c.ts >= cutoff)
            .order_by(positions.c.ts)
        )
        return [dict(r) for r in conn.execute(q).mappings().all()]


def list_events(type_: str | None = None, zone: str | None = None, limit: int = 200) -> list[dict]:
    eng = get_engine()
    with eng.connect() as conn:
        q = select(events).order_by(events.c.started_at.desc()).limit(min(limit, 1000))
        if type_:
            q = q.where(events.c.type == type_)
        if zone:
            q = q.where(events.c.zone == zone)
        rows = [dict(r) for r in conn.execute(q).mappings().all()]
    for r in rows:
        if isinstance(r.get("raw"), str):
            try:
                r["raw"] = json.loads(r["raw"])
            except (TypeError, ValueError):
                pass
    return rows


def prune_positions() -> int:
    """Retención hot: borra posiciones más viejas que la ventana configurada.
    El histórico completo vive en el archivo frío (parquet en R2), no acá."""
    eng = get_engine()
    cutoff = utcnow() - timedelta(days=settings.posiciones_retencion_dias)
    with eng.begin() as conn:
        res = conn.execute(delete(positions).where(positions.c.ts < cutoff))
        return res.rowcount or 0


def day_tracks(fecha: datetime, step_min: int = 10) -> dict:
    """Recorridos de todos los buques durante un día calendario (UTC),
    submuestreados a un punto por buque cada `step_min` minutos.

    Alimenta la 'película' del frontend: puntos [[minuto_del_día, lon, lat]]
    por buque, que el cliente interpola para mostrar movimiento fluido.
    """
    eng = get_engine()
    inicio = fecha.replace(hour=0, minute=0, second=0, microsecond=0)
    fin = inicio + timedelta(days=1)
    buques: dict[str, dict] = {}
    with eng.connect() as conn:
        q = (
            select(positions.c.mmsi, positions.c.ts, positions.c.lat, positions.c.lon,
                   vessels.c.name, vessels.c.flag)
            .outerjoin(vessels, vessels.c.mmsi == positions.c.mmsi)
            .where(positions.c.ts >= inicio, positions.c.ts < fin)
            .order_by(positions.c.mmsi, positions.c.ts)
        )
        for r in conn.execute(q).mappings():
            b = buques.setdefault(r["mmsi"], {"name": r["name"], "flag": r["flag"], "pts": []})
            minuto = (r["ts"] - inicio).total_seconds() / 60.0
            # submuestreo: un punto por bucket de step_min
            if b["pts"] and minuto - b["pts"][-1][0] < step_min:
                continue
            b["pts"].append([round(minuto, 1), round(r["lon"], 5), round(r["lat"], 5)])
    return buques
