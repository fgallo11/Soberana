"""Datos de DEMOSTRACIÓN para que el mapa no nazca vacío.

Cada archivo lleva `demo: true` y el frontend muestra un banner cuando los
usa. Los jobs reales (gfw, viirs, alturas) pisan estos archivos con datos
verdaderos en cuanto hay tokens configurados. Nada de esto representa buques
ni eventos reales: posiciones y nombres son inventados.

Uso: python -m soberana.ingest.demo_data
"""

import json
import math
import random
from datetime import timedelta
from pathlib import Path

from ..config import settings
from ..db import utcnow
from .hidrovia import cargar_troncal


def _acumulado(path: list[tuple[float, float]]) -> tuple[list[float], float]:
    """Distancias acumuladas (km, aprox equirectangular) a lo largo de una traza."""
    acc = [0.0]
    for (lo1, la1), (lo2, la2) in zip(path, path[1:]):
        dx = (lo2 - lo1) * 111.32 * math.cos(math.radians((la1 + la2) / 2))
        dy = (la2 - la1) * 110.57
        acc.append(acc[-1] + math.hypot(dx, dy))
    return acc, acc[-1]


def _punto_en(path: list[tuple[float, float]], acc: list[float], d_km: float) -> tuple[float, float]:
    """Punto interpolado a `d_km` del inicio de la traza."""
    d = max(0.0, min(d_km, acc[-1]))
    for i in range(1, len(acc)):
        if acc[i] >= d:
            f = (d - acc[i - 1]) / (acc[i] - acc[i - 1] or 1e-9)
            lo = path[i - 1][0] + (path[i][0] - path[i - 1][0]) * f
            la = path[i - 1][1] + (path[i][1] - path[i - 1][1]) * f
            return lo, la
    return path[-1]


# ruta costera de cabotaje (Recalada → Bahía Blanca → Golfo San Matías)
RUTA_COSTERA = [
    (-55.90, -35.35), (-56.80, -36.40), (-57.40, -37.80), (-58.50, -38.80),
    (-60.50, -39.30), (-62.00, -39.40), (-63.20, -41.20), (-64.50, -42.30),
]


def generar(out_dir: str | None = None) -> list[Path]:
    out = Path(out_dir or settings.data_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(201)  # determinístico: mismos datos demo en cada corrida
    ahora = utcnow()
    escritos = []

    # Detecciones SAR demo: 30 días con un cluster que deriva a lo largo del
    # borde de la milla 200 / Agujero Azul (al retroceder en el tiempo se ve
    # la flota "moverse")
    sar = []
    for d in range(1, 31):
        fecha = (ahora - timedelta(days=d)).date().isoformat()
        centro_lat = -44.2 - (d % 15) * 0.22   # deriva sur-norte y vuelta
        centro_lon = -59.6 - (d % 9) * 0.12
        for _ in range(rng.randint(8, 18)):
            sar.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [
                    round(centro_lon + rng.gauss(0, 0.55), 3),
                    round(centro_lat + rng.gauss(0, 0.45), 3),
                ]},
                "properties": {"matched": rng.random() < 0.45, "fecha": fecha, "fuente": "DEMO"},
            })
    p = out / "sar_detections.geojson"
    p.write_text(json.dumps({
        "type": "FeatureCollection",
        "metadata": {"demo": True, "generado": ahora.isoformat(),
                     "nota": "DATOS DE DEMOSTRACIÓN — no representan buques reales"},
        "features": sar,
    }, ensure_ascii=False))
    escritos.append(p)

    # Luces VIIRS demo: 14 noches de la 'ciudad flotante' de poteros, con el
    # enjambre derivando noche a noche pegado a la milla 201
    viirs = []
    for d in range(1, 15):
        fecha = (ahora - timedelta(days=d)).date().isoformat()
        centro_lat = -45.5 + (d % 7) * 0.18
        centro_lon = -59.4 - (d % 5) * 0.15
        for _ in range(rng.randint(60, 110)):
            viirs.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [
                    round(centro_lon + rng.gauss(0, 0.5), 3),
                    round(centro_lat + rng.gauss(0, 0.4), 3),
                ]},
                "properties": {"fecha": fecha, "qf": "1", "fuente": "DEMO"},
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

    # Película demo: buques recorriendo la Hidrovía REAL (traza generada por
    # hidrovia.py, con meandros) y la costa a velocidad realista (~15-22 km/h
    # los fluviales), muestreados cada 10 minutos, para los últimos 3 días.
    # El frontend interpola entre puntos → movimiento fluido.
    troncal = cargar_troncal(str(out))
    rutas = [(troncal, _acumulado(troncal)), (RUTA_COSTERA, _acumulado(RUTA_COSTERA))]
    flota = []
    for i in range(14):
        ruta_idx = 0 if i < 10 else 1
        path, (acc, largo) = rutas[ruta_idx]
        flota.append({
            "mmsi": f"7012345{i:02d}",
            "name": f"DEMO {'BARCAZA' if ruta_idx == 0 else 'COSTERO'} {i + 1}",
            "path": path, "acc": acc, "largo": largo,
            "vel_kmh": rng.uniform(14.0, 22.0),
            "offset_km": rng.uniform(0, largo),
            "dir": 1 if rng.random() < 0.5 else -1,
        })
    dias_replay: dict[str, dict] = {}
    for d in range(0, 3):
        fecha = (ahora - timedelta(days=d)).date().isoformat()
        buques: dict[str, dict] = {}
        for b in flota:
            pts = []
            for minuto in range(0, 1440, 10):
                horas_totales = (2 - d) * 24 + minuto / 60.0  # tiempo corrido en los 3 días
                # va y vuelve a lo largo de la ruta (ping-pong)
                d_km = b["offset_km"] + b["dir"] * b["vel_kmh"] * horas_totales
                ciclo = d_km % (2 * b["largo"])
                if ciclo < 0:
                    ciclo += 2 * b["largo"]
                pos = ciclo if ciclo <= b["largo"] else 2 * b["largo"] - ciclo
                lo, la = _punto_en(b["path"], b["acc"], pos)
                pts.append([minuto, round(lo, 5), round(la, 5)])
            buques[b["mmsi"]] = {"name": b["name"], "flag": "ARG", "pts": pts}
        dias_replay[fecha] = buques
    p = out / "replay_demo.json"
    p.write_text(json.dumps({
        "demo": True,
        "generado": ahora.isoformat(),
        "nota": "PELÍCULA DE DEMOSTRACIÓN — recorridos sintéticos, no son buques reales",
        "dias": dias_replay,
    }, ensure_ascii=False))
    escritos.append(p)
    return escritos


if __name__ == "__main__":
    for path in generar():
        print(f"✓ {path}")
