"""Consumidor del websocket de aisstream.io + detector propio de gaps.

Es EL proceso persistente del sistema (corre en la VM, ver docs/despliegue.md).
- Inserta posiciones AIS del área costera/fluvial en la DB.
- Detector de gaps near real-time: si un buque que veníamos viendo deja de
  transmitir más de N minutos sin estar cerca de un puerto, se registra un
  evento `ais_gap_local` con confianza BAJA (la pérdida de señal terrestre
  tiene causas inocentes: sombra de cobertura, clima, antena). Cuando el
  buque reaparece, se registra la reaparición y se cierra el gap.

Uso: python -m soberana.ingest.ais_live
"""

import asyncio
import json
import logging
import math
from datetime import datetime, timezone

import websockets
from sqlalchemy.dialects import sqlite as _sqlite  # noqa: F401  (asegura dialecto en bundle)

from ..config import settings
from ..db import events, get_engine, init_db, positions, prune_positions, utcnow, vessels

log = logging.getLogger("soberana.ais")

# Puertos para silenciar falsas alarmas de gap (un buque amarrado apaga el AIS legítimamente)
PUERTOS = [
    ("Rosario", -32.94, -60.63),
    ("San Lorenzo/San Martín", -32.72, -60.73),
    ("Timbúes", -32.67, -60.71),
    ("Santa Fe", -31.65, -60.70),
    ("San Nicolás", -33.33, -60.21),
    ("Zárate", -34.09, -59.03),
    ("Campana", -34.16, -58.95),
    ("Buenos Aires", -34.58, -58.37),
    ("Dock Sud", -34.65, -58.35),
    ("La Plata", -34.85, -57.88),
    ("Bahía Blanca", -38.79, -62.27),
    ("Quequén", -38.58, -58.70),
    ("Mar del Plata", -38.03, -57.53),
    ("Barranqueras", -27.48, -58.93),
]

# Estado en memoria del detector: mmsi -> última posición/timestamp
_last_seen: dict[str, dict] = {}
_open_gaps: set[str] = set()


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _cerca_de_puerto(lat: float, lon: float) -> bool:
    return any(_km(lat, lon, plat, plon) <= settings.gap_radio_puerto_km for _, plat, plon in PUERTOS)


def _zona(lat: float, lon: float) -> str:
    if lon > -59.5 and lat > -35.5:
        return "hidrovia"
    return "costero"


async def consumir() -> None:
    if not settings.aisstream_api_key:
        raise SystemExit("Falta SOBERANA_AISSTREAM_API_KEY — pedila gratis en https://aisstream.io/")
    init_db()
    eng = get_engine()
    lon_min, lat_min, lon_max, lat_max = settings.bbox_ais_costero
    subscribe = {
        "APIKey": settings.aisstream_api_key,
        # aisstream usa [[lat, lon], [lat, lon]]
        "BoundingBoxes": [[[lat_min, lon_min], [lat_max, lon_max]]],
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
    }
    backoff = 2
    while True:
        try:
            async with websockets.connect("wss://stream.aisstream.io/v0/stream") as ws:
                await ws.send(json.dumps(subscribe))
                log.info("conectado a aisstream.io, bbox=%s", settings.bbox_ais_costero)
                backoff = 2
                ultimo_mantenimiento = utcnow()
                async for raw in ws:
                    msg = json.loads(raw)
                    _procesar(eng, msg)
                    if (utcnow() - ultimo_mantenimiento).total_seconds() > 120:
                        _detectar_gaps(eng)
                        prune_positions()
                        ultimo_mantenimiento = utcnow()
        except (websockets.WebSocketException, OSError) as exc:
            log.warning("websocket caído (%s); reintento en %ss", exc, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 300)


def _procesar(eng, msg: dict) -> None:
    tipo = msg.get("MessageType")
    meta = msg.get("MetaData", {})
    mmsi = str(meta.get("MMSI", ""))
    if not mmsi:
        return
    if tipo == "PositionReport":
        body = msg.get("Message", {}).get("PositionReport", {})
        lat, lon = body.get("Latitude"), body.get("Longitude")
        if lat is None or lon is None:
            return
        ts = utcnow()
        with eng.begin() as conn:
            conn.execute(
                positions.insert().values(
                    mmsi=mmsi, ts=ts, lat=lat, lon=lon,
                    sog=body.get("Sog"), cog=body.get("Cog"), src="aisstream",
                )
            )
        if mmsi in _open_gaps:
            _registrar_reaparicion(eng, mmsi, lat, lon, ts)
        _last_seen[mmsi] = {"ts": ts, "lat": lat, "lon": lon, "name": meta.get("ShipName", "").strip()}
    elif tipo == "ShipStaticData":
        body = msg.get("Message", {}).get("ShipStaticData", {})
        with eng.begin() as conn:
            existing = conn.execute(vessels.select().where(vessels.c.mmsi == mmsi)).first()
            values = {
                "name": (body.get("Name") or "").strip() or None,
                "callsign": (body.get("CallSign") or "").strip() or None,
                "updated_at": utcnow(),
            }
            if existing:
                conn.execute(vessels.update().where(vessels.c.mmsi == mmsi).values(**values))
            else:
                conn.execute(vessels.insert().values(mmsi=mmsi, **values))


def _detectar_gaps(eng) -> None:
    limite = settings.gap_minutos_silencio * 60
    ahora = utcnow()
    for mmsi, info in list(_last_seen.items()):
        if mmsi in _open_gaps:
            continue
        silencio = (ahora - info["ts"]).total_seconds()
        if silencio < limite:
            continue
        lat, lon = info["lat"], info["lon"]
        if _cerca_de_puerto(lat, lon):
            del _last_seen[mmsi]  # amarrado: caso inocente, no alarmar
            continue
        # ¿salió del área de cobertura? si el último contacto fue en el borde, no alarmar
        lon_min, lat_min, lon_max, lat_max = settings.bbox_ais_costero
        margen = 0.25
        if not (lon_min + margen < lon < lon_max - margen and lat_min + margen < lat < lat_max - margen):
            del _last_seen[mmsi]
            continue
        evento_id = f"local-gap-{mmsi}-{int(info['ts'].timestamp())}"
        with eng.begin() as conn:
            if conn.execute(events.select().where(events.c.id == evento_id)).first():
                continue
            conn.execute(
                events.insert().values(
                    id=evento_id, type="ais_gap_local", src="soberana", confidence="baja",
                    mmsi=mmsi, vessel_name=info.get("name") or None,
                    lat=lat, lon=lon, started_at=info["ts"], zone=_zona(lat, lon),
                    raw={"silencio_seg": int(silencio)},
                )
            )
        _open_gaps.add(mmsi)
        log.info("gap local: %s (%s) silencio=%dmin", mmsi, info.get("name"), silencio // 60)


def _registrar_reaparicion(eng, mmsi: str, lat: float, lon: float, ts: datetime) -> None:
    with eng.begin() as conn:
        abierto = conn.execute(
            events.select()
            .where(events.c.mmsi == mmsi, events.c.type == "ais_gap_local", events.c.ended_at.is_(None))
            .order_by(events.c.started_at.desc())
        ).first()
        if abierto:
            conn.execute(events.update().where(events.c.id == abierto.id).values(ended_at=ts))
    _open_gaps.discard(mmsi)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    asyncio.run(consumir())
