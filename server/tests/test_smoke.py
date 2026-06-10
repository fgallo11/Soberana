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


def test_capas_estaticas_se_generan(tmp_path):
    from soberana.ingest.static_layers import generar
    archivos = generar(out_dir=str(tmp_path))
    nombres = {p.name for p in archivos}
    assert {"zee.geojson", "ficz_focz.geojson", "amps.geojson",
            "bases_militares.geojson", "hidrovia.geojson", "puertos.geojson"} <= nombres
    import json
    zee = json.loads((tmp_path / "zee.geojson").read_text())
    assert zee["metadata"]["aproximado"] is True
    assert len(zee["features"]) == 2
