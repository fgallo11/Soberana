"""Extranjerización de tierras rurales por provincia.

Fuente: Registro Nacional de Tierras Rurales (RNTR), dato OFICIAL y PÚBLICO
del Estado argentino (argentina.gob.ar/justicia/tierrasrurales/datos). No
hace falta pedir permiso: es dato público. El Observatorio de Tierras y la
prensa lo difunden, pero el origen es el RNTR.

Contexto: la Ley 26.737 de Tierras Rurales fijaba un tope del 15% de
extranjerización por provincia y por departamento; fue derogada por el DNU
70/2023. A nivel nacional ~5-6% de la tierra rural (~13 millones de ha) está
en manos extranjeras, con departamentos que superan el 50% (San Carlos y
Molinos en Salta, Lácar en Neuquén).

Geometría: provincias de Natural Earth 10m (dominio público). Los porcentajes
provinciales son los de la última serie publicada por el RNTR; las provincias
sin valor confirmado quedan como `null` (sin dato) y pueden completarse desde
el RNTR (ver pestaña Colaborá).

Uso: python -m soberana.ingest.extranjerizacion
"""

import json
import logging
import unicodedata
from pathlib import Path

import httpx
from shapely.geometry import mapping, shape

from ..config import settings

log = logging.getLogger("soberana.extranjerizacion")

NE = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
      "geojson/ne_10m_admin_1_states_provinces.geojson")

# % de extranjerización por provincia (RNTR, última serie publicada).
# Solo se cargan los valores confirmados de fuentes públicas; el resto = null.
PORCENTAJES = {
    "SALTA": 11.56,
    "MISIONES": 11.07,
    "SAN JUAN": 10.48,
    "CORRIENTES": 9.87,
    "LA PAMPA": 2.39,
    "RIO NEGRO": 1.78,
    "SANTA FE": 1.70,
    "CORDOBA": 1.12,
}

# Departamentos "punto caliente" (superan ampliamente el ex tope del 15%).
# (nombre, lon, lat, pct, provincia)
DEPARTAMENTOS = [
    ("San Carlos", -66.08, -25.90, 59.8, "Salta"),
    ("Molinos", -66.28, -25.43, 57.7, "Salta"),
    ("Lácar", -71.35, -40.16, 54.0, "Neuquén"),
    ("Cushamen", -70.55, -42.18, 22.9, "Chubut"),
]


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").upper().strip()


def generar(out_dir: str | None = None) -> Path:
    out = Path(out_dir or settings.data_dir)
    out.mkdir(parents=True, exist_ok=True)

    r = httpx.get(NE, timeout=180, follow_redirects=True)
    r.raise_for_status()
    data = r.json()

    features = []
    for f in data["features"]:
        props = f.get("properties", {})
        if props.get("iso_a2") != "AR" and props.get("admin") != "Argentina":
            continue
        nombre = props.get("name") or ""
        pct = PORCENTAJES.get(_norm(nombre))
        geom = shape(f["geometry"]).simplify(0.02)
        features.append({
            "type": "Feature",
            "geometry": mapping(geom),
            "properties": {
                "nombre": nombre,
                "tipo": "provincia",
                "pct": pct,  # None = sin dato
                "descripcion": (
                    f"Extranjerización de tierras rurales: {pct}% de la superficie provincial en manos "
                    "extranjeras (Registro Nacional de Tierras Rurales)."
                    if pct is not None else
                    "Sin dato provincial cargado. El valor oficial está en el Registro Nacional de "
                    "Tierras Rurales y puede sumarse (ver pestaña Colaborá)."
                ),
                "fuente": "Registro Nacional de Tierras Rurales (dato oficial argentino)",
            },
        })

    # departamentos punto caliente (marcadores)
    for nombre, lon, lat, pct, prov in DEPARTAMENTOS:
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "nombre": f"Depto. {nombre} ({prov})",
                "tipo": "departamento",
                "pct": pct,
                "descripcion": (
                    f"{pct}% de las tierras del departamento en manos extranjeras — muy por encima del "
                    "tope del 15% que fijaba la ley 26.737 (derogada en 2023). Uno de los focos de "
                    "extranjerización más altos del país."
                ),
                "fuente": "Registro Nacional de Tierras Rurales (dato oficial argentino)",
            },
        })

    p = out / "extranjerizacion.geojson"
    p.write_text(json.dumps({
        "type": "FeatureCollection",
        "metadata": {
            "descripcion": "Extranjerización de tierras rurales por provincia (RNTR). "
                           "~5-6% nacional (~13 M ha). Ley 26.737 derogada por DNU 70/2023.",
            "fuente": "Registro Nacional de Tierras Rurales — argentina.gob.ar/justicia/tierrasrurales",
            "parcial": True,
        },
        "features": features,
    }, ensure_ascii=False))
    con_dato = sum(1 for f in features if f["properties"].get("pct") is not None and f["properties"]["tipo"] == "provincia")
    log.info("extranjerización: %d provincias (%d con dato) + %d deptos → %s",
             24, con_dato, len(DEPARTAMENTOS), p)
    return p


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"✓ {generar()}")
