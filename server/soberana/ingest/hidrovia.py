"""Trazado real de la Hidrovía Paraná-Paraguay y del río Uruguay.

Reemplaza la polilínea a mano alzada de la v1 (21 vértices que cortaban
campo) por el curso real del río, con tres niveles de fuente:

1. OpenStreetMap vía Overpass (primaria, corre en Actions): relaciones
   waterway del Río Paraná, Río Paraguay y los brazos navegables del delta
   (Paraná de las Palmas, Guazú) + canales del Río de la Plata (Emilio
   Mitre, Punta Indio). Licencia ODbL, atribución ya presente en el mapa.
2. Natural Earth 10m rivers (fallback automático): meandros reales aunque
   menos detalle de brazos. Dominio público.
3. Constante curada (último recurso, sin red): la polilínea v1.

Produce `hidrovia.geojson` con:
- features de contexto: el curso de los ríos (tipo="curso")
- la TRONCAL: una LineString única y ordenada Corrientes → Recalada
  (tipo="troncal"), que usan la película demo y el resaltado del mapa.

La traza legal/balizada de la Vía Navegable Troncal (AGP) no se publica en
formato SIG; si algún día aparece, entra como fuente 0.

Uso: python -m soberana.ingest.hidrovia
"""

import json
import logging
import math
from pathlib import Path

import httpx

from ..config import settings

log = logging.getLogger("soberana.hidrovia")

NE_RIVERS = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_rivers_lake_centerlines.geojson"
OVERPASS = "https://overpass-api.de/api/interpreter"

# cuenca de interés (lon_min, lat_min, lon_max, lat_max): de Asunción a Recalada
CUENCA = (-62.0, -36.5, -54.0, -16.0)
CORRIENTES = (-58.83, -27.47)
# tramo estuarial (Río de la Plata): no es "río" en ninguna fuente de centerlines;
# el canal real (Emilio Mitre → Punta Indio → Recalada) viene de OSM cuando hay
# Overpass; este es el respaldo curado, que va sobre agua.
COLA_ESTUARIO = [
    (-58.40, -34.45), (-58.20, -34.55), (-57.50, -34.85),
    (-56.70, -35.05), (-56.42, -35.10), (-55.90, -35.35),
]

# Polilínea curada v1 — SOLO último recurso sin red (tests, contingencia)
TRONCAL_CURADA = [
    (-58.83, -27.47), (-58.80, -27.95), (-59.05, -28.50), (-59.26, -29.14),
    (-59.55, -29.70), (-59.63, -30.74), (-59.98, -31.23), (-60.70, -31.65),
    (-60.64, -32.07), (-60.70, -32.50), (-60.63, -32.95), (-60.21, -33.33),
    (-59.66, -33.68), (-59.03, -34.10), (-58.96, -34.16), (-58.50, -34.30),
] + COLA_ESTUARIO

OVERPASS_QUERY = """
[out:json][timeout:120];
(
  relation["waterway"="river"]["name"~"^Río Paraná$|^Río Paraguay$|^Río Uruguay$|Paraná de las Palmas|Paraná Guazú"]({lat_min},{lon_min},{lat_max},{lon_max});
  way["waterway"~"^(river|canal)$"]["name"~"Emilio Mitre|Punta Indio|Paraná de las Palmas"]({lat_min},{lon_min},{lat_max},{lon_max});
);
out geom;
"""


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _encadenar(segmentos: list[list[tuple[float, float]]], inicio: tuple[float, float],
               tope_salto: float = 0.35) -> list[tuple[float, float]]:
    """Encadena segmentos sueltos en UNA polilínea ordenada desde `inicio`.

    Greedy con regla de avance: arranca por el segmento con un extremo más
    cercano a `inicio` y anexa el segmento pendiente más cercano a la cola
    (invertido si hace falta) SOLO si su extremo lejano se aleja de `inicio`
    — eso descarta brazos paralelos/bifurcaciones que volverían hacia atrás.
    Corta cuando el salto supera `tope_salto` grados (~35 km).
    """
    pendientes = [list(s) for s in segmentos if len(s) >= 2]
    if not pendientes:
        return []
    mejor = min(pendientes, key=lambda s: min(_dist(s[0], inicio), _dist(s[-1], inicio)))
    pendientes.remove(mejor)
    if _dist(mejor[-1], inicio) < _dist(mejor[0], inicio):
        mejor.reverse()
    cadena = mejor
    while pendientes:
        cola = cadena[-1]
        cand = min(pendientes, key=lambda s: min(_dist(s[0], cola), _dist(s[-1], cola)))
        salto = min(_dist(cand[0], cola), _dist(cand[-1], cola))
        if salto > tope_salto:
            break
        pendientes.remove(cand)
        if _dist(cand[-1], cola) < _dist(cand[0], cola):
            cand.reverse()
        # regla de avance: el extremo lejano debe alejarse del inicio
        if _dist(cand[-1], inicio) < _dist(cola, inicio) - 0.05:
            continue  # brazo paralelo que retrocede: descartado
        cadena.extend(cand)
    return cadena


