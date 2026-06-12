"""API pública de Soberana.

Corre en la VM (único proceso persistente junto con la ingesta AIS).
Detrás de Cloudflare: los endpoints declaran Cache-Control para que el CDN
absorba el tráfico de lectura. El token de GFW jamás llega al navegador:
las capas de GFW se sirven proxiadas por acá.
"""

import time
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from .. import __version__
from ..config import settings
from ..db import day_tracks, init_db, latest_positions, list_events, utcnow, vessel_track

app = FastAPI(title="Soberana API", version=__version__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["GET"],
    allow_headers=["*"],
)

GFW_TILE_BASE = "https://gateway.api.globalfishingwatch.org/v3/4wings/tile/heatmap"
# Capas 4Wings habilitadas para proxy (id público -> dataset GFW)
GFW_LAYERS = {
    "pesca": "public-global-fishing-effort:latest",
    "sar": "public-global-sar-presence:latest",
    "presencia": "public-global-presence:latest",
}

_aircraft_cache: dict = {"ts": 0.0, "data": None}


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "version": __version__,
        "now": utcnow().isoformat(),
        "fuentes": {
            "gfw": bool(settings.gfw_api_token),
            "aisstream": bool(settings.aisstream_api_key),
            "viirs": bool(settings.eog_username),
            "adsb": True,  # adsb.lol no requiere token
        },
    }


@app.get("/api/vessels")
def vessels_geojson(
    response: Response,
    bbox: str | None = Query(None, description="lon_min,lat_min,lon_max,lat_max"),
    max_age_min: int = Query(60, le=24 * 60),
    at: str | None = Query(None, description="ISO datetime: posiciones a ese instante (archivo)"),
):
    """Última posición conocida de cada buque (GeoJSON). Fuente: AIS terrestre.
    Con `at`, devuelve el estado histórico dentro de la retención de la DB."""
    box = None
    if bbox:
        try:
            box = tuple(float(x) for x in bbox.split(","))
            assert len(box) == 4
        except (ValueError, AssertionError):
            raise HTTPException(400, "bbox inválido: se espera lon_min,lat_min,lon_max,lat_max")
    instante = None
    if at:
        try:
            instante = datetime.fromisoformat(at.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(400, "at inválido: se espera ISO 8601")
    rows = latest_positions(bbox=box, max_age_min=max_age_min, at=instante)
    response.headers["Cache-Control"] = "public, max-age=300" if at else "public, max-age=30"
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
                "properties": {
                    "mmsi": r["mmsi"],
                    "name": r.get("name"),
                    "flag": r.get("flag"),
                    "ship_type": r.get("ship_type"),
                    "sog": r.get("sog"),
                    "cog": r.get("cog"),
                    "ts": r["ts"].isoformat() if r.get("ts") else None,
                },
            }
            for r in rows
        ],
    }


@app.get("/api/replay")
def replay(response: Response, fecha: str, step_min: int = Query(10, ge=1, le=60)):
    """La 'película' de un día: recorridos AIS de todos los buques en ese día
    calendario (UTC). `step_min` controla el submuestreo (default 10 min):
    es una decisión de tamaño de respuesta NUESTRA, no un límite de la
    fuente — el AIS llega cada pocos segundos y la DB guarda todo; con
    step_min=1 la película sale con resolución de 1 minuto. El frontend
    interpola entre puntos. Limitado por la retención hot."""
    try:
        dia = datetime.fromisoformat(fecha)
    except ValueError:
        raise HTTPException(400, "fecha inválida: se espera YYYY-MM-DD")
    response.headers["Cache-Control"] = "public, max-age=600"
    return {"fecha": fecha, "demo": False, "step_min": step_min, "buques": day_tracks(dia, step_min=step_min)}


@app.get("/api/vessels/{mmsi}/track")
def track(mmsi: str, hours: int = Query(48, le=14 * 24)):
    pts = vessel_track(mmsi, hours=hours)
    if not pts:
        raise HTTPException(404, "sin posiciones recientes para ese MMSI")
    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [[p["lon"], p["lat"]] for p in pts],
        },
        "properties": {"mmsi": mmsi, "desde": pts[0]["ts"].isoformat(), "hasta": pts[-1]["ts"].isoformat()},
    }


