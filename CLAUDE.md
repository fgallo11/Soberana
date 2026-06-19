# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Soberana is a public map of Argentine sovereignty monitoring across maritime, riverine, and aerial domains. It combines open data (AIS, SAR, VIIRS, ADS-B) with no login, no ads, and zero operational cost. Every data layer declares its latency honestly; events are evidence for investigation, never accusations.

## Commands

### Frontend

```bash
cd frontend
npm install
npm run dev        # dev server at http://localhost:5173
npm run build      # production build → dist/
npm run lint
```

### Backend

```bash
cd server
pip install -e ".[dev,geo]"
uvicorn soberana.api.main:app --reload   # API at http://localhost:8000

# Run all tests
python -m pytest tests/ -q

# Run a single test
python -m pytest tests/test_smoke.py::test_health -q
```

### With Docker (Postgres + API)

```bash
docker compose up                       # db + api
docker compose --profile ais up         # + persistent AIS consumer (requires token)
```

### Batch ingestion (local)

```bash
cd server
export SOBERANA_DATA_DIR=../frontend/public/data
python -m soberana.ingest.static_layers
python -m soberana.ingest.gfw          # requires SOBERANA_GFW_API_TOKEN
python -m soberana.ingest.viirs        # requires EOG credentials
python -m soberana.ingest.alturas
```

## Architecture

### Stack

| Layer | Tech |
|-------|------|
| Frontend | React 18.3 + TypeScript 5.6, Vite 6, MapLibre GL JS 5 |
| Backend | FastAPI 0.115+, SQLAlchemy 2.0, Uvicorn |
| Database | SQLite (dev) / Postgres (prod via Supabase) |
| Ingestion | Python batch scripts, GitHub Actions cron every 6h |
| Hosting | Vercel (frontend), Oracle always-free VM (API), Cloudflare R2 (cold archive) |

### Data flow

```
LIVE:
  aisstream.io (websocket) → VM (ingest/ais_live.py) → Postgres → /api/vessels

BATCH (every 6h via GitHub Actions):
  GFW API           → gfw.py            → DB + frontend/public/data/*.geojson
  EOG/VIIRS         → viirs.py          → viirs_boats.geojson
  Prefectura        → alturas.py        → alturas.json
  OSM/IGN/Natural Earth → static_layers.py, tierra.py, etc. → GeoJSON files

FRONTEND:
  Static mode (no backend): reads /public/data/*.geojson + live ADS-B from adsb.lol
  With backend: + /api/vessels (live AIS), /api/replay (history), /api/events, /api/tiles/gfw/*
```

### Graceful degradation

The frontend works fully in static mode if the backend is down. `VITE_API_URL` empty → no backend calls. `/api/health` reports which sources are active. Missing tokens → that source is marked offline, demo data shown.

## Key Files

| File | Purpose |
|------|---------|
| `frontend/src/layers.ts` | Layer registry: every map layer is a config entry here |
| `frontend/src/MapView.tsx` | MapLibre wrapper; `fotograma()` interpolates replay positions |
| `frontend/src/map_style.ts` | MapLibre style spec (dark ops aesthetic) |
| `frontend/src/config.ts` | `API_URL`, bbox bounds, zoom limits, badge types |
| `server/soberana/api/main.py` | All API endpoints |
| `server/soberana/db.py` | SQLAlchemy schema + query functions |
| `server/soberana/config.py` | `Settings` (Pydantic): reads `SOBERANA_*` env vars |
| `.github/workflows/ingest.yml` | Cron pipeline: ingest → commit GeoJSON → triggers Vercel redeploy |

## Conventions

### Layers (frontend)

Each entry in `layers.ts` `CAPAS` array defines: `id`, `grupo`, `titulo`, `descripcion`, `badge` (latency label), `mapLayers` (MapLibre style layer IDs), `defaultOn`, `requiereBackend`, `proximamente`. Adding a new domain means a new entry here + style in `map_style.ts`, not code rewrites.

### Database

- **No PostGIS types** — lat/lon stored as plain floats; spatial operations use Shapely at ingest time.
- Same `db.py` code runs on SQLite (dev/tests) and Postgres (prod). No dialect-specific SQL.
- Hot data (14 days): Postgres. Cold archive: Parquet files in Cloudflare R2 via `ingest/export_frio.py`.

### Ingestion

- **Idempotent**: GFW events use stable IDs (`gfw-evt-*`); upserts are safe for re-runs.
- **Resilient**: each job wrapped in try/except; Actions steps use `|| echo "::warning::"` so one failure doesn't abort the pipeline.
- **UTC everywhere**: midnight boundary = 00:00 UTC, not local time.

### Events

Events table is an append-only log. `id` is the primary key (stable: `gfw-evt-X` or `soberana-gap-X`). `type` values: `ais_gap_gfw`, `ais_gap_local`, `encounter`, `loitering`, `reaparicion`. `confidence`: `alta | media | baja`.

### Replay

`/api/replay?fecha=YYYY-MM-DD` returns interpolated positions in 10-minute buckets. Gaps >45 min hide the vessel (coverage shadow). `fotograma()` in `MapView.tsx` linearly interpolates between buckets.

### Port inference

Haversine distance to curated port list (Dirección Nacional de Puertos); 8 km radius, ≥2 hrs dwell = port call. No external geo service needed.

### Testing

`tests/test_smoke.py` uses SQLite + `TestClient` (no external services). All new API endpoints and ingest functions should have a smoke test that inserts synthetic data and asserts the response.

### TypeScript

Strict mode (`tsconfig.json`). Target ES2022. No CSS framework — single `styles.css`, responsive via media queries.

## Environment Variables

Backend (`server/.env` or shell):

```bash
SOBERANA_DATABASE_URL=sqlite:///./soberana.db
SOBERANA_GFW_API_TOKEN=          # optional; free at globalfishingwatch.org
SOBERANA_AISSTREAM_API_KEY=      # optional; free at aisstream.io
SOBERANA_EOG_USERNAME=           # optional; free from eog@mines.edu
SOBERANA_EOG_PASSWORD=
SOBERANA_EOG_CLIENT_ID=
SOBERANA_EOG_CLIENT_SECRET=
SOBERANA_DATA_DIR=../frontend/public/data
```

Frontend:

```bash
VITE_API_URL=https://api.soberana.ar   # empty = static mode
```

## Adding a New Layer

1. Create `server/soberana/ingest/<domain>.py` — fetches data, writes GeoJSON to `$SOBERANA_DATA_DIR`.
2. Add entry to `frontend/src/layers.ts` (`CAPAS` array).
3. Add paint/layout style layers to `frontend/src/map_style.ts`.
4. If batch job: add step to `.github/workflows/ingest.yml`.
5. If it needs an API endpoint: add query to `db.py`, route to `api/main.py`, smoke test.