def _clip_bbox(coords: list[tuple[float, float]], bbox) -> list[list[tuple[float, float]]]:
    """Parte una polilínea en tramos que caen dentro del bbox."""
    lon_min, lat_min, lon_max, lat_max = bbox
    tramos: list[list[tuple[float, float]]] = []
    actual: list[tuple[float, float]] = []
    for lon, lat in coords:
        if lon_min <= lon <= lon_max and lat_min <= lat <= lat_max:
            actual.append((lon, lat))
        elif actual:
            tramos.append(actual)
            actual = []
    if actual:
        tramos.append(actual)
    return tramos


def _desde_overpass() -> tuple[list[dict], list[list[tuple[float, float]]]]:
    lon_min, lat_min, lon_max, lat_max = CUENCA
    q = OVERPASS_QUERY.format(lat_min=lat_min, lon_min=lon_min, lat_max=lat_max, lon_max=lon_max)
    r = httpx.post(OVERPASS, data={"data": q}, timeout=180)
    r.raise_for_status()
    data = r.json()
    cursos: list[dict] = []
    segmentos: list[list[tuple[float, float]]] = []
    for el in data.get("elements", []):
        nombre = (el.get("tags", {}) or {}).get("name", "")
        ways = []
        if el["type"] == "way" and el.get("geometry"):
            ways = [el["geometry"]]
        elif el["type"] == "relation":
            ways = [m.get("geometry") for m in el.get("members", [])
                    if m.get("type") == "way" and m.get("geometry")]
        for g in ways:
            coords = [(p["lon"], p["lat"]) for p in g]
            for tramo in _clip_bbox(coords, CUENCA):
                segmentos.append(tramo)
                cursos.append({"nombre": nombre, "coords": tramo})
    if not segmentos:
        raise RuntimeError("Overpass no devolvió geometría")
    return cursos, segmentos


def _desde_natural_earth() -> tuple[list[dict], list[list[tuple[float, float]]]]:
    r = httpx.get(NE_RIVERS, timeout=180, follow_redirects=True)
    r.raise_for_status()
    data = r.json()
    cursos: list[dict] = []
    segmentos: list[list[tuple[float, float]]] = []
    for f in data["features"]:
        nombre = f["properties"].get("name") or ""
        if not any(k in nombre for k in ("Paraná", "Parana", "Paraguay", "Paraguai", "Uruguay", "Uruguai")):
            continue
        if nombre in ("Paranaíba", "Paranapanema"):
            continue
        geom = f["geometry"]
        lineas = geom["coordinates"] if geom["type"] == "MultiLineString" else [geom["coordinates"]]
        for linea in lineas:
            coords = [(c[0], c[1]) for c in linea]
            for tramo in _clip_bbox(coords, CUENCA):
                cursos.append({"nombre": nombre, "coords": tramo})
                # para la troncal solo encadenamos el Paraná
                if "Paran" in nombre:
                    segmentos.append(tramo)
    if not segmentos:
        raise RuntimeError("Natural Earth no trajo el Paraná")
    return cursos, segmentos