@app.get("/api/events")
def events_list(
    response: Response,
    type: str | None = None,
    zone: str | None = None,
    limit: int = Query(200, le=1000),
):
    """Log de eventos: apagones de AIS (GFW + detector propio), encuentros, loitering.
    El log es permanente — es la memoria del proyecto."""
    response.headers["Cache-Control"] = "public, max-age=300"
    rows = list_events(type_=type, zone=zone, limit=limit)
    for r in rows:
        for k in ("started_at", "ended_at"):
            if r.get(k) is not None and hasattr(r[k], "isoformat"):
                r[k] = r[k].isoformat()
    return {"count": len(rows), "events": rows}


@app.get("/api/aircraft")
async def aircraft_live(response: Response):
    """Tráfico aéreo en el área de interés, con flag militar.
    Fuente: adsb.lol (comunitaria, sin filtrar, sin token). Cache 15 s para
    que N usuarios del mapa generen 1 request upstream."""
    now = time.monotonic()
    if _aircraft_cache["data"] is not None and now - _aircraft_cache["ts"] < 15:
        response.headers["Cache-Control"] = "public, max-age=15"
        return _aircraft_cache["data"]

    lon_min, lat_min, lon_max, lat_max = settings.bbox_aereo
    lat_c, lon_c = (lat_min + lat_max) / 2, (lon_min + lon_max) / 2
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # punto + radio amplio (nm) cubre el bbox; /v2/mil agrega militares fuera del área
            r1 = await client.get(f"https://api.adsb.lol/v2/point/{lat_c}/{lon_c}/250")
            r2 = await client.get("https://api.adsb.lol/v2/mil")
            r1.raise_for_status()
            r2.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(503, f"adsb.lol no disponible: {exc}") from exc

    seen: dict[str, dict] = {}
    for ac in r1.json().get("ac", []):
        if ac.get("lat") is None:
            continue
        seen[ac.get("hex", "")] = _aircraft_feature(ac, mil=bool(ac.get("dbFlags", 0) & 1))
    for ac in r2.json().get("ac", []):
        lat, lon = ac.get("lat"), ac.get("lon")
        if lat is None or lon is None:
            continue
        if lon_min <= lon <= lon_max and lat_min <= lat <= lat_max:
            seen[ac.get("hex", "")] = _aircraft_feature(ac, mil=True)

    data = {"type": "FeatureCollection", "features": list(seen.values())}
    _aircraft_cache.update(ts=now, data=data)
    response.headers["Cache-Control"] = "public, max-age=15"
    return data


def _aircraft_feature(ac: dict, mil: bool) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [ac.get("lon"), ac.get("lat")]},
        "properties": {
            "hex": ac.get("hex"),
            "callsign": (ac.get("flight") or "").strip(),
            "reg": ac.get("r"),
            "type": ac.get("t"),
            "alt_ft": ac.get("alt_baro"),
            "gs_kt": ac.get("gs"),
            "track": ac.get("track"),
            "mil": mil,
        },
    }


@app.get("/api/tiles/gfw/{layer}/{z}/{x}/{y}.png")
async def gfw_tile(
    layer: str, z: int, x: int, y: int,
    interval: str = "30days",
    desde: str | None = None,
    hasta: str | None = None,
):
    """Proxy autenticado a los tiles 4Wings de GFW (el token vive solo acá).
    `desde`/`hasta` (YYYY-MM-DD) permiten pedir el heatmap de un período
    pasado — la barra de tiempo del frontend los usa. Cache largo en CDN."""
    if layer not in GFW_LAYERS:
        raise HTTPException(404, f"capa desconocida; disponibles: {list(GFW_LAYERS)}")
    if not settings.gfw_api_token:
        raise HTTPException(503, "GFW no configurado en este despliegue (falta SOBERANA_GFW_API_TOKEN)")
    params = {
        "format": "PNG",
        "interval": interval,
        "datasets[0]": GFW_LAYERS[layer],
    }
    if desde and hasta:
        params["date-range"] = f"{desde},{hasta}"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            f"{GFW_TILE_BASE}/{z}/{x}/{y}",
            params=params,
            headers={"Authorization": f"Bearer {settings.gfw_api_token}"},
        )
    if r.status_code != 200:
        raise HTTPException(r.status_code, "error upstream de GFW")
    return Response(
        content=r.content,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )
