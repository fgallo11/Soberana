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

    # --- tierra (10m: resolución necesaria para que las islas chicas del
    #     Atlántico Sur y la Antártida —Laurie/Orcadas, Shetland, Marambio—
    #     se dibujen y los puntos no floten en el agua) ---
    land = _bajar("ne_10m_land")
    geoms = []
    for f in land["features"]:
        g = shape(f["geometry"])
        if g.intersects(CAJA):
            geoms.append(g.intersection(CAJA))
    tierra_full = unary_union(geoms)
    # tolerancia fina (~0.005° ≈ 500 m) para conservar las islas chicas
    tierra = tierra_full.simplify(0.005)
    p = out / "tierra.geojson"
    p.write_text(json.dumps({
        "type": "FeatureCollection",
        "metadata": {
            "fuente": "Natural Earth 10m (dominio público)",
            "nota": "fallback de tierra: el territorio se ve aunque el basemap externo falle",
        },
        "features": [{"type": "Feature", "geometry": mapping(tierra), "properties": {}}],
    }))
    log.info("tierra: %.0f KB → %s", p.stat().st_size / 1024, p)
    escritos.append(p)

    # --- territorios argentinos bajo control británico (se pintan en ROJO) ---
    # Malvinas, Georgias del Sur y Sandwich del Sur: administradas de hecho por
    # el Reino Unido y reclamadas por Argentina. Se extrae la silueta real de la
    # tierra (misma fuente que el verde) recortando por la zona de cada
    # archipiélago, que en mar abierto solo contiene esas islas.
    OCUPADOS = {
        "Islas Malvinas": box(-61.5, -53.1, -57.5, -50.8),
        "Islas Georgias del Sur": box(-38.6, -55.5, -35.0, -53.5),
        "Islas Sandwich del Sur": box(-28.8, -60.0, -25.5, -56.0),
    }
    MARCO_ONU = (
        "La ONU reconoce la disputa de soberanía: Resolución 2065 (1965) —cuestión a resolver por "
        "negociación bilateral, no de libre determinación—, 3160 (1973) —acelerar negociaciones— y "
        "31/49 (1976) —no innovar unilateralmente—. El Comité de Descolonización lo reitera cada año."
    )
    feats_ocupados = []
    for nombre, caja in OCUPADOS.items():
        isla = tierra_full.intersection(caja)
        if not isla.is_empty:
            feats_ocupados.append({
                "type": "Feature",
                "geometry": mapping(isla.simplify(0.004)),
                "properties": {
                    "nombre": nombre,
                    "estado": "Territorio argentino bajo ocupación británica",
                    "marco_onu": MARCO_ONU,
                },
            })
    p = out / "territorios_ocupados.geojson"
    p.write_text(json.dumps({
        "type": "FeatureCollection",
        "metadata": {
            "fuente": "Natural Earth 10m (dominio público)",
            "nota": "Territorios argentinos administrados de hecho por el Reino Unido; "
                    "se resaltan en rojo. Reclamados por Argentina (disputa de soberanía reconocida por la ONU).",
        },
        "features": feats_ocupados,
    }, ensure_ascii=False))
    log.info("territorios ocupados: %d → %s", len(feats_ocupados), p)
    escritos.append(p)

    # --- territorio argentino (continente + islas del Atlántico Sur) ---
    # 10m: alta resolución, coincide con la costa de la capa de tierra
    paises = _bajar("ne_10m_admin_0_countries")
    partes = []
    for f in paises["features"]:
        props = f.get("properties", {})
        isos = {str(props.get(k, "")).upper() for k in ("ISO_A2", "ISO_A3", "ADM0_A3", "SOV_A3")}
        if isos & ISOS_TERRITORIO:
            partes.append(shape(f["geometry"]))
    if not partes:
        raise SystemExit("Natural Earth cambió su esquema de propiedades: revisar ISOs")
    territorio = unary_union(partes).simplify(0.008)
    p = out / "territorio_argentino.geojson"
    p.write_text(json.dumps({
        "type": "FeatureCollection",
        "metadata": {
            "fuente": "Natural Earth 10m (dominio público)",
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
