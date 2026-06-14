"""Presencia extranjera en infraestructura crítica argentina.

Relevo curado a partir de material público (prensa y organismos argentinos:
BCR, La Nación, Infobae, elDiarioAR, Dialogue Earth, EconoJournal). Cubre
cuatro categorías donde el control, la operación o el financiamiento de
infraestructura estratégica está en manos extranjeras:

  - litio   : proyectos del Triángulo del Litio (NOA) y sus operadores
  - represa : grandes hidroeléctricas con construcción/financiamiento chino
  - cable   : punto de amarre de cables submarinos (infraestructura digital)
  - puerto  : terminales de la Hidrovía operadas por traders extranjeros

Coordenadas APROXIMADAS (centro del salar / sitio de obra / localidad);
los salares son extensos. Cada ficha cita su fuente.

Uso: python -m soberana.ingest.infraestructura
"""

import json
import logging
from pathlib import Path

from ..config import settings

log = logging.getLogger("soberana.infraestructura")

# (nombre, lon, lat, categoria, tipo_legible, pais, descripcion, fuente)
INFRAESTRUCTURA = [
    # ----------------- LITIO (Triángulo del Litio, NOA) -----------------
    ("Cauchari-Olaroz", -66.72, -23.65, "litio", "Litio", "China / Canadá",
     "Mina de litio en operación. Controlada por la china Ganfeng Lithium (~51%) junto a Lithium "
     "Americas y la estatal jujeña JEMSE. Uno de los mayores proyectos de litio del país.",
     "Prensa argentina / Dialogue Earth"),
    ("Sales de Jujuy — Salar de Olaroz", -66.72, -23.42, "litio", "Litio", "Australia / Japón",
     "Mina de litio en operación. Operada por Arcadium Lithium (ex Allkem, Australia) con Toyota "
     "Tsusho (Japón) y JEMSE.",
     "Prensa argentina / BCR"),
    ("Fénix — Salar del Hombre Muerto", -66.95, -25.40, "litio", "Litio", "Estados Unidos",
     "Mina de litio en operación desde los años 90. Operada por Arcadium Lithium (ex Livent, EE.UU.). "
     "Una de las productoras históricas de litio del país.",
     "Prensa argentina / Dialogue Earth"),
    ("Sal de Vida — Salar del Hombre Muerto", -66.92, -25.52, "litio", "Litio", "Australia / EE.UU.",
     "Proyecto de litio de Arcadium Lithium (ex Galaxy/Allkem) en el mismo salar que Fénix.",
     "Prensa argentina"),
    ("Tres Quebradas (3Q)", -68.55, -27.35, "litio", "Litio", "China",
     "Proyecto de litio controlado por la china Zijin Mining (compró Liex/Neo Lithium). "
     "Catamarca, zona de Fiambalá.",
     "Prensa argentina / Dialogue Earth"),
    ("Centenario-Ratones", -67.05, -24.95, "litio", "Litio", "Francia / China",
     "Mina de litio. Sociedad de la francesa Eramet con la china Tsingshan. Salta.",
     "Prensa argentina"),
    ("Mariana — Salar de Llullaillaco", -68.22, -25.00, "litio", "Litio", "China",
     "Proyecto de litio de la china Ganfeng Lithium (inversión ~US$580 M). Salta, depto. Los Andes.",
     "Prensa argentina"),
    # ----------------- MINERÍA (oro/cobre, operadores extranjeros) -----------------
    ("Veladero", -69.92, -29.33, "mineria", "Mina de oro", "Canadá / China",
     "Una de las mayores minas de oro del país (Iglesia, San Juan, en plena cordillera). Operada en "
     "sociedad 50/50 por la canadiense Barrick Gold y la estatal china Shandong Gold (que compró el "
     "50% en 2017). En zona de glaciares y nacientes de agua.",
     "Prensa argentina / Letra P"),
    ("MARA — Bajo de la Alumbrera / Agua Rica", -66.62, -27.33, "mineria", "Mina de cobre y oro", "Suiza / EE.UU.",
     "Proyecto cuprífero MARA (Andalgalá, Catamarca). Controlado por capitales extranjeros: Glencore "
     "(Suiza, 25%) y Newmont (EE.UU.), entre otros. Históricamente uno de los mayores yacimientos de "
     "cobre y oro del país.",
     "Prensa argentina / EconoJournal"),
    ("Josemaría / Filo del Sol (Vicuña)", -69.78, -28.95, "mineria", "Cobre/oro/plata", "Canadá / Australia",
     "Distrito cuprífero gigante en San Juan (frontera con Chile), entre las mayores reservas de cobre "
     "del mundo. Desarrollado por Vicuña Corp: la canadiense Lundin Mining y la angloaustraliana BHP.",
     "Prensa argentina / EconoJournal"),
    # ----------------- REPRESAS (financiamiento/construcción china) -----------------
    ("Represa Néstor Kirchner (Cóndor Cliff)", -70.86, -50.16, "represa", "Represa hidroeléctrica", "China (financia/construye)",
     "Mayor obra hidroeléctrica en construcción del país, sobre el río Santa Cruz. La construye una UTE "
     "liderada por la china Gezhouba (54%) y la financia un consorcio de bancos estatales chinos "
     "(China Development Bank, ICBC, Bank of China). La obra es argentina; el financiamiento y la "
     "construcción, mayormente chinos.",
     "La Nación / Infobae / EconoJournal"),
    ("Represa Jorge Cepernic (La Barrancosa)", -70.20, -50.02, "represa", "Represa hidroeléctrica", "China (financia/construye)",
     "Segunda gran represa sobre el río Santa Cruz, mismo esquema de construcción (Gezhouba) y "
     "financiamiento chino que la Néstor Kirchner.",
     "La Nación / EconoJournal"),
    # ----------------- CABLES SUBMARINOS (infraestructura digital) -----------------
    ("Las Toninas — amarre de cables submarinos", -56.69, -36.52, "cable", "Cable submarino", "EE.UU. (operadores)",
     "Principal punto de amarre de cables submarinos del país: por aquí entra casi todo el tráfico "
     "internacional de internet. Aterrizan SAm-1, SAC, Atlantis-2, Tannat y Firmina (Google), Malbec "
     "(Meta), entre otros. La infraestructura física está en Argentina, pero los cables son de "
     "gigantes tecnológicos extranjeros.",
     "La Nación / TeleSemana"),
    # ----------------- PUERTOS / TERMINALES (operadores extranjeros) -----------------
    ("Terminales de Puerto General San Martín", -60.73, -32.72, "puerto", "Terminal portuaria", "China / EE.UU. / otros",
     "Corazón del nodo agroexportador del Gran Rosario. Conviven terminales de traders extranjeros: "
     "COFCO (estatal china), Cargill y Bunge (EE.UU.), Louis Dreyfus (Francia), Viterra/Glencore "
     "(Suiza). Por la Hidrovía sale ~80% de las exportaciones argentinas.",
     "Bolsa de Comercio de Rosario / ArgenPorts"),
]


def generar(out_dir: str | None = None) -> Path:
    out = Path(out_dir or settings.data_dir)
    out.mkdir(parents=True, exist_ok=True)
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "nombre": nombre,
                "categoria": categoria,
                "tipo": tipo,
                "pais": pais,
                "descripcion": desc,
                "fuente": fuente,
                "extranjera": True,
            },
        }
        for nombre, lon, lat, categoria, tipo, pais, desc, fuente in INFRAESTRUCTURA
    ]
    p = out / "infraestructura_critica.geojson"
    p.write_text(json.dumps({
        "type": "FeatureCollection",
        "metadata": {
            "descripcion": "Presencia extranjera en infraestructura crítica argentina "
                           "(litio, represas, cables submarinos, puertos). Coordenadas aproximadas.",
            "fuente": "Relevo de material público (prensa y organismos argentinos)",
        },
        "features": features,
    }, ensure_ascii=False))
    log.info("infraestructura crítica: %d sitios → %s", len(features), p)
    return p


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"✓ {generar()}")
