"""Alturas del río Paraná — Prefectura Naval Argentina.

Prefectura publica el registro de alturas en una página HTML
(https://contenidosweb.prefecturanaval.gob.ar/alturas/). No hay API formal:
esto es scraping ligero de una tabla pública oficial, citando la fuente.
Si la página cambia de estructura, el job falla ruidosamente (mejor que
publicar datos mal parseados).

Uso: python -m soberana.ingest.alturas
"""

import json
import logging
import re
from html.parser import HTMLParser
from pathlib import Path

import httpx

from ..config import settings
from ..db import utcnow

log = logging.getLogger("soberana.alturas")
URL = "https://contenidosweb.prefecturanaval.gob.ar/alturas/index.php"

# Puertos de la Vía Navegable Troncal que mostramos (con coordenadas para el mapa)
PUERTOS_HIDROVIA = {
    "CORRIENTES": (-27.469, -58.834),
    "BARRANQUERAS": (-27.486, -58.934),
    "GOYA": (-29.140, -59.263),
    "RECONQUISTA": (-29.150, -59.650),
    "LA PAZ": (-30.745, -59.645),
    "SANTA FE": (-31.633, -60.710),
    "PARANA": (-31.732, -60.529),
    "DIAMANTE": (-32.066, -60.639),
    "ROSARIO": (-32.947, -60.630),
    "SAN NICOLAS": (-33.333, -60.210),
    "RAMALLO": (-33.486, -60.005),
    "SAN PEDRO": (-33.679, -59.665),
    "ZARATE": (-34.098, -59.028),
    "CAMPANA": (-34.158, -58.959),
}


class _TablaAlturas(HTMLParser):
    """Parser mínimo sin dependencias: extrae filas <tr> de celdas de texto."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def ingerir() -> Path:
    resp = httpx.get(URL, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    parser = _TablaAlturas()
    parser.feed(resp.text)

    registros = []
    for row in parser.rows:
        if len(row) < 2:
            continue
        nombre = row[0].upper().strip()
        for puerto, (lat, lon) in PUERTOS_HIDROVIA.items():
            if puerto in nombre:
                m = re.search(r"(-?\d+[.,]\d+)", " ".join(row[1:]))
                if not m:
                    continue
                registros.append({
                    "puerto": puerto.title(),
                    "altura_m": float(m.group(1).replace(",", ".")),
                    "lat": lat,
                    "lon": lon,
                })
                break

    if not registros:
        raise SystemExit("No se pudo parsear ninguna altura: ¿cambió la página de Prefectura?")

    out = Path(settings.data_dir) / "alturas.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "fuente": "Prefectura Naval Argentina — registro del estado de los ríos",
        "url": URL,
        "generado": utcnow().isoformat(),
        "demo": False,
        "alturas": registros,
    }, ensure_ascii=False))
    log.info("alturas: %d puertos → %s", len(registros), out)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingerir()
