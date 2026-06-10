"""VIIRS Boat Detection (VBD) — luces nocturnas de barcos.

La flota potera pesca con lámparas de miles de watts: VIIRS la ve aunque
apague el AIS. Producto diario del Earth Observation Group (Colorado School
of Mines), gratuito con registro: https://eogdata.mines.edu/products/vbd/

El acceso programático usa el endpoint de descarga de EOG con autenticación
(usuario/clave del registro). Limitaciones del sensor que el frontend declara:
solo de noche, lo degradan las nubes y la luna llena, no identifica buques.

Uso: python -m soberana.ingest.viirs
"""

import csv
import io
import json
import logging
from datetime import timedelta
from pathlib import Path

import httpx

from ..config import settings
from ..db import utcnow

log = logging.getLogger("soberana.viirs")

# Mosaico que cubre el Atlántico Sur en la grilla de VBD de EOG
EOG_TOKEN_URL = "https://eogauth.mines.edu/auth/realms/master/protocol/openid-connect/token"
EOG_VBD_URL = "https://eogdata.mines.edu/wwwdata/viirs_products/vbd/v23/global-saa/nrt"


def _token(client: httpx.Client) -> str:
    resp = client.post(
        EOG_TOKEN_URL,
        data={
            "client_id": "eogdata_oidc",
            "grant_type": "password",
            "username": settings.eog_username,
            "password": settings.eog_password,
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def ingerir(dias: int = 3) -> Path:
    """Baja los CSV diarios de VBD recientes y filtra al área de interés."""
    if not settings.eog_username:
        raise SystemExit("Faltan SOBERANA_EOG_USERNAME/PASSWORD — registro gratis en https://eogdata.mines.edu/")
    lon_min, lat_min, lon_max, lat_max = settings.bbox_zee
    features: list[dict] = []
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        token = _token(client)
        headers = {"Authorization": f"Bearer {token}"}
        for d in range(1, dias + 1):
            fecha = (utcnow() - timedelta(days=d)).strftime("%Y%m%d")
            url = f"{EOG_VBD_URL}/VBD_npp_d{fecha}_global-saa_noaa_ops_v23.csv"
            try:
                resp = client.get(url, headers=headers)
                if resp.status_code != 200:
                    log.warning("VBD %s: HTTP %s (puede no estar publicado aún)", fecha, resp.status_code)
                    continue
            except httpx.HTTPError as exc:
                log.warning("VBD %s: %s", fecha, exc)
                continue
            for row in csv.DictReader(io.StringIO(resp.text)):
                try:
                    lat, lon = float(row["Lat_DNB"]), float(row["Lon_DNB"])
                except (KeyError, ValueError):
                    continue
                if not (lon_min <= lon <= lon_max and lat_min <= lat <= lat_max):
                    continue
                # QF_Detect 1 = detección fuerte de barco; descartar ruido y gas flares
                if row.get("QF_Detect") not in ("1", "2", "3"):
                    continue
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {
                        "fecha": fecha,
                        "qf": row.get("QF_Detect"),
                        "radiancia": row.get("Rad_DNB"),
                    },
                })
    out = Path(settings.data_dir) / "viirs_boats.geojson"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "type": "FeatureCollection",
        "metadata": {
            "fuente": "VIIRS Boat Detection — Earth Observation Group, Colorado School of Mines / NOAA",
            "generado": utcnow().isoformat(),
            "ventana_dias": dias,
            "demo": False,
        },
        "features": features,
    }, ensure_ascii=False))
    log.info("VIIRS: %d detecciones → %s", len(features), out)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingerir()
