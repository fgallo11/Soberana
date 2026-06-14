"""Generador de capas estáticas de contexto y soberanía.

IMPORTANTE — precisión: las geometrías de ZEE, FOCZ y AMPs generadas acá son
APROXIMADAS (buffer geodésico sobre una costa simplificada, rectángulos).
Sirven para que el mapa funcione desde el día 1 y cada feature lleva
`aproximado: true`. El job de Actions con red abierta debe reemplazarlas por
las fuentes de referencia:
  - ZEE:     Marine Regions (VLIZ), https://marineregions.org/ (mrgid Argentina)
  - Límites: geoservicios del IGN, https://www.ign.gob.ar/
  - AMPs:    Sistema Nacional de Áreas Marinas Protegidas
La FICZ sí responde a su definición publicada (círculo de 150 mn centrado en
51°40'S 59°30'W). Las bases militares y puertos son puntos de conocimiento
público (coordenadas aproximadas al km).

Uso: python -m soberana.ingest.static_layers
"""

import json
import math
from pathlib import Path

from shapely.geometry import Point, Polygon, mapping
from shapely.ops import unary_union

from ..config import settings

NM = 1.852  # km por milla náutica
R_TIERRA = 6371.0


def _destino(lat: float, lon: float, rumbo_deg: float, dist_km: float) -> tuple[float, float]:
    """Punto destino geodésico (fórmula esférica)."""
    br = math.radians(rumbo_deg)
    d = dist_km / R_TIERRA
    la1, lo1 = math.radians(lat), math.radians(lon)
    la2 = math.asin(math.sin(la1) * math.cos(d) + math.cos(la1) * math.sin(d) * math.cos(br))
    lo2 = lo1 + math.atan2(
        math.sin(br) * math.sin(d) * math.cos(la1),
        math.cos(d) - math.sin(la1) * math.sin(la2),
    )
    return math.degrees(la2), math.degrees(lo2)


def circulo_geodesico(lat: float, lon: float, radio_km: float, n: int = 90) -> Polygon:
    return Polygon(
        [(lo, la) for la, lo in (_destino(lat, lon, b * 360 / n, radio_km) for b in range(n + 1))]
    )


# Costa argentina simplificada (cabos salientes, N→S) + puntos en Malvinas
# (la ZEE argentina reclamada incluye las islas)
COSTA = [
    (-56.70, -36.30), (-57.50, -38.05), (-58.70, -38.60), (-60.90, -38.98),
    (-62.10, -39.00), (-62.25, -40.80), (-63.75, -42.08), (-63.63, -42.77),
    (-64.95, -42.70), (-65.20, -43.60), (-65.50, -44.90), (-65.75, -47.20),
    (-65.90, -47.75), (-66.00, -48.10), (-67.55, -49.30), (-68.30, -50.10),
    (-69.00, -51.55), (-68.35, -52.33), (-68.40, -52.90), (-67.60, -53.80),
    (-66.70, -54.30), (-65.20, -54.90), (-64.30, -54.85), (-63.80, -54.75),
]
COSTA_MALVINAS = [
    (-61.30, -51.40), (-60.20, -51.00), (-58.80, -51.25), (-57.75, -51.55),
    (-58.20, -52.20), (-59.40, -52.30), (-60.90, -52.10),
]

