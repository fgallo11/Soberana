"""Archivo frío del historial AIS.

La DB retiene posiciones ~14 días (límite del free tier); este script
exporta cada día calendario COMPLETO a un CSV comprimido ANTES de que la
poda lo alcance. Es el prerrequisito de "recorridos del pasado" más allá
de la retención hot: sin esto, el dato muere a los 14 días y no vuelve.

- Corre en la VM (cron/systemd timer diario; ver docs/operacion.md).
- Solo stdlib: escribe `<dir>/positions_YYYY-MM-DD.csv.gz`.
- Idempotente: si el archivo del día ya existe, lo saltea.
- La subida a Cloudflare R2 (o el commit al repo) se hace con rclone/aws-cli
  por fuera de este script — un paso, documentado en operación.

Uso: python -m soberana.ingest.export_frio [dir_destino]
"""

import csv
import gzip
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from ..config import settings
from ..db import get_engine, init_db, positions, utcnow

log = logging.getLogger("soberana.export_frio")


def exportar(dir_destino: str = "./archivo_frio", dias_atras: int | None = None) -> list[Path]:
    """Exporta todos los días completos aún presentes en la DB y sin archivo.
    `dias_atras` limita cuántos días mirar (default: la retención completa)."""
    init_db()
    out = Path(dir_destino)
    out.mkdir(parents=True, exist_ok=True)
    ventana = dias_atras or settings.posiciones_retencion_dias
    hoy = utcnow().date()
    escritos: list[Path] = []
    eng = get_engine()

    for d in range(1, ventana + 1):  # ayer hacia atrás: solo días terminados
        dia = hoy - timedelta(days=d)
        destino = out / f"positions_{dia.isoformat()}.csv.gz"
        if destino.exists():
            continue
        inicio = datetime(dia.year, dia.month, dia.day, tzinfo=timezone.utc)
        fin = inicio + timedelta(days=1)
        with eng.connect() as conn:
            rows = conn.execute(
                select(positions.c.mmsi, positions.c.ts, positions.c.lat,
                       positions.c.lon, positions.c.sog, positions.c.cog, positions.c.src)
                .where(positions.c.ts >= inicio, positions.c.ts < fin)
                .order_by(positions.c.mmsi, positions.c.ts)
            ).all()
        if not rows:
            continue
        with gzip.open(destino, "wt", newline="") as f:
            w = csv.writer(f)
            w.writerow(["mmsi", "ts", "lat", "lon", "sog", "cog", "src"])
            for r in rows:
                w.writerow([r.mmsi, r.ts.isoformat(), r.lat, r.lon, r.sog, r.cog, r.src])
        log.info("exportado %s: %d posiciones → %s", dia, len(rows), destino)
        escritos.append(destino)
    return escritos


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    destino = sys.argv[1] if len(sys.argv) > 1 else "./archivo_frio"
    archivos = exportar(destino)
    print(f"✓ {len(archivos)} días exportados a {destino}" if archivos else "nada nuevo para exportar")
