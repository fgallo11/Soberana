"""Datos de DEMOSTRACIÓN para que el mapa no nazca vacío.

Cada archivo lleva `demo: true` y el frontend muestra un banner cuando los
usa. Los jobs reales (gfw, viirs, alturas) pisan estos archivos con datos
verdaderos en cuanto hay tokens configurados. Nada de esto representa buques
ni eventos reales: posiciones y nombres son inventados.

Uso: python -m soberana.ingest.demo_data
"""

import json
import random
from datetime import timedelta
from pathlib import Path

from ..config import settings
from ..db import utcnow


def generar(out_dir: str | None = None) -> list[Path]:
    out = Path(out_dir or settings.data_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(201)  # determinístico: mismos datos demo en cada corrida
    ahora = utcnow()
    escritos = []

    # Detecciones SAR demo: cluster sobre el borde de la milla 200 / Agujero Azul
    sar = []
    for _ in range(60):
        lon = rng.uniform(-61.0, -58.2)
        lat = rng.uniform(-47.3, -43.8)
        sar.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 3), round(lat, 3)]},
            "properties": {
                "matched": rng.random() < 0.45,
                "fecha": (ahora - timedelta(days=rng.randint(1, 6))).date().isoformat(),
                "fuente": "DEMO",
            },
        })
    p = out / "sar_detections.geojson"
    p.write_text(json.dumps({
        "type": "FeatureCollection",
        "metadata": {"demo": True, "generado": ahora.isoformat(),
                     "nota": "DATOS DE DEMOSTRACIÓN — no representan buques reales"},
        "features": sar,
    }, ensure_ascii=False))
    escritos.append(p)

    # Luces VIIRS demo: la 'ciudad flotante' de poteros pegada a la milla 201
    viirs = []
    for _ in range(120):
        lon = rng.uniform(-60.8, -58.0)
        lat = rng.uniform(-47.0, -44.0)
        viirs.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 3), round(lat, 3)]},
            "properties": {"fecha": (ahora - timedelta(days=1)).date().isoformat(), "qf": "1", "fuente": "DEMO"},
        })
    p = out / "viirs_boats.geojson"
    p.write_text(json.dumps({
        "type": "FeatureCollection",
        "metadata": {"demo": True, "generado": ahora.isoformat(),
                     "nota": "DATOS DE DEMOSTRACIÓN — no representan detecciones reales"},
        "features": viirs,
    }, ensure_ascii=False))
    escritos.append(p)

    # Log de eventos demo
    eventos = []
    nombres = ["DEMO PESQUERO 1", "DEMO POTERO 2", "DEMO CARGUERO 3", "DEMO ARRASTRERO 4"]
    for i in range(8):
        inicio = ahora - timedelta(days=rng.randint(1, 12), hours=rng.randint(0, 23))
        cerrado = rng.random() < 0.6
        eventos.append({
            "id": f"demo-gap-{i}",
            "type": "ais_gap_gfw" if i % 3 else "ais_gap_local",
            "src": "gfw" if i % 3 else "soberana",
            "confidence": "alta" if i % 3 else "baja",
            "mmsi": f"4120000{i:02d}",
            "vessel_name": nombres[i % len(nombres)],
            "flag": rng.choice(["CHN", "TWN", "KOR", "ESP"]),
            "lat": round(rng.uniform(-47.0, -44.0), 3),
            "lon": round(rng.uniform(-60.5, -58.2), 3),
            "started_at": inicio.isoformat(),
            "ended_at": (inicio + timedelta(hours=rng.randint(6, 72))).isoformat() if cerrado else None,
            "zone": "milla_201",
            "demo": True,
        })
    eventos.sort(key=lambda e: e["started_at"], reverse=True)
    p = out / "events.json"
    p.write_text(json.dumps({
        "generado": ahora.isoformat(), "demo": True,
        "nota": "DATOS DE DEMOSTRACIÓN — no representan eventos reales",
        "events": eventos,
    }, ensure_ascii=False))
    escritos.append(p)

    # Alturas demo (estructura idéntica a la real)
    p = out / "alturas.json"
    p.write_text(json.dumps({
        "fuente": "DEMO — estructura del job de alturas de Prefectura",
        "generado": ahora.isoformat(), "demo": True,
        "alturas": [
            {"puerto": "Corrientes", "altura_m": 2.85, "lat": -27.469, "lon": -58.834},
            {"puerto": "Santa Fe", "altura_m": 3.10, "lat": -31.633, "lon": -60.710},
            {"puerto": "Rosario", "altura_m": 2.65, "lat": -32.947, "lon": -60.630},
            {"puerto": "San Pedro", "altura_m": 1.95, "lat": -33.679, "lon": -59.665},
            {"puerto": "Zárate", "altura_m": 1.40, "lat": -34.098, "lon": -59.028},
        ],
    }, ensure_ascii=False))
    escritos.append(p)
    return escritos


if __name__ == "__main__":
    for path in generar():
        print(f"✓ {path}")
