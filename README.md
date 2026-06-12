# Soberana

**Mapa público de actividad marítima, fluvial y aérea en territorio argentino.**
Hidrovía Paraná–Paraguay · Zona Económica Exclusiva · milla 201 · Malvinas y Atlántico Sur.

Gratuito a perpetuidad. Sin publicidad. Sin cuentas. Datos abiertos y código abierto.
El objetivo es uno solo: que cualquier persona pueda ver qué pasa en los mares y ríos argentinos.

> 📋 El plan operativo (alcance, fuentes, trade-offs, roadmap) está en [PLAN.md](PLAN.md).
> 🧭 La visión completa —soberanía por dominios: marítimo, Hidrovía, territorial, energético, digital, aéreo— en [docs/vision.md](docs/vision.md).
> 🤝 ¿Querés sumarte? La pestaña **Colaborá** del sitio explica cómo; los issues del repo son el punto de entrada.

## Qué muestra

| Capa | Fuente | Latencia |
|---|---|---|
| Buques en vivo (Hidrovía y litoral) | aisstream.io (AIS terrestre) | minutos |
| Detecciones por radar satelital — buques *dark* | Global Fishing Watch / Sentinel-1 | ~5 días |
| Luces nocturnas de la flota potera | VIIRS (EOG/NOAA) | ~24 hs |
| Esfuerzo pesquero (heatmap) | Global Fishing Watch | 72 hs |
| **Alarmas de apagado de AIS** (con log permanente) | GFW + detector propio | 72 hs / NRT |
| Aeronaves, incluidas militares (puente aéreo RAF) | adsb.lol (red comunitaria sin filtrar) | segundos |
| ZEE, milla 200, FICZ/FOCZ, bases militares, AMPs | IGN, Marine Regions, fuentes públicas | estático |
| Alturas del Paraná | Prefectura Naval | horas |

La página **“Qué estás viendo (y qué no)”** del sitio explica las limitaciones reales de cada
sensor. Regla de oro: el mapa muestra *actividad aparente*, no delitos; la ausencia de un buque
no prueba que no esté.

## Correr local (2 minutos, sin tokens)

```bash
# Frontend (modo estático: capas de archivo + tráfico aéreo de adsb.lol)
cd frontend
npm install
npm run dev          # http://localhost:5173

# Backend opcional (sqlite, sin docker)
cd server
pip install -e ".[dev,geo]"
uvicorn soberana.api.main:app --reload   # http://localhost:8000/api/health
```

Sin tokens configurados, las capas satelitales muestran **datos de demostración** (banner visible).
Con Postgres real: `docker compose up`. Tokens: ver [.env.example](.env.example) — todos gratuitos.

## Arquitectura (costo operativo: USD 0)

```
GitHub Actions (cron 6 h) ──► regenera frontend/public/data/*.geojson ──► commit ──► Vercel redeploya
   GFW · VIIRS · alturas · capas estáticas

VM Oracle always-free ──► websocket aisstream.io + detector de gaps + API FastAPI
   └── Postgres (Supabase free / la misma VM) · archivo frío en Cloudflare R2

Frontend: React + MapLibre GL JS, SPA estática en Vercel (basemap: OpenFreeMap)
```

El frontend funciona **sin backend** (modo estático): solo pierde el AIS en vivo y el heatmap GFW,
y lo dice en el panel de capas. Guía completa de despliegue: [docs/despliegue.md](docs/despliegue.md).

## Estructura

```
frontend/   SPA (React + Vite + MapLibre) — Vercel
server/     API (FastAPI) + jobs de ingesta (Python) — VM / Actions
  soberana/api/       endpoints públicos + proxy de tiles GFW
  soberana/ingest/    ais_live, gfw, viirs, alturas, static_layers, demo_data
.github/workflows/    ci.yml (tests+build) · ingest.yml (datos cada 6 h)
docs/       despliegue ($0 paso a paso) y operación
```

## Principios

1. **Honestidad sobre los datos:** cada capa declara su retraso y su cobertura. No prometemos
   "tiempo real" donde no existe (la milla 201 no se ve en vivo gratis — se ve por satélite, con días).
2. **Evidencia, no condena:** un apagado de AIS o una detección sin correlacionar es un dato para
   investigar, nunca una acusación.
3. **Transparencia total:** código, pipelines y log de eventos públicos y auditables. La capa militar
   muestra todo lo que la red comunitaria capta, sin filtrar, de cualquier fuerza.
4. **$0 para siempre:** sin publicidad, sin cobros, infraestructura sobre free tiers, todo migrable.

## Atribuciones

Global Fishing Watch · Earth Observation Group (Colorado School of Mines / NOAA) · aisstream.io ·
adsb.lol · Prefectura Naval Argentina · IGN · Marine Regions (VLIZ) · OpenStreetMap · OpenFreeMap ·
Copernicus/ESA (Sentinel-1).

## Licencia

[MIT](LICENSE). Los datos de terceros conservan sus licencias de origen (GFW y OpenSky: uso no comercial con atribución).
