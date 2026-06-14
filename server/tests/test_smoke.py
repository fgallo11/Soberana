"""Smoke tests: API levanta, esquema se crea, endpoints básicos responden.
Corren sobre sqlite (sin servicios externos): son los que corre CI."""

import os
import tempfile

os.environ["SOBERANA_DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"

from fastapi.testclient import TestClient  # noqa: E402

from soberana.api.main import app  # noqa: E402
from soberana.db import events, get_engine, init_db, positions, utcnow  # noqa: E402

init_db()  # TestClient a nivel módulo no dispara el evento de startup
client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "fuentes" in body


def test_vessels_vacio_y_con_datos():
    r = client.get("/api/vessels")
    assert r.status_code == 200
    assert r.json()["type"] == "FeatureCollection"

    init_db()
    with get_engine().begin() as conn:
        conn.execute(positions.insert().values(
            mmsi="701000001", ts=utcnow(), lat=-34.5, lon=-58.3, sog=8.2, cog=120.0,
        ))
    r = client.get("/api/vessels")
    feats = r.json()["features"]
    assert len(feats) == 1
    assert feats[0]["properties"]["mmsi"] == "701000001"

    # filtro bbox que NO incluye la posición
    r = client.get("/api/vessels", params={"bbox": "-70,-50,-65,-45"})
    assert len(r.json()["features"]) == 0

    r = client.get("/api/vessels", params={"bbox": "no-es-un-bbox"})
    assert r.status_code == 400


def test_vessels_viaje_en_el_tiempo():
    from datetime import timedelta
    init_db()
    hace_3h = utcnow() - timedelta(hours=3)
    with get_engine().begin() as conn:
        conn.execute(positions.insert().values(
            mmsi="701000099", ts=hace_3h, lat=-33.0, lon=-59.0,
        ))
    # ahora (ventana 60 min): no aparece
    r = client.get("/api/vessels", params={"bbox": "-60,-34,-58,-32"})
    assert all(f["properties"]["mmsi"] != "701000099" for f in r.json()["features"])
    # como se veía hace 3 horas: aparece
    r = client.get("/api/vessels", params={"bbox": "-60,-34,-58,-32", "at": hace_3h.isoformat()})
    assert any(f["properties"]["mmsi"] == "701000099" for f in r.json()["features"])
    # at inválido
    assert client.get("/api/vessels", params={"at": "ayer"}).status_code == 400


def test_replay_pelicula_del_dia():
    from datetime import timedelta
    init_db()
    base = utcnow().replace(hour=10, minute=0, second=0, microsecond=0)
    with get_engine().begin() as conn:
        for i in range(4):  # posiciones cada 5 min: el submuestreo (10 min) debe dejar 2
            conn.execute(positions.insert().values(
                mmsi="701000777", ts=base + timedelta(minutes=5 * i),
                lat=-32.9 - i * 0.01, lon=-60.6,
            ))
    fecha = base.date().isoformat()
    r = client.get("/api/replay", params={"fecha": fecha})
    assert r.status_code == 200
    body = r.json()
    assert body["fecha"] == fecha
    pts = body["buques"]["701000777"]["pts"]
    assert len(pts) == 2  # submuestreado a 10 min
    assert pts[0][0] == 600.0  # minuto del día (10:00 UTC)
    assert client.get("/api/replay", params={"fecha": "no-es-fecha"}).status_code == 400


def test_events():
    init_db()
    with get_engine().begin() as conn:
        conn.execute(events.insert().values(
            id="test-gap-1", type="ais_gap_local", src="soberana", confidence="baja",
            mmsi="701000001", lat=-45.0, lon=-60.0, started_at=utcnow(), zone="milla_201",
        ))
    r = client.get("/api/events")
    assert r.status_code == 200
    assert r.json()["count"] >= 1
    r = client.get("/api/events", params={"type": "ais_gap_local"})
    assert all(e["type"] == "ais_gap_local" for e in r.json()["events"])


def test_gfw_tiles_sin_token_devuelve_503():
    r = client.get("/api/tiles/gfw/pesca/3/2/5.png")
    assert r.status_code == 503  # sin token configurado en tests


def test_gfw_eventos_fechas_string_se_guardan():
    """Regresión: GFW devuelve fechas como string ISO / epoch ms; deben
    convertirse a datetime antes de insertar (si no, SQLite tira TypeError)."""
    from datetime import datetime

    from soberana.ingest.gfw import _a_datetime, _guardar_eventos

    assert isinstance(_a_datetime("2026-01-15T10:30:00.000Z"), datetime)
    assert isinstance(_a_datetime(1736937000000), datetime)
    assert _a_datetime(None) is None
    assert _a_datetime("basura") is None

    init_db()
    entradas = [{
        "id": "evt-test-1",
        "start": "2026-01-15T10:30:00.000Z",
        "end": "2026-01-15T18:00:00.000Z",
        "position": {"lat": -45.0, "lon": -60.0},
        "vessel": {"ssvid": "701000123", "name": "TEST", "flag": "ARG"},
    }]
    n = _guardar_eventos(get_engine(), "ais_gap_gfw", entradas)
    assert n == 1
    r = client.get("/api/events", params={"type": "ais_gap_gfw"})
    assert any(e["id"] == "gfw-evt-test-1" for e in r.json()["events"])


def test_capas_estaticas_se_generan(tmp_path):
    from soberana.ingest.static_layers import generar
    archivos = generar(out_dir=str(tmp_path))
    nombres = {p.name for p in archivos}
    assert {"zee.geojson", "ficz_focz.geojson", "amps.geojson",
            "antartida.geojson", "bases_militares.geojson"} <= nombres
    import json
    zee = json.loads((tmp_path / "zee.geojson").read_text())
    assert zee["metadata"]["aproximado"] is True
    assert len(zee["features"]) == 2


def test_hidrovia_y_puertos_fallback_sin_red(tmp_path):
    import json

    from soberana.ingest.hidrovia import cargar_troncal, generar as gen_hidrovia
    from soberana.ingest.puertos import cargar_puertos, generar as gen_puertos

    gen_hidrovia(out_dir=str(tmp_path), fuente="curada")
    h = json.loads((tmp_path / "hidrovia.geojson").read_text())
    troncal = [f for f in h["features"] if f["properties"]["tipo"] == "troncal"]
    assert len(troncal) == 1 and len(troncal[0]["geometry"]["coordinates"]) >= 15
    assert len(cargar_troncal(str(tmp_path))) >= 15

    gen_puertos(out_dir=str(tmp_path), fuente="curada")
    puertos = cargar_puertos(str(tmp_path))
    assert len(puertos) >= 20
    assert any(n == "Rosario" for n, _, _, _ in puertos)


def test_escalas_en_puerto():
    from datetime import timedelta

    from soberana.db import port_calls
    init_db()
    base = utcnow() - timedelta(days=1)
    with get_engine().begin() as conn:
        # 3 horas amarrado en Rosario (-32.947, -60.630), después navegando lejos
        for i in range(7):
            conn.execute(positions.insert().values(
                mmsi="701000555", ts=base + timedelta(minutes=30 * i),
                lat=-32.95, lon=-60.63,
            ))
        conn.execute(positions.insert().values(
            mmsi="701000555", ts=base + timedelta(hours=6), lat=-33.5, lon=-59.9,
        ))
    escalas = port_calls("701000555", dias=3)
    assert len(escalas) == 1
    assert escalas[0]["puerto"] == "Rosario"
    assert escalas[0]["horas"] >= 2.5
    r = client.get("/api/vessels/701000555/escalas")
    assert r.status_code == 200
    assert r.json()["reconstruido"] is True
    assert r.json()["escalas"][0]["puerto"] == "Rosario"
