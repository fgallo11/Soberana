"""Puertos argentinos — fuente única para todo el sistema.

Antes había TRES listas hardcodeadas (static_layers, alturas, ais_live);
este módulo las unifica: genera `puertos.geojson` y expone `cargar_puertos()`
para que el resto del código lea siempre del mismo lugar.

Fuentes:
1. Dataset oficial "Puertos" de la Secretaría de Transporte (Dirección
   Nacional de Puertos) vía CKAN de datos.transporte.gob.ar — GeoJSON/CSV,
   licencia abierta. Corre en Actions (red abierta).
2. Fallback: lista curada embebida (21 puertos principales), que además
   completa el tipo (fluvial/marítimo) cuando la fuente oficial no lo trae.

Uso: python -m soberana.ingest.puertos
"""

import json
import logging
import unicodedata
from pathlib import Path

import httpx

from ..config import settings

log = logging.getLogger("soberana.puertos")

CKAN_PACKAGE = "https://datos.transporte.gob.ar/api/3/action/package_show?id=puertos"

# Lista curada: respaldo sin red y fuente de `tipo` (nombre, lon, lat, tipo)
PUERTOS_BASE = [
    ("Corrientes", -58.834, -27.469, "fluvial"), ("Barranqueras", -58.934, -27.486, "fluvial"),
    ("Goya", -59.264, -29.140, "fluvial"), ("Reconquista", -59.650, -29.150, "fluvial"),
    ("La Paz", -59.645, -30.745, "fluvial"), ("Santa Fe", -60.710, -31.633, "fluvial"),
    ("Paraná", -60.529, -31.732, "fluvial"), ("Diamante", -60.639, -32.066, "fluvial"),
    ("Rosario", -60.630, -32.947, "fluvial"), ("San Lorenzo/San Martín", -60.730, -32.720, "fluvial"),
    ("Timbúes", -60.710, -32.670, "fluvial"), ("San Nicolás", -60.210, -33.333, "fluvial"),
    ("Ramallo", -60.005, -33.486, "fluvial"), ("San Pedro", -59.665, -33.679, "fluvial"),
    ("Zárate", -59.028, -34.098, "fluvial"), ("Campana", -58.959, -34.158, "fluvial"),
    ("Buenos Aires", -58.370, -34.580, "fluvial"), ("Dock Sud", -58.350, -34.650, "fluvial"),
    ("La Plata", -57.880, -34.850, "fluvial"), ("Ibicuy", -59.157, -33.738, "fluvial"),
    # río Uruguay (margen argentina)
    ("Gualeguaychú", -58.516, -33.010, "fluvial"), ("Concepción del Uruguay", -58.230, -32.480, "fluvial"),
    ("Colón", -58.140, -32.220, "fluvial"), ("Concordia", -58.020, -31.390, "fluvial"),
    ("Bahía Blanca", -62.270, -38.790, "marítimo"), ("Quequén", -58.700, -38.580, "marítimo"),
    ("Mar del Plata", -57.530, -38.030, "marítimo"), ("Puerto Madryn", -65.030, -42.760, "marítimo"),
    ("Comodoro Rivadavia", -67.480, -45.860, "marítimo"), ("Puerto Deseado", -65.900, -47.750, "marítimo"),
    ("Punta Quilla", -68.420, -50.120, "marítimo"), ("Ushuaia", -68.300, -54.810, "marítimo"),
]


# Contexto por puerto (río + descripción), clave = nombre normalizado.
# Lo que importa para soberanía: qué se mueve y por qué importa.
CONTEXTO = {
    "ROSARIO": ("Río Paraná", "Núcleo del Gran Rosario, el mayor complejo agroexportador del país: "
                "por aquí sale buena parte de la soja y el maíz argentinos."),
    "SAN LORENZO/SAN MARTIN": ("Río Paraná", "Mayor polo de terminales graneleras y aceiteras de la Hidrovía."),
    "TIMBUES": ("Río Paraná", "Terminales agroexportadoras de última generación sobre el Paraná."),
    "SANTA FE": ("Río Paraná", "Puerto de ultramar más al norte de la Hidrovía troncal."),
    "BARRANQUERAS": ("Río Paraná", "Puerto del NEA, salida de la producción chaqueña."),
    "BUENOS AIRES": ("Río de la Plata", "Principal puerto de contenedores del país."),
    "LA PLATA": ("Río de la Plata", "Puerto con terminal de contenedores y polo petroquímico."),
    "BAHIA BLANCA": ("Mar Argentino", "Puerto de aguas profundas; granos, combustibles y futuro polo del GNL."),
    "CONCEPCION DEL URUGUAY": ("Río Uruguay", "Principal puerto argentino sobre el río Uruguay."),
    "CONCORDIA": ("Río Uruguay", "Puerto del litoral entrerriano sobre el río Uruguay."),
    "COLON": ("Río Uruguay", "Puerto y paso internacional sobre el río Uruguay."),
    "GUALEGUAYCHU": ("Río Gualeguaychú", "Puerto sobre el río Gualeguaychú, afluente del Uruguay."),
    "USHUAIA": ("Canal Beagle", "Puerto más austral del país; base de la proyección antártica y turística."),
    "PUERTO MADRYN": ("Golfo Nuevo", "Puerto de aguas profundas; aluminio, pesca y carga general."),
    "COMODORO RIVADAVIA": ("Mar Argentino", "Puerto petrolero de la cuenca del Golfo San Jorge."),
    "PUERTO DESEADO": ("Mar Argentino", "Puerto pesquero patagónico, base de la flota calamarera."),
    "MAR DEL PLATA": ("Mar Argentino", "Principal puerto pesquero del país."),
    "QUEQUEN": ("Mar Argentino", "Puerto granelero de aguas profundas del sudeste bonaerense."),
}


