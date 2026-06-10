# Operación

## Mapa de procesos

| Proceso | Dónde corre | Qué hace | Si se cae |
|---|---|---|---|
| `soberana.api.main` | VM (systemd) | API pública + proxy tiles GFW | el mapa sigue en modo estático; AIS vivo y heatmap quedan deshabilitados con aviso |
| `soberana.ingest.ais_live` | VM (systemd) | websocket AIS + detector de gaps + retención | se pierden posiciones del período; reconecta solo con backoff |
| `soberana.ingest.gfw` | Actions (6 h) | eventos (gaps/encuentros/loitering) + SAR | quedan los datos del ciclo anterior (timestamp visible) |
| `soberana.ingest.viirs` | Actions (6 h) | luces nocturnas | ídem |
| `soberana.ingest.alturas` | Actions (6 h) | alturas Paraná (scraping Prefectura) | falla ruidosa si cambió el HTML: arreglar el parser |
| `soberana.ingest.static_layers` | Actions (6 h) | capas de contexto/soberanía | son estáticas: sin urgencia |

## Comandos útiles

```bash
# estado de las fuentes configuradas
curl -s https://api.tu-dominio.org/api/health | python3 -m json.tool

# correr cualquier job a mano
cd server && python -m soberana.ingest.gfw eventos
cd server && python -m soberana.ingest.alturas

# logs en la VM
journalctl -u soberana-ais -f
journalctl -u soberana-api -f
```

## Decisiones de retención

- Posiciones AIS: 14 días “hot” en Postgres (`SOBERANA_POSICIONES_RETENCION_DIAS`),
  luego se podan; el archivo frío (parquet en R2) es el histórico real.
- Log de eventos: **nunca se borra**. Es la memoria del proyecto y es chico
  (decenas de filas/día).

## Falsas alarmas del detector de gaps

El detector local (`ais_live.py`) silencia: buques cerca de puerto (amarrados),
y últimos contactos en el borde del área de cobertura (salieron del rango de
las antenas). Si aparece ruido sistemático en una zona (sombra de cobertura),
agregar la zona a la lista de exclusión y documentarlo en la página de metodología.

## Checklist semanal (10 minutos)

1. ¿Workflow “Ingesta de datos” verde en Actions?
2. ¿`/api/health` responde y lista las fuentes esperadas en `true`?
3. ¿El timestamp de `frontend/public/data/sar_detections.geojson` es de <24 hs?
4. ¿Disco/DB dentro de límites? (`SELECT pg_database_size(...)` < 400 MB en Supabase free)
