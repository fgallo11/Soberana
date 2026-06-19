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
            tipo_total = 0
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
                if resp.status_code != 200:
                    log.warning("GFW %s (dataset=%s) HTTP %s: %s",
                                tipo, dataset, resp.status_code, resp.text[:200])
                    break
                data = resp.json()
                entries = data.get("entries", [])
                tipo_total += len(entries)
                if not entries:
                    api_total = data.get("total", "?")
                    log.info("GFW %s offset=%d: 0 entradas (total según API=%s)", tipo, offset, api_total)
                    break
                total += _guardar_eventos(eng, tipo, entries)
                if data.get("nextOffset") is None:
                    break
                offset = data["nextOffset"]
            log.info("GFW %s: %d entradas descargadas (dataset=%s, rango=%s→%s)",
                     tipo, tipo_total, dataset, desde, hasta)
            if tipo_total == 0:
                log.warning("GFW %s devolvió 0 eventos — token sin acceso o dataset incorrecto (esperado: %s)", tipo, dataset)
    log.info("eventos GFW ingeridos/actualizados total: %d", total)
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


def _sar_report(client, desde, hasta, filtro: str | None = None) -> list[dict]:
    """Una consulta al report de SAR (celdas agregadas). `filtro` opcional, p.ej.
    "matched = false" para detecciones SIN correlación AIS (buques dark)."""
    params = {
        "datasets[0]": "public-global-sar-presence:latest",
        "temporal-resolution": "DAILY",
        "spatial-resolution": "HIGH",
        "format": "JSON",
        "date-range": f"{desde},{hasta}",
    }
    if filtro:
        params["filters[0]"] = filtro
    resp = client.post("/4wings/report", params=params, json={"geojson": _region_geojson()})
    resp.raise_for_status()
    rows = []
    for entry in resp.json().get("entries", []):
        for _, celdas in entry.items():
            for row in celdas or []:
                if row.get("lat") is not None:
                    rows.append(row)
    return rows


def ingerir_sar(dias: int = 30) -> Path:
    """Detecciones SAR (Sentinel-1) → GeoJSON, separando las correlacionadas con
    AIS (matched) de las NO correlacionadas (dark). La correlación la calcula
    GFW contra AIS satelital. Si el filtro de GFW no estuviera disponible, se
    publican las detecciones SIN afirmar correlación (matched=null), para no
    etiquetar de forma engañosa.
    """
    hasta = utcnow().date()
    desde = hasta - timedelta(days=dias)
    with _client() as client:
        total = _sar_report(client, desde, hasta)
        try:
            dark = _sar_report(client, desde, hasta, "matched = 'false'")
            matched = _sar_report(client, desde, hasta, "matched = 'true'")
        except httpx.HTTPStatusError as exc:
            log.warning("filtro matched de SAR no aceptado (%s); publico sin correlación", exc)
            dark = matched = None

    def _feat(row, matched_val):
        return {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]},
            "properties": {
                "matched": matched_val,
                "detecciones": row.get("detections") or row.get("value"),
                "fecha": row.get("date"),
                "fuente": "GFW / Sentinel-1",
            },
        }

    # ¿el filtro realmente segmentó, o devolvió todo en ambos casos?
    filtro_ok = (
        dark is not None and matched is not None
        and not (len(dark) == len(matched) == len(total) and len(total) > 0)
    )
    if filtro_ok:
        features = [_feat(r, False) for r in dark] + [_feat(r, True) for r in matched]
        nota = None
    else:
        features = [_feat(r, None) for r in total]
        nota = "Correlación con AIS no disponible en esta corrida: se muestran las detecciones sin clasificar."

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
            "nota": nota,
        },
        "features": features,
    }, ensure_ascii=False))
    log.info("SAR: %d detecciones (dark=%s matched=%s, filtro_ok=%s) → %s",
             len(features), None if dark is None else len(dark),
             None if matched is None else len(matched), filtro_ok, out)
    return out


def _exportar_eventos_json() -> None:
    """Snapshot balanceado por tipo para el frontend en modo estático.
    Toma los N más recientes de cada tipo para que ningún tipo se coma el cupo."""
    from ..db import list_events
    POR_TIPO = 300
    tipos = list(EVENT_DATASETS.keys())
    vistos: set[str] = set()
    rows: list[dict] = []
    for tipo in tipos:
        for r in list_events(type_=tipo, limit=POR_TIPO):
            if r["id"] not in vistos:
                vistos.add(r["id"])
                rows.append(r)
    # también incluir eventos de otras fuentes (ais_gap_local, reaparicion, etc.)
    for r in list_events(limit=POR_TIPO):
        if r["id"] not in vistos:
            vistos.add(r["id"])
            rows.append(r)
    rows.sort(key=lambda r: r.get("started_at") or "", reverse=True)
    for r in rows:
        for k in ("started_at", "ended_at"):
            if r.get(k) is not None and hasattr(r[k], "isoformat"):
                r[k] = r[k].isoformat()
    out = Path(settings.data_dir) / "events.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    from collections import Counter
    conteo = dict(Counter(r.get("type") for r in rows))
    log.info("exportando events.json: %d eventos %s", len(rows), conteo)
    out.write_text(json.dumps({"generado": utcnow().isoformat(), "demo": False, "events": rows}, ensure_ascii=False, default=str))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    que = sys.argv[1] if len(sys.argv) > 1 else "todo"
    if que in ("eventos", "todo"):
        ingerir_eventos()
    if que in ("sar", "todo"):
        ingerir_sar()