def _normalizar(nombre: str) -> str:
    s = unicodedata.normalize("NFD", nombre)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").upper().strip()


def _desde_ckan() -> list[dict]:
    r = httpx.get(CKAN_PACKAGE, timeout=60, follow_redirects=True)
    r.raise_for_status()
    recursos = r.json()["result"]["resources"]
    geo = next((x for x in recursos if "geojson" in (x.get("format", "") + x.get("url", "")).lower()), None)
    if geo is None:
        raise RuntimeError("el dataset oficial no expone GeoJSON")
    data = httpx.get(geo["url"], timeout=120, follow_redirects=True).json()
    tipos_base = {_normalizar(n): t for n, _, _, t in PUERTOS_BASE}
    puertos = []
    for f in data.get("features", []):
        g = f.get("geometry") or {}
        if g.get("type") != "Point":
            continue
        props = f.get("properties", {})
        nombre = (props.get("nombre") or props.get("puerto") or props.get("NOMBRE") or "").strip()
        if not nombre:
            continue
        lon, lat = g["coordinates"][0], g["coordinates"][1]
        puertos.append({
            "nombre": nombre, "lon": lon, "lat": lat,
            "tipo": tipos_base.get(_normalizar(nombre), props.get("tipo") or "puerto"),
            "fuente": "Dirección Nacional de Puertos (datos.transporte.gob.ar)",
        })
    if not puertos:
        raise RuntimeError("dataset oficial vacío o con esquema cambiado")
    return puertos


def generar(out_dir: str | None = None, fuente: str = "auto") -> Path:
    """fuente: auto (CKAN→curada) | ckan | curada"""
    out = Path(out_dir or settings.data_dir)
    out.mkdir(parents=True, exist_ok=True)
    puertos: list[dict] = []
    usada = fuente
    if fuente in ("auto", "ckan"):
        try:
            puertos = _desde_ckan()
            usada = "Dirección Nacional de Puertos (licencia abierta)"
        except Exception as exc:  # noqa: BLE001
            log.warning("fuente oficial de puertos falló (%s)", exc)
            if fuente == "ckan":
                raise
    if not puertos:
        usada = "lista curada (respaldo)"
        puertos = [{"nombre": n, "lon": lo, "lat": la, "tipo": t, "fuente": "curada"}
                   for n, lo, la, t in PUERTOS_BASE]

    p = out / "puertos.geojson"
    p.write_text(json.dumps({
        "type": "FeatureCollection",
        "metadata": {"fuente": usada, "descripcion": "Puertos argentinos — fuente única del sistema"},
        "features": [
            _puerto_feature(x, usada) for x in puertos
        ],
    }, ensure_ascii=False))
    log.info("puertos: %d (%s) → %s", len(puertos), usada, p)
    return p


def _puerto_feature(x: dict, fuente: str) -> dict:
    rio, desc = CONTEXTO.get(_normalizar(x["nombre"]), (None, None))
    props = {"nombre": x["nombre"], "tipo": x["tipo"], "fuente": x.get("fuente", fuente)}
    if rio:
        props["rio"] = rio
    if desc:
        props["descripcion"] = desc
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [round(x["lon"], 5), round(x["lat"], 5)]},
        "properties": props,
    }


def cargar_puertos(data_dir: str | None = None) -> list[tuple[str, float, float, str]]:
    """[(nombre, lat, lon, tipo)] desde el geojson generado; fallback curado.
    La usan alturas.py (georreferenciar) y ais_live.py (silenciar gaps en puerto)."""
    p = Path(data_dir or settings.data_dir) / "puertos.geojson"
    try:
        data = json.loads(p.read_text())
        out = [
            (f["properties"]["nombre"], f["geometry"]["coordinates"][1],
             f["geometry"]["coordinates"][0], f["properties"].get("tipo", "puerto"))
            for f in data.get("features", [])
            if f.get("geometry", {}).get("type") == "Point"
        ]
        if out:
            return out
    except (OSError, ValueError, KeyError):
        pass
    return [(n, la, lo, t) for n, lo, la, t in PUERTOS_BASE]


def indice_normalizado(data_dir: str | None = None) -> dict[str, tuple[float, float]]:
    """{NOMBRE_SIN_ACENTOS: (lat, lon)} — para matchear contra tablas oficiales
    (p. ej. las alturas de Prefectura, que vienen en mayúsculas sin tildes)."""
    return {_normalizar(n): (la, lo) for n, la, lo, _ in cargar_puertos(data_dir)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"✓ {generar()}")
