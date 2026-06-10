"""Capa de tierra propia (fallback del basemap) + territorio argentino.

Fuente: Natural Earth (dominio público), vía el repositorio oficial
nvkelso/natural-earth-vector. Genera dos archivos commiteados al repo:

- tierra.geojson: masas de tierra (50m) recortadas al área del mapa.
  Garantiza que el territorio SIEMPRE se vea, incluso si el servidor de
  vector tiles externo (OpenFreeMap) está caído o bloqueado.
- territorio_argentino.geojson: continente + Malvinas + Georgias y
  Sandwich del Sur (50m, unión), para tintar el territorio nacional
  conforme a la cartografía oficial argentina. La Antártida argentina ya
  tiene su propia capa (static_layers).

Uso: python -m soberana.ingest.tierra
"""

import json
import logging
from pathlib import Path

import httpx
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

from ..config import settings

log = logging.getLogger("soberana.tierra")

NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson"
# caja del mapa (coincide con LIMITES del frontend, con margen)
CAJA = box(-100.0, -86.0, -10.0, -5.0)
# territorios que la cartografía oficial argentina integra al país
# (códigos ISO de Natural Earth: Malvinas=FLK, Georgias/Sandwich=SGS)
ISOS_TERRITORIO = {"AR", "ARG", "FK", "FLK", "GS", "SGS"}


def _bajar(nombre: str) -> dict:
    r = httpx.get(f"{NE}/{nombre}.geojson", timeout=120, follow_redirects=True)
    r.raise_for_status()
    return r.json()


def generar(out_dir: str | None = None) -> list[Path]:
    out = Path(out_dir or settings.data_dir)
    out.mkdir(parents=True, exist_ok=True)
    escritos: list[Path] = []

    # --- tierra (50m, recortada y simplificada) ---
    land = _bajar("ne_50m_land")
    geoms = []
    for f in land["features"]:
        g = shape(f["geometry"])
        if g.intersects(CAJA):
            geoms.append(g.intersection(CAJA))
    tierra = unary_union(geoms).simplify(0.01)
    p = out / "tierra.geojson"
    p.write_text(json.dumps({
        "type": "FeatureCollection",
        "metadata": {
            "fuente": "Natural Earth 50m (dominio público)",
            "nota": "fallback de tierra: el territorio se ve aunque el basemap externo falle",
        },
        "features": [{"type": "Feature", "geometry": mapping(tierra), "properties": {}}],
    }))
    log.info("tierra: %.0f KB → %s", p.stat().st_size / 1024, p)
    escritos.append(p)

    # --- territorio argentino (continente + islas del Atlántico Sur) ---
    # 50m: la resolución 110m no incluye Georgias ni Sandwich del Sur
    paises = _bajar("ne_50m_admin_0_countries")
    partes = []
    for f in paises["features"]:
        props = f.get("properties", {})
        isos = {str(props.get(k, "")).upper() for k in ("ISO_A2", "ISO_A3", "ADM0_A3", "SOV_A3")}
        if isos & ISOS_TERRITORIO:
            partes.append(shape(f["geometry"]))
    if not partes:
        raise SystemExit("Natural Earth cambió su esquema de propiedades: revisar ISOs")
    territorio = unary_union(partes).simplify(0.02)
    p = out / "territorio_argentino.geojson"
    p.write_text(json.dumps({
        "type": "FeatureCollection",
        "metadata": {
            "fuente": "Natural Earth 110m (dominio público)",
            "nota": "continente + Malvinas + Georgias y Sandwich del Sur, conforme a la "
                    "cartografía oficial argentina; el Sector Antártico tiene capa propia",
        },
        "features": [{
            "type": "Feature",
            "geometry": mapping(territorio),
            "properties": {"nombre": "Territorio argentino (continental e insular)"},
        }],
    }, ensure_ascii=False))
    log.info("territorio: %.0f KB → %s", p.stat().st_size / 1024, p)
    escritos.append(p)
    return escritos


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for path in generar():
        print(f"✓ {path}")