BASES_MILITARES = [
    # nombre, lon, lat, fuerza, pais, nota
    ("BFSAI Mount Pleasant (aérea)", -58.447, -51.823, "Royal Air Force", "Reino Unido",
     "Base militar extranjera en territorio argentino ocupado (Malvinas). Núcleo de las Fuerzas "
     "Británicas del Atlántico Sur (BFSAI): ~1.300 a 1.700 efectivos de Ejército, Royal Navy y RAF, "
     "más ~40 voluntarios de la Falkland Islands Defence Force. Aire: 4 cazas Eurofighter Typhoon "
     "FGR4 (Escuadrón Nº 1435) en alerta permanente, 1 avión cisterna Voyager y 1 transporte A400M "
     "Atlas (Escuadrón Nº 1312). Defensa aérea: misiles Sky Sabre (reemplazaron a los Rapier en 2022). "
     "Pista inaugurada en 1985. (Datos de fuentes públicas: RAF, Forces News, MercoPress.)"),
    ("Mare Harbour / East Cove (naval)", -58.430, -51.900, "Royal Navy", "Reino Unido",
     "Puerto militar extranjero en territorio argentino ocupado (Malvinas). Base naval de la Royal "
     "Navy en las islas: un buque patrullero guardián permanente (clase River, p. ej. HMS Forth o "
     "HMS Medway en rotación) más el apoyo de un buque de la Royal Fleet Auxiliary. Sostiene "
     "logísticamente a la guarnición de Mount Pleasant. (Fuentes públicas: Royal Navy, UK Def. Journal.)"),
    ("Base Naval Puerto Belgrano", -62.103, -38.894, "Armada Argentina", "Argentina",
     "Principal base naval del país"),
    ("Base Aeronaval Comandante Espora", -62.169, -38.725, "Armada Argentina", "Argentina",
     "Principal base de la aviación naval argentina, junto a Puerto Belgrano."),
    ("Base Naval Mar del Plata", -57.531, -38.034, "Armada Argentina", "Argentina",
     "Apostadero de la fuerza de submarinos. Desde aquí zarpó el ARA San Juan en 2017."),
    ("Base Naval Ushuaia / Polo Logístico Antártico", -68.297, -54.819, "Armada Argentina", "Argentina",
     "Base naval más austral del país y futura Base Naval Integrada / Polo Logístico Antártico (el "
     "puerto operativo más cercano a la Antártida). Proyecto de la Armada Argentina con fuerte "
     "interés estratégico de Estados Unidos: en 2024 fue visitada por la entonces jefa del Comando "
     "Sur de EE.UU. No es una base estadounidense; la soberanía y operación son argentinas."),
    ("Estación Espacio Lejano (China)", -70.1495, -38.1914, "CLTC (organismo civil-militar chino)", "China",
     "NO es una base militar con efectivos: es una estación CIENTÍFICA de rastreo de espacio profundo "
     "(antena de 35 m) que apoya el programa lunar chino, operada por personal técnico. Bajada del Agrio "
     "(Neuquén): 200 hectáreas cedidas por ~50 años, operativa desde 2017. La preocupación de soberanía "
     "no son tropas sino el OPERADOR —la CLTC, que controla satélites para el Ejército Popular de "
     "Liberación— sumado al escaso control argentino del sitio y a su potencial uso dual. Único enclave "
     "de una potencia extranjera en el territorio continental argentino."),
    ("Base Aeronaval Almirante Quijada (Río Grande)", -67.750, -53.778, "Armada Argentina", "Argentina",
     "Base aeronaval en Tierra del Fuego, clave en la vigilancia del Atlántico Sur."),
    ("BAM Río Gallegos", -69.312, -51.609, "Fuerza Aérea Argentina", "Argentina",
     "Base aérea militar; durante 1982 fue base de operaciones hacia Malvinas."),
    ("IX Brigada Aérea (Comodoro Rivadavia)", -67.466, -45.785, "Fuerza Aérea Argentina", "Argentina",
     "Brigada aérea de la Patagonia central."),
    ("VI Brigada Aérea (Tandil)", -59.250, -37.237, "Fuerza Aérea Argentina", "Argentina",
     "Asiento de los cazas interceptores de la Fuerza Aérea."),
]

# NOTA: los puertos y la traza de la Hidrovía se mudaron a sus propios jobs
# con fuentes reales (puertos.py: dataset oficial de la Dirección Nacional de
# Puertos; hidrovia.py: OSM vía Overpass / Natural Earth).

