# Despliegue a costo USD 0 — paso a paso

Arquitectura: ver [PLAN.md](../PLAN.md) §2. Orden recomendado: cada paso deja algo útil online.

## Paso 1 — Frontend en Vercel (10 min) → ya tenés mapa público

1. Importá el repo en [vercel.com](https://vercel.com) (Add New → Project).
2. Configuración: **Root Directory: `frontend`** — Vercel detecta Vite solo (build `npm run build`, output `dist`).
3. Deploy. Listo: mapa público en `<proyecto>.vercel.app` en **modo estático**:
   capas de soberanía + datos demo + tráfico aéreo en vivo (adsb.lol directo).

## Paso 2 — Datos reales vía GitHub Actions (15 min)

1. Sacá los tokens (todos gratis):
   - **GFW**: registrate en https://globalfishingwatch.org/our-apis/ → API token.
   - **EOG (VIIRS)** — son dos pasos desde mayo 2025:
     1. Registrate en https://eogdata.mines.edu/products/register/ → usuario/clave.
     2. Mandá un mail a **eog@mines.edu** pidiendo un *OpenID client ID y secret
        para descargas programáticas* (gratuito). Sin esto, la descarga
        automatizada puede fallar (el flujo viejo está discontinuado).
2. En GitHub: Settings → Secrets and variables → Actions → New repository secret:
   `GFW_API_TOKEN`, `EOG_USERNAME`, `EOG_PASSWORD`, `EOG_CLIENT_ID`, `EOG_CLIENT_SECRET`.
3. Corré a mano el workflow **“Ingesta de datos”** (Actions → Run workflow) para validar.
4. A partir de ahí corre cada 6 hs, commitea los datos y Vercel redeploya solo.
   El banner de “datos de demostración” desaparece en el primer ciclo exitoso.

## Paso 3 — Backend en VM Oracle always-free (1-2 hs) → AIS en vivo + alarmas NRT

1. Cuenta en [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/); creá una VM
   **Ampere A1** (hasta 4 OCPU / 24 GB siguen siendo always-free; con 1 OCPU sobra).
   Ubuntu 24.04. Abrí el puerto 443/80 en la VCN.
2. En la VM:
   ```bash
   sudo apt update && sudo apt install -y python3-pip python3-venv git caddy
   git clone https://github.com/fgallo11/Soberana && cd Soberana/server
   python3 -m venv .venv && .venv/bin/pip install -e ".[postgres,geo]"
   ```
3. Base de datos: dos opciones
   - **Supabase free**: creá el proyecto, copiá el connection string →
     `SOBERANA_DATABASE_URL=postgresql+psycopg://...`
   - **Postgres local en la VM** (más simple, un proveedor menos): `sudo apt install postgresql`.
4. API key de **aisstream.io** (gratis) → `SOBERANA_AISSTREAM_API_KEY`.
5. Servicios systemd (api + ingesta AIS). Unidades de ejemplo:
   ```ini
   # /etc/systemd/system/soberana-api.service
   [Unit]
   Description=Soberana API
   After=network.target
   [Service]
   WorkingDirectory=/home/ubuntu/Soberana/server
   EnvironmentFile=/home/ubuntu/Soberana/server/.env
   ExecStart=/home/ubuntu/Soberana/server/.venv/bin/uvicorn soberana.api.main:app --host 127.0.0.1 --port 8000
   Restart=always
   [Install]
   WantedBy=multi-user.target
   ```
   ```ini
   # /etc/systemd/system/soberana-ais.service  (igual, con:)
   ExecStart=/home/ubuntu/Soberana/server/.venv/bin/python -m soberana.ingest.ais_live
   ```
   `sudo systemctl enable --now soberana-api soberana-ais`
6. **Caddy** como reverse proxy con TLS automático (`/etc/caddy/Caddyfile`):
   ```
   api.tu-dominio.org {
       reverse_proxy 127.0.0.1:8000
   }
   ```
   Sin dominio propio: usá Cloudflare Tunnel (gratis) o la IP con el subdominio de sslip.io.
7. Poné el dominio detrás de **Cloudflare** (plan gratis) — caché y absorción de picos.
8. En Vercel: Settings → Environment Variables → `VITE_API_URL=https://api.tu-dominio.org` → redeploy.
   Se habilitan: AIS en vivo, heatmap GFW, eventos servidos por API.

## Paso 4 — Archivo frío (cuando haya volumen)

Cloudflare R2 free (10 GB): bucket `soberana-archivo`; un cron en la VM exporta diariamente
posiciones viejas a parquet y las borra de Postgres (`prune_positions` ya limita el hot a 14 días).

## Mantenimiento de free tiers (importante)

| Riesgo | Mitigación |
|---|---|
| Oracle reclama VMs idle | la ingesta AIS genera CPU constante; igual: healthcheck externo (Uptime Kuma / cron-job.org gratis) |
| Supabase pausa proyectos inactivos | la ingesta escribe cada pocos segundos; no aplica |
| Vercel/Actions cambian límites | el frontend es portable a Cloudflare Pages sin cambios; los jobs corren en cualquier runner |
| aisstream/adsb.lol desaparecen | ingesta agnóstica de fuente; plan de receptores propios (PLAN.md fase 5) |