def generar(out_dir: str | None = None, fuente: str = "auto") -> Path:
    """fuente: auto (Overpass→NE→curada) | overpass | ne | curada"""
    out = Path(out_dir or settings.data_dir)
    out.mkdir(parents=True, exist_ok=True)

    cursos: list[dict] = []
    segmentos: list[list[tuple[float, float]]] = []
    usada = fuente
    if fuente in ("auto", "overpass"):
        try:
            cursos, segmentos = _desde_overpass()
            usada = "OpenStreetMap (Overpass, ODbL)"
        except Exception as exc:  # noqa: BLE001 — cualquier falla pasa al fallback
            log.warning("Overpass falló (%s)", exc)
            if fuente == "overpass":
                raise
    if not segmentos and fuente in ("auto", "ne"):
        try:
            cursos, segmentos = _desde_natural_earth()
            usada = "Natural Earth 10m (dominio público)"
        except Exception as exc:  # noqa: BLE001
            log.warning("Natural Earth falló (%s)", exc)
            if fuente == "ne":
                raise
    if not segmentos:
        usada = "polilínea curada (último recurso — SIN meandros reales)"
        cursos, segmentos = [], [list(TRONCAL_CURADA)]

    # la troncal va de Corrientes al sur: solo segmentos enteramente aguas
    # abajo de la confluencia (el Paraguay y el Alto Paraná quedan de contexto)
    segs_troncal = [s for s in segmentos if max(s[0][1], s[-1][1]) <= CORRIENTES[1] + 0.2]
    if not segs_troncal:
        segs_troncal = segmentos
    troncal = _encadenar(segs_troncal, CORRIENTES)
    # empalmar el tramo estuarial si la cadena murió en el delta
    if troncal and _dist(troncal[-1], COLA_ESTUARIO[0]) < 1.2:
        troncal.extend(COLA_ESTUARIO)

    features = [
        {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[round(lo, 5), round(la, 5)] for lo, la in c["coords"]]},
            "properties": {
                "nombre": c["nombre"] or "curso de agua", "tipo": "curso",
                "descripcion": f"Curso del {c['nombre']}." if c["nombre"] else "Curso de agua navegable.",
                "fuente": usada,
            },
        }
        for c in cursos if len(c["coords"]) >= 2
    ]
    features.append({
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[round(lo, 5), round(la, 5)] for lo, la in troncal]},
        "properties": {
            "nombre": "Hidrovía — Vía Navegable Troncal",
            "tipo": "troncal",
            "descripcion": "Ruta navegable Corrientes → Recalada (~1.477 km). Por aquí sale cerca del "
                           "80% de las exportaciones argentinas. Administrada mediante peaje; la "
                           "soberanía sobre su dragado y control es una discusión estratégica abierta.",
            "fuente": usada,
        },
    })
    p = out / "hidrovia.geojson"
    p.write_text(json.dumps({
        "type": "FeatureCollection",
        "metadata": {"fuente": usada, "descripcion": "Curso real de la Hidrovía Paraná-Paraguay"},
        "features": features,
    }, ensure_ascii=False))
    log.info("hidrovia: %d cursos + troncal de %d pts (%s) → %s", len(features) - 1, len(troncal), usada, p)
    return p


def cargar_troncal(data_dir: str | None = None) -> list[tuple[float, float]]:
    """Polilínea troncal para la película demo: del geojson generado si existe,
    si no la curada (tests / primer arranque sin red)."""
    p = Path(data_dir or settings.data_dir) / "hidrovia.geojson"
    try:
        data = json.loads(p.read_text())
        for f in data.get("features", []):
            if f.get("properties", {}).get("tipo") == "troncal":
                coords = f["geometry"]["coordinates"]
                if len(coords) >= 2:
                    return [(c[0], c[1]) for c in coords]
    except (OSError, ValueError, KeyError):
        pass
    return list(TRONCAL_CURADA)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"✓ {generar()}")