# Sector Antártico Argentino: entre los meridianos 25°O y 74°O al sur del
# paralelo 60°S (recortado en 85°S por el límite de la proyección web mercator)
SECTOR_ANTARTICO = [(-74.0, -60.0), (-25.0, -60.0), (-25.0, -85.0), (-74.0, -85.0), (-74.0, -60.0)]

ISLAS_ATLANTICO_SUR = [
    ("Islas Malvinas", -58.90, -51.80,
     "Archipiélago argentino bajo ocupación británica desde 1833 (~3.600 habitantes). "
     "La ONU reconoce la disputa de soberanía: la Resolución 2065 (1965) la definió como "
     "una cuestión a resolver por negociación bilateral entre Argentina y el Reino Unido —no "
     "un caso de libre determinación—; la Resolución 3160 (1973) instó a acelerar las "
     "negociaciones; y la 31/49 (1976) pidió a las partes no introducir modificaciones "
     "unilaterales mientras la disputa siga pendiente. El Comité de Descolonización lo reitera cada año."),
    ("Islas Georgias del Sur", -36.50, -54.30,
     "Bajo administración británica y reclamadas por Argentina; comprendidas en la disputa de "
     "soberanía reconocida por la ONU (Res. 2065 y subsiguientes). Sin población permanente salvo "
     "la estación de Grytviken. Aguas de altísima riqueza pesquera (kril, austromerluza)."),
    ("Islas Sandwich del Sur", -26.50, -57.80,
     "Archipiélago volcánico deshabitado, bajo administración británica y reclamado por Argentina; "
     "incluido en la disputa de soberanía reconocida por la ONU (Res. 2065 y subsiguientes)."),
    ("Islas Orcadas del Sur", -45.40, -60.60,
     "Dentro del Sector Antártico Argentino. Sede de la Base Orcadas, la base antártica "
     "permanente más antigua del mundo (1904)."),
    ("Islas Shetland del Sur", -58.50, -62.10,
     "Archipiélago antártico con la mayor concentración de bases científicas del mundo "
     "(argentinas, chilenas, china, rusa, brasileña, etc.)."),
]

# Bases antárticas y asentamientos en las islas (conocimiento público,
# coordenadas aproximadas al km): nombre, lon, lat, país, nota
BASES_ANTARTICAS = [
    # --- argentinas permanentes ---
    ("Base Orcadas", -44.74, -60.74, "Argentina",
     "La base antártica permanente más antigua del mundo (1904) — Islas Orcadas del Sur"),
    ("Base Marambio", -56.62, -64.24, "Argentina", "Pista aérea principal del sector — isla Marambio"),
    ("Base Esperanza", -56.98, -63.40, "Argentina", "Base con población civil permanente"),
    ("Base Carlini", -58.67, -62.24, "Argentina", "Investigación científica — isla 25 de Mayo"),
    ("Base San Martín", -67.10, -68.13, "Argentina", ""),
    ("Base Belgrano II", -34.62, -77.87, "Argentina", "La base argentina más austral"),
    ("Base Petrel", -56.28, -63.47, "Argentina", "En reactivación como polo logístico"),
    # --- extranjeras dentro del Sector Antártico Argentino ---
    ("Rothera (Reino Unido)", -68.13, -67.57, "Reino Unido", "Principal base británica del sector"),
    ("Halley VI (Reino Unido)", -26.57, -75.57, "Reino Unido", ""),
    ("O'Higgins (Chile)", -57.90, -63.32, "Chile", ""),
    ("Frei / Villa Las Estrellas (Chile)", -58.96, -62.20, "Chile", "Base con población civil"),
    ("Gran Muralla (China)", -58.96, -62.22, "China", ""),
    ("Bellingshausen (Rusia)", -58.97, -62.20, "Rusia", ""),
    ("Comandante Ferraz (Brasil)", -58.39, -62.08, "Brasil", ""),
    # --- asentamientos en las islas del Atlántico Sur ---
    ("Puerto Argentino", -57.85, -51.69, "Reino Unido",
     "Capital de las Islas Malvinas, bajo ocupación británica (los británicos lo llaman Stanley)"),
    ("Grytviken / King Edward Point", -36.51, -54.28, "Reino Unido",
     "Estación administrada por el Reino Unido — Islas Georgias del Sur"),
]

