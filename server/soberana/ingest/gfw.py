"""Jobs batch contra la API v3 de Global Fishing Watch (corre en GitHub Actions).

- Eventos: gaps de AIS (apagado intencional, alta confianza según GFW),
  encuentros y loitering dentro de la ZEE ampliada → tabla `events` + JSON
  para el frontend en modo estático.
- Detecciones SAR: detecciones de Sentinel-1 (matched/dark) → GeoJSON.

Todo con delay de 72 hs (AIS) / ~5 días (SAR): el frontend lo declara.
Atribución obligatoria: los datos son de Global Fishing Watch.

Uso: python -m soberana.ingest.gfw [eventos|sar|todo]
"""

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from ..config import settings
from ..db import events, get_engine, init_db, utcnow

log = logging.getLogger("soberana.gfw")
BASE = "https://gateway.api.globalfishingwatch.org/v3"

EVENT_DATASETS = {
    "ais_gap_gfw": "public-global-gaps-events:latest",
    "encounter": "public-global-encounters-events:latest",
    "loitering": "public-global-loitering-events:latest",
}

# Región de interés: ZEE + borde milla 201 (GeoJSON simple, el fino lo hace GFW)
def _region_geojson() -> dict:
    lon_min, lat_min, lon_max, lat_max = settings.bbox_zee
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon_min, lat_min], [lon_max, lat_min],
            [lon_max, lat_max], [lon_min, lat_max], [lon_min, lat_min],
        ]],
    }


def _client() -> httpx.Client:
    if not settings.gfw_api_token:
        raise SystemExit("Falta SOBERANA_GFW_API_TOKEN — pedilo gratis en https://globalfishingwatch.org/our-apis/")
    return httpx.Client(
        base_url=BASE,
        headers={"Authorization": f"Bearer {settings.gfw_api_token}"},
        timeout=60,
    )


def ingerir_eventos(dias: int = 30) -> int:
    """Descarga eventos de los últimos `dias` y los upserta (id estable de GFW)."""
    init_db()
    eng = get_engine()
    hasta = utcnow().date()
    desde = hasta - timedelta(days=dias)
    total = 0
    with _client() as client:
        for tipo, dataset in EVENT_DATASETS.items():
            offset = 0
            while True:
                resp = client.post(
                    "/events",
                    params={"offset": offset, "limit": 500},
                    json={
                        "datasets": [dataset],
                        "startDate": str(desde),
                        "endDate": str(hasta),
                        "geometry": _region_geojson(),
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                entries = data.get("entries", [])
                if not entries:
                    break
                total += _guardar_eventos(eng, tipo, entries)
                if data.get("nextOffset") is None:
                    break
                offset = data["nextOffset"]
    log.info("eventos GFW ingeridos/actualizados: %d", total)
    _exportar_eventos_json()
    return total


def _a_datetime(valor) -> datetime | None:
    """GFW devuelve fechas como ISO 8601 (str) o epoch en milisegundos (int).
    SQLite/SQLAlchemy necesitan un objeto datetime, no un string."""
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return datetime.fromtimestamp(valor / 1000, tz=timezone.utc)
    if isinstance(valor, str):
        try:
            return datetime.fromisoformat(valor.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _guardar_eventos(eng, tipo: str, entries: list[dict]) -> int:
    n = 0
    with eng.begin() as conn:
        for e in entries:
            eid = f"gfw-{e['id']}"
            if conn.execute(events.select().where(events.c.id == eid)).first():
                continue
            pos = e.get("position", {})
            vessel = e.get("vessel", {})
            conn.execute(
                events.insert().values(
                    id=eid,
                    type=tipo,
                    src="gfw",
                    confidence="alta" if tipo == "ais_gap_gfw" else "media",
                    mmsi=str(vessel.get("ssvid") or ""),
                    vessel_name=vessel.get("name"),
                    flag=vessel.get("flag"),
                    lat=pos.get("lat"),
                    lon=pos.get("lon"),
                    started_at=_a_datetime(e.get("start")),
                    ended_at=_a_datetime(e.get("end")),
                    zone="ZEE",
                    raw=e,
                )
            )
            n += 1
    return n


def ingerir_sar(dias: int = 30) -> Path:
    """Detecciones SAR (Sentinel-1) vía 4Wings report → GeoJSON para el frontend.

    Cada feature trae `matched` (correlacionada con AIS) — las no matcheadas
    son los buques *dark*. La capa se rotula 'detección no correlacionada
    con AIS', nunca 'buque ilegal'.

    Resolución temporal DIARIA: cada detección lleva su fecha, que es lo
    que permite la barra de tiempo del frontend (ventana de 30 días).
    """
    hasta = utcnow().date()
    desde = hasta - timedelta(days=dias)
    with _client() as client:
        resp = client.post(
            "/4wings/report",
            params={
                "datasets[0]": "public-global-sar-presence:latest",
                "temporal-resolution": "DAILY",
                "spatial-resolution": "HIGH",
                "format": "JSON",
                "date-range": f"{desde},{hasta}",
            },
            json={"geojson": _region_geojson()},
        )
        resp.raise_for_status()
        data = resp.json()

    features = []
    for entry in data.get("entries", []):
        for _, rows in entry.items():
            for row in rows or []:
                if row.get("lat") is None:
                    continue
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]},
                    "properties": {
                        "detecciones": row.get("detections") or row.get("value"),
                        "fecha": row.get("date"),
                        "fuente": "GFW / Sentinel-1",
                    },
                })
    out = Path(settings.data_dir) / "sar_detections.geojson"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "type": "FeatureCollection",
        "metadata": {
            "fuente": "Global Fishing Watch — SAR vessel detections (Sentinel-1)",
            "atribucion": "Global Fishing Watch",
            "generado": utcnow().isoformat(),
            "ventana_dias": dias,
            "demo": False,
        },
        "features": features,
    }, ensure_ascii=False))
    log.info("SAR: %d detecciones → %s", len(features), out)
    return out


def _exportar_eventos_json() -> None:
    """Snapshot del log de eventos para el frontend en modo estático."""
    from ..db import list_events
    rows = list_events(limit=500)
    for r in rows:
        for k in ("started_at", "ended_at"):
            if r.get(k) is not None and hasattr(r[k], "isoformat"):
                r[k] = r[k].isoformat()
    out = Path(settings.data_dir) / "events.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"generado": utcnow().isoformat(), "demo": False, "events": rows}, ensure_ascii=False, default=str))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    que = sys.argv[1] if len(sys.argv) > 1 else "todo"
    if que in ("eventos", "todo"):
        ingerir_eventos()
    if que in ("sar", "todo"):
        ingerir_sar()
