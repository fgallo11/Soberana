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

    # fuente única de puertos (puertos.geojson generado por puertos.py)
    from .puertos import _normalizar, indice_normalizado
    puertos = indice_normalizado()

    registros = []
    for row in parser.rows:
        if len(row) < 2:
            continue
        nombre = _normalizar(row[0])
        for puerto, (lat, lon) in puertos.items():
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