def _fc(features: list[dict], **metadata) -> dict:
    return {"type": "FeatureCollection", "metadata": metadata, "features": features}


def _feature(geom, **props) -> dict:
    return {"type": "Feature", "geometry": mapping(geom), "properties": props}


def generar(out_dir: str | None = None) -> list[Path]:
    out = Path(out_dir or settings.data_dir)
    out.mkdir(parents=True, exist_ok=True)
    escritos: list[Path] = []

    # --- ZEE aproximada: unión de círculos geodésicos de 200 mn sobre la costa ---
    circulos = [circulo_geodesico(lat, lon, 200 * NM) for lon, lat in COSTA + COSTA_MALVINAS]
    zee = unary_union(circulos)
    # recorte norte aproximado (límite lateral con Uruguay) y simplificación
    zee = zee.intersection(Polygon([(-70, -58.8), (-48, -58.8), (-48, -34.8), (-70, -34.8)]))
    zee = zee.simplify(0.05)
    borde = zee.boundary  # la "milla 200": el borde exterior es la línea que importa

    zee_fc = _fc(
        [
            _feature(zee, nombre="ZEE Argentina (aproximada)", aproximado=True,
                     descripcion="Zona Económica Exclusiva: hasta 200 millas náuticas desde la línea de "
                                 "base. Argentina tiene derechos soberanos sobre los recursos vivos y "
                                 "minerales. Es la zona que la flota extranjera explota desde el borde.",
                     fuente="Geometría aproximada (buffer geodésico); referencia: CONVEMAR / Marine Regions / IGN"),
            _feature(borde, nombre="Límite de las 200 millas", tipo="milla_200", aproximado=True,
                     descripcion="El borde exterior de la ZEE. Justo afuera (la 'milla 201') la flota "
                                 "pesquera extranjera se estaciona para pescar sin licencia argentina.",
                     fuente="Geometría aproximada"),
        ],
        descripcion="Zona Económica Exclusiva argentina",
        aproximado=True,
    )
    p = out / "zee.geojson"
    p.write_text(json.dumps(zee_fc))
    escritos.append(p)

    # --- FICZ (definición publicada: 150 mn centradas en 51°40'S 59°30'W) y FOCZ (aprox) ---
    ficz = circulo_geodesico(-51.667, -59.5, 150 * NM)
    focz = circulo_geodesico(-51.667, -59.5, 200 * NM).difference(ficz).simplify(0.02)
    p = out / "ficz_focz.geojson"
    p.write_text(json.dumps(_fc([
        _feature(ficz, nombre="FICZ — Zona de Conservación de las Malvinas",
                 descripcion="Zona de pesca que la administración británica de las islas declara y "
                             "licencia a buques extranjeros, dentro de aguas que Argentina reclama como "
                             "propias. La venta de licencias es la principal fuente de ingresos de la ocupación.",
                 detalle="Círculo de 150 mn centrado en 51°40'S 59°30'W",
                 fuente="Definición publicada (FICZ); geometría según radio oficial",
                 aproximado=False),
        _feature(focz, nombre="FOCZ — Zona Exterior de Conservación (aprox.)",
                 descripcion="Extensión exterior de la zona pesquera administrada desde las islas, "
                             "hasta unas 200 mn. El límite real sigue líneas medias.",
                 fuente="Geometría aproximada",
                 aproximado=True),
    ], descripcion="Zonas de licencias pesqueras emitidas por la administración de las Islas Malvinas")))
    escritos.append(p)

    # --- Áreas marinas protegidas + Agujero Azul (rectángulos aproximados) ---
    amps = [
        _feature(Polygon([(-61.4, -54.7), (-56.6, -54.7), (-56.6, -53.6), (-61.4, -53.6), (-61.4, -54.7)]),
                 nombre="AMP Namuncurá – Banco Burdwood", tipo="AMP", aproximado=True,
                 descripcion="Área Marina Protegida sobre una meseta submarina de altísima biodiversidad. "
                             "Creada por ley para proteger el fondo marino de la pesca de arrastre.",
                 fuente="Sistema Nacional de Áreas Marinas Protegidas (geometría aproximada)"),
        _feature(Polygon([(-68.5, -57.2), (-65.0, -57.2), (-65.0, -55.2), (-68.5, -55.2), (-68.5, -57.2)]),
                 nombre="AMP Yaganes", tipo="AMP", aproximado=True,
                 descripcion="Área Marina Protegida al sur de Tierra del Fuego, en la confluencia de los "
                             "océanos Atlántico y Pacífico. Zona de paso de especies migratorias.",
                 fuente="Sistema Nacional de Áreas Marinas Protegidas (geometría aproximada)"),
        _feature(Polygon([(-61.5, -47.5), (-58.0, -47.5), (-58.0, -43.5), (-61.5, -43.5), (-61.5, -47.5)]),
                 nombre="Agujero Azul", tipo="area_interes", aproximado=True,
                 descripcion="Sector del talud continental más allá de las 200 millas, sobre la "
                             "plataforma extendida argentina. Es donde se concentra la flota pesquera "
                             "extranjera (potera y arrastrera) que opera sin control.",
                 fuente="Zona de interés (geometría aproximada)"),
    ]
    p = out / "amps.geojson"
    p.write_text(json.dumps(_fc(amps, descripcion="Áreas marinas protegidas y zonas de interés — geometrías aproximadas")))
    escritos.append(p)

    # --- Antártida Argentina e islas del Atlántico Sur ---
    p = out / "antartida.geojson"
    p.write_text(json.dumps(_fc(
        [
            _feature(Polygon(SECTOR_ANTARTICO),
                     nombre="Sector Antártico Argentino", tipo="sector",
                     descripcion="Porción de la Antártida reclamada por Argentina: entre los meridianos "
                                 "25°O y 74°O, al sur del paralelo 60°S. El Tratado Antártico (1959) "
                                 "congela los reclamos pero no los anula. Argentina mantiene presencia "
                                 "permanente desde 1904.",
                     detalle="Recortado en 85°S por la proyección del mapa",
                     fuente="Cartografía oficial argentina"),
            _feature(Point(-49.5, -74.0), nombre="ANTÁRTIDA ARGENTINA", tipo="etiqueta"),
            *[
                _feature(Point(lon, lat), nombre=n, tipo="isla", descripcion=desc,
                         fuente="Cartografía y marco ONU: fuentes oficiales argentinas (Cancillería / IGN)")
                for n, lon, lat, desc in ISLAS_ATLANTICO_SUR
            ],
            *[
                _feature(Point(lon, lat), nombre=n, tipo="base", pais=pais,
                         descripcion=nota, argentina=(pais == "Argentina"),
                         fuente="Conocimiento público (ubicación aproximada)")
                for n, lon, lat, pais, nota in BASES_ANTARTICAS
            ],
        ],
        descripcion="Sector Antártico Argentino, islas del Atlántico Sur, bases antárticas "
                     "y asentamientos (cartografía oficial argentina; coordenadas aproximadas)",
    ), ensure_ascii=False))
    escritos.append(p)

    # --- Bases militares ---
    p = out / "bases_militares.geojson"
    p.write_text(json.dumps(_fc([
        _feature(Point(lon, lat), nombre=n, fuerza=f, pais=pa, descripcion=nota,
                 extranjera=(pa != "Argentina"),
                 fuente="Conocimiento público (ubicación aproximada)")
        for n, lon, lat, f, pa, nota in BASES_MILITARES
    ], descripcion="Instalaciones militares de conocimiento público (coordenadas aproximadas)"), ensure_ascii=False))
    escritos.append(p)

    return escritos


if __name__ == "__main__":
    for path in generar():
        print(f"✓ {path}")
