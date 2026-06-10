# Soberana — Plan de proyecto (v2)

**Mapa público de actividad marítima, fluvial y aérea en territorio argentino**
Foco: Hidrovía Paraná-Paraguay, Zona Económica Exclusiva (ZEE), milla 201 y **vigilancia de soberanía** (Malvinas y Atlántico Sur).
Objetivo: transparencia ciudadana — cualquier persona abre el mapa y entiende qué está pasando, sin cuenta ni conocimiento técnico.

> Documento de planificación. No hay código todavía. v2 — junio 2026.
> Cambios respecto de v1: decisiones de financiamiento y política editorial tomadas, arquitectura rediseñada a costo operativo USD 0, capa militar/soberanía incorporada, sistema de alarmas de apagado de AIS definido, ideas adicionales propuestas.

## Decisiones tomadas (antes preguntas abiertas)

| Decisión | Definición |
|---|---|
| Financiamiento | **Costo operativo USD 0.** Nunca cobrar, nunca publicidad. Todo sobre free tiers. Compatible con las licencias no-comerciales de GFW y OpenSky |
| Identidad de buques | **Se muestra** (nombre, MMSI, bandera, historial) con disclaimer prominente: el mapa muestra actividad *aparente*, no delitos |
| Capa militar | **Todo lo captable, sin filtrar** — aeronaves militares de cualquier fuerza (extranjeras y argentinas) que la red ADS-B comunitaria capte, más capas estáticas de soberanía (ver §3-bis) |
| Alarmas | Apagado de AIS visible **en el mapa + log histórico navegable**. Sin bots externos por ahora |

---

## 0. La verdad incómoda primero

Tres realidades que condicionan todo lo demás. Si no las aceptamos, el proyecto promete algo que no puede cumplir:

1. **"Tiempo real" en la milla 201 no existe gratis.** El AIS terrestre llega a ~200 km de la costa como máximo; la milla 201 está a ~370 km. Lo que pasa ahí solo se ve por AIS satelital (comercial, miles de USD/mes) o por las fuentes derivadas que publica Global Fishing Watch **con 72 horas de retraso**. El mapa va a ser *near real-time* en la Hidrovía y la costa, y *delayed* (72 hs a 5 días) en altamar. Hay que decirlo en la UI, no esconderlo.

2. **Los barcos que más interesan son justamente los que no transmiten.** La flota potera que pesca pegada a la milla 201 apaga el AIS o transmite intermitentemente, y **los buques de guerra no transmiten AIS por diseño** (están exentos de SOLAS). Para verlos hacen falta sensores que no dependen de cooperación del buque: SAR (Sentinel-1) y luces nocturnas (VIIRS). Ambos existen gratis y procesados — esa es la apuesta central del proyecto, no el AIS.

3. **Las fuentes "oficiales" argentinas no tienen APIs.** Prefectura no publica posiciones (sí publica alturas de los ríos — ver §3.11). El sistema Guardacostas no es público. SAOCOM requiere licencia y casi seguro prohíbe republicación. El plan no puede depender de que el Estado coopere; si después coopera, mejor.

---

## 1. Alcance y definición del MVP

### Qué ES el producto

Un mapa web estático-más-API, público, sin login, gratuito a perpetuidad y sin publicidad, que superpone capas de actividad sobre el territorio marítimo/fluvial argentino, con la fecha/hora de cada dato visible y un selector temporal simple. No es una plataforma de inteligencia y no identifica "culpables" — muestra evidencia con su grado de certeza.

### MVP (primera versión funcional)

| Incluye | Detalle |
|---|---|
| Capas estáticas de contexto | ZEE, límite milla 200/201, línea de base, traza de la Hidrovía troncal, puertos principales, límites IGN |
| **Capas estáticas de soberanía** | Bases militares propias y extranjeras (Mount Pleasant incluida), zonas de pesca licenciada por las islas (FICZ/FOCZ), áreas marinas protegidas (Namuncurá–Burdwood, Yaganes), Agujero Azul, zonas restringidas a la navegación. Son archivos estáticos: baratísimas de servir y de alto valor narrativo |
| Esfuerzo pesquero (GFW) | Heatmap de actividad pesquera aparente, últimos 30 días, delay 72 hs |
| **Detecciones SAR (GFW)** | Buques detectados por Sentinel-1, clasificados *matched* (con AIS) vs *dark* (sin AIS) — la capa estrella para milla 201 y Malvinas |
| **Luces nocturnas (VIIRS VBD)** | Detección de luces de barcos (flota potera) — actualización diaria |
| AIS en vivo costero/fluvial | Posiciones vía aisstream.io para Hidrovía + litoral |
| Ficha de buque | Nombre, MMSI, bandera, tipo — de los metadatos AIS y la API de vessels de GFW, con disclaimer |
| Transparencia metodológica | Página "qué estás viendo y qué no": fuentes, delays, cobertura, limitaciones |

### Explícitamente FUERA del MVP (y por qué)

- **Capa aérea (ADS-B), incluida la militar:** la cobertura comunitaria en Argentina es rala y sobre el mar casi nula. Es la capa con más demanda emocional (puente aéreo RAF) pero requiere resolver identificación de aeronaves militares y cobertura — mejor hacerla bien en fase 4 que mal en el MVP.
- **Alarma de apagado de AIS:** fase 3, porque depende de tener primero la ingesta de eventos GFW estable y el esquema de log (§3-ter).
- **Procesamiento SAR propio (Sentinel-1 crudo):** GFW ya lo hace y lo publica por API. Reinventarlo sería peor y carísimo. Solo como contingencia documentada.
- **SAOCOM:** requiere convenio con CONAE. → Fase de partnership, no técnica.
- **Histórico navegable completo:** valioso pero no mínimo. Eso sí: **se almacena todo desde el día 1**.
- **MarineTraffic:** descartado (ver §3.5).

### Criterio de éxito del MVP

Una persona sin contexto abre el sitio, ve la ZEE, ve la mancha de la flota pesquera sobre la milla 201 (SAR + VIIRS + heatmap), ve la zona ocupada con sus bases y licencias pesqueras dibujadas, ve barcos moviéndose en vivo por el Paraná, y entiende —porque la UI se lo dice— qué dato es de hace 5 minutos y cuál de hace 3 días.

---

## 2. Arquitectura del sistema — costo operativo USD 0

### Principio rector

**Restricción dura: USD 0/mes.** Eso descarta el VPS único de la v1 y obliga a una arquitectura distribuida sobre free tiers. El trade-off es honesto: más piezas que coordinar, límites de almacenamiento, y dependencia de la buena voluntad de ~4 proveedores gratuitos. A cambio: el proyecto no muere nunca por falta de plata, que era el riesgo n.º 1. Cada pieza se elige para que sea **migrable**: si un free tier cambia sus condiciones, se mueve esa pieza sin reescribir el sistema.

### Componentes y dónde corre cada uno

```
┌────────────────────────────────────────────────────────────────┐
│ GITHUB ACTIONS (cron, gratis en repo público)                   │
│  [cada 6h]  GFW 4Wings: heatmap, detecciones SAR ──────────┐    │
│  [cada 6h]  GFW Events: encuentros, loitering, GAPS DE AIS │    │
│  [diario]   VIIRS VBD (luces nocturnas)                    │    │
│  [cada 6h]  Alturas del Paraná (Prefectura/INA)            │    │
│  [semanal]  Catálogos estáticos (IGN, puertos, soberanía)  │    │
│  [diario]   Archivo frío: parquet/PMTiles → R2             │    │
└────────────────────────────────────────────────────────────┼────┘
                                                             ▼
┌──────────────────────────────┐         ┌───────────────────────────┐
│ VM ORACLE CLOUD always-free  │         │ SUPABASE free tier         │
│ (único proceso persistente)  │ ──────► │ Postgres + PostGIS 500 MB  │
│  - websocket aisstream.io    │         │  - posiciones vivas (hot)  │
│  - detector de gaps propio   │         │  - detecciones, eventos,   │
│    (costa/Hidrovía, NRT)     │         │    log de alarmas          │
│  - API FastAPI: /vessels,    │         └────────────┬──────────────┘
│    tiles MVT, proxy GFW      │                      │ archivo frío
└──────────────┬───────────────┘                      ▼
               │                          ┌───────────────────────────┐
               │ (detrás de Cloudflare    │ CLOUDFLARE R2 free (10 GB) │
               │  gratis: caché + TLS)    │ parquet histórico, PMTiles │
               ▼                          └───────────────────────────┘
┌──────────────────────────────┐
│ VERCEL free (frontend)        │  ← capas estáticas (PMTiles) servidas
│ SPA MapLibre GL JS            │     directo desde R2/CDN, sin backend
└──────────────────────────────┘
```

### Por qué Vercel no puede correr todo

Vercel es serverless: funciones efímeras de segundos. La ingesta AIS es una **conexión websocket permanente** y la base con PostGIS necesita un servidor de verdad. Por eso el reparto: Vercel sirve el frontend (su fuerte, gratis, con CDN global), GitHub Actions corre los jobs batch (no necesitan servidor propio), y la única pieza que exige un proceso vivo 24/7 —el consumidor de aisstream.io más la API— va a la VM always-free de Oracle (4 ARM cores / 24 GB RAM gratis, holgadísimo). Cloudflare gratis adelante de la VM da caché y TLS, y absorbe picos de tráfico si el mapa sale en la prensa.

### Decisiones y trade-offs de la arquitectura $0

- **Supabase free (500 MB) como Postgres+PostGIS** vs Neon: Supabase incluye PostGIS sin fricción y el límite de 500 MB es el real constraint. Consecuencia de diseño: las posiciones AIS vivas se retienen ~7-14 días en caliente; el resto se degrada a posiciones submuestreadas y se exporta diario a parquet en R2. El histórico completo vive en R2, no en Postgres. Alternativa si Supabase aprieta: PostGIS en la propia VM de Oracle (la VM da de sobra) — de hecho es el plan B natural y elimina un proveedor.
- **GitHub Actions como scheduler** vs cron en la VM: Actions deja los jobs versionados, con logs públicos (transparencia también del pipeline) y sin depender de la VM para lo batch. Contra: límites de minutos (generosos en repo público) y latencia de arranque — irrelevante para jobs cada 6 hs.
- **Riesgo free tier asumido y documentado:** Oracle puede reclamar VMs always-free idle, Supabase pausa proyectos inactivos, Vercel puede cambiar términos. Mitigaciones: healthchecks con keep-alive, infraestructura como código para recrear cada pieza en <1 hora, y todo el dato persistente en R2 + el propio repo (nada irrecuperable vive en un free tier).
- **Polling del frontend cada 30-60 s** para posiciones vivas (no websocket propio en MVP): menos estado en el servidor, cacheable en Cloudflare. Websocket propio solo si el polling queda corto con usuarios reales.

---

## 3. Análisis de cada fuente de datos

Orden: de más a menos útil para este proyecto.

### 3.1 Global Fishing Watch — ⭐ columna vertebral

| Aspecto | Realidad |
|---|---|
| Acceso | API REST v3 gratuita con registro y token. Rate limit: **50.000 req/día, 1.55 M/mes** — sobra para jobs server-side, jamás exponer el token al navegador |
| Datos | 4Wings (rásteres de esfuerzo pesquero, presencia AIS, **detecciones SAR de Sentinel-1 2017→hace ~5 días, clasificadas con deep learning, matcheadas contra AIS**), **eventos — incluidos los gaps de AIS: apagados considerados intencionales, de alta confianza** (base de la alarma, §3-ter), encuentros entre buques, *loitering*, visitas a puerto, identidad de buques |
| Frecuencia | AIS con **delay de 72 hs**; SAR según revisita de Sentinel-1 sobre el Atlántico Sur (~6-12 días por punto) |
| Formato | JSON, tiles 4Wings (PNG/MVT), CSV por data portal |
| Restricciones | Atribución obligatoria. Términos no-comerciales — compatibles con la decisión de $0/sin publicidad |
| Trade-off brutal | Dependencia única para lo más valioso (SAR + eventos + altamar). Mitigación: archivar todo lo descargado; fallback (pipeline SAR propio) documentado pero costoso |

### 3.2 VIIRS Boat Detection (NOAA/EOG, Colorado School of Mines)

Detección nocturna de luces de barcos. La flota potera de la milla 201 pesca con lámparas de miles de watts: **VIIRS la ve aunque apague el AIS**. Producto diario, gratuito con registro en EOG. CSV/GeoJSON por fecha y región. Limitaciones: solo de noche, lo arruinan nubes y luna llena, no identifica buques individuales. Complemento perfecto del SAR, barato de ingerir.

### 3.3 aisstream.io — AIS vivo, gratis de verdad

Websocket gratuito de AIS terrestre agregado, con API key. Filtrable por bounding box. Cobertura: ~200 km de costa donde haya estaciones — Río de la Plata, litoral y buena parte de la Hidrovía razonables; milla 201, cero. Riesgo: servicio comunitario sin SLA. Mitigación: ingesta agnóstica de la fuente (mensajes AIVDM normalizados) para enchufar AISHub o receptores propios sin tocar nada río abajo.

### 3.4 AISHub — solo si ponemos fierros

Requiere contribuir una estación AIS propia (~USD 100-200, RTL-SDR + antena + techo con vista al agua). No es MVP. Una red de 3-5 receptores (Rosario, San Lorenzo, Zárate, Buenos Aires, Bahía Blanca) daría independencia total para la capa fluvial. → Fase 5.

### 3.5 MarineTraffic — descartado

API solo paga, ToS prohíben scraping y republicación. Cualquier camino es plata o juicio. Fuera.

### 3.6 OpenSky Network — ADS-B, fase 4

400 créditos/día anónimo, 4.000 registrado, 8.000 alimentando con receptor. Cobertura sudamericana pobre (receptores voluntarios concentrados en ciudades); sobre el mar, nada. Licencia no-comercial: compatible. Fuente secundaria de la capa aérea.

### 3.7 ADS-B Exchange — descartado; alternativas comunitarias sí

API paga desde su venta a JETNET (~USD 10/mes vía RapidAPI). La comunidad migró a **adsb.lol, adsb.fi y airplanes.live**: APIs gratuitas compatibles con el formato ADSBx, **datos sin filtrar — clave para la capa militar**, porque los trackers comerciales filtran aeronaves militares y estas redes no. adsb.lol primario, OpenSky secundario, receptor propio (~USD 50, único gasto de capital opcional) para cuota mejorada.

### 3.8 Sentinel-1 / Sentinel-2 (Copernicus Data Space Ecosystem)

Acceso gratuito vía CDSE (STAC/OData + tier gratuito de Sentinel Hub con cuotas). No procesamos Sentinel-1 crudo (ver §1). Uso realista: Sentinel-2 cloudless de EOX como capa base satelital (WMTS gratuito con atribución); quicklooks de escenas recientes linkeando al Copernicus Browser (fase 4); pipeline SAR propio solo como contingencia si GFW desaparece.

### 3.9 SAOCOM / CONAE

Catálogo navegable sin registro; descarga exige registro + licencia; adquisiciones nuevas, convenio. La licencia casi seguro prohíbe republicar derivados en un mapa público. Camino realista: convenio institucional con CONAE (el objetivo de soberanía les es afín). No prometer esta capa.

### 3.10 Prefectura Naval, IGN, datos.gob.ar

- **Prefectura:** sin API de posiciones; Guardacostas no es abierto. Aprovechable: normativa, jurisdicciones, **ordenanzas con zonas restringidas a la navegación** (insumo de la capa de soberanía), y pedidos de acceso a la información pública (ley 27.275) para datasets puntuales.
- **IGN:** geoservicios WMS/WFS públicos — límites, línea de costa, toponimia. La cartografía oficial argentina (Malvinas como territorio argentino) es además el amparo de las decisiones cartográficas del proyecto. Cruzar ZEE con Marine Regions (VLIZ).
- **datos.gob.ar / Min. Transporte:** datasets estáticos de puertos y tráfico de la Hidrovía; frecuencia errática; job semanal tolerante a caídas.

### 3.11 Alturas del río Paraná (Prefectura / INA / AGP) — nueva en v2

Prefectura publica el registro de alturas de los ríos en su web (contenidosweb.prefecturanaval.gob.ar/alturas), el INA opera el sistema de alerta hidrológico de la cuenca, y la AGP mantiene **59 hidrómetros en la Vía Navegable Troncal**. No hay API formal: es scraping ligero de tablas públicas (legalmente tranquilo: dato público oficial, citando fuente). Capa de contexto para la Hidrovía: altura en cada puerto, tendencia, y correlación con el tráfico (la bajante condiciona cuánto cargan los buques). Job cada 6 hs.

### Matriz fuente → capa

| Capa del mapa | Fuente | Latencia real | Costo |
|---|---|---|---|
| AIS vivo Hidrovía/costa | aisstream.io | segundos-minutos | $0 |
| Esfuerzo pesquero ZEE | GFW 4Wings | 72 hs | $0 + atribución |
| Buques *dark* milla 201/Malvinas | GFW SAR detections | ~5 días | $0 + atribución |
| Luces flota potera | VIIRS VBD | ~24 hs | $0 + registro |
| **Alarma apagado AIS** | GFW events (gaps) + detector propio | 72 hs / NRT costero | $0 + atribución |
| **Aeronaves (incl. militares)** | adsb.lol / OpenSky | segundos | $0 |
| **Soberanía** (bases, FICZ/FOCZ, AMPs, zonas restringidas) | OSM, Marine Regions, Prefectura, fuentes públicas | estático | $0 |
| Alturas del Paraná | Prefectura/INA/AGP | horas | $0 |
| Contexto (ZEE, límites, puertos) | IGN, Marine Regions, datos.gob.ar | estático | $0 |

---

## 3-bis. Capa militar y de soberanía

Requisito central del proyecto: Argentina tiene parte de su territorio ocupado y el mapa debe aportar a la vigilancia ciudadana de la soberanía. Qué se puede mostrar de verdad, sin humo:

### Lo que SÍ es captable con datos abiertos

- **Aeronaves militares vía ADS-B comunitario sin filtrar.** El puente aéreo de la RAF entre Brize Norton y Mount Pleasant (A330 Voyager de AirTanker, ~2 vuelos semanales) **es visible en los trackers** — verificado. adsb.lol/airplanes.live no filtran aeronaves militares (los trackers comerciales sí). Identificación: rangos de ICAO hex asignados a fuerzas armadas + bases de datos comunitarias de aeronaves militares (las que usa tar1090). Política decidida: **todo lo captable, de cualquier fuerza, sin filtrar** — incluidas las argentinas. Limitación honesta: muchas aeronaves militares vuelan con transponder apagado o en modo no-ADS-B; lo que se ve es una fracción.
- **Detecciones SAR no correlacionadas alrededor de Malvinas.** Los buques de guerra no transmiten AIS, pero el radar de Sentinel-1 los ve igual que a cualquier casco metálico. La capa SAR de GFW cubre el área; se agrega una **vista dedicada Malvinas/Atlántico Sur** con zoom y permalink propios.
- **La economía de la ocupación:** zonas de pesca licenciada por el gobierno de las islas (FICZ/FOCZ) como polígonos estáticos + la actividad pesquera GFW dentro de ellas. Mostrar quién pesca con licencia de quién, dentro de la ZEE argentina, es probablemente la capa de soberanía más elocuente y es 100% datos ya disponibles.

### Capas estáticas de soberanía (baratas, MVP)

- Bases militares **propias y extranjeras**: Mount Pleasant (aérea + puerto de Mare Harbour), bases navales y aéreas argentinas — de fuentes públicas/OSM. Son puntos/polígonos estáticos con ficha informativa.
- Límites de navegación y zonas restringidas (ordenanzas de Prefectura), zonas de practicaje de la Hidrovía.
- Áreas marinas protegidas: Namuncurá–Burdwood I y II, Yaganes, y el área del **Agujero Azul** — contexto de por qué importa lo que pasa en cada zona.

### Advertencias que la UI debe dar

- Ausencia en el mapa ≠ ausencia real: los buques de guerra son invisibles al AIS y las aeronaves militares pueden apagar el transponder. El mapa muestra la fracción observable.
- La información mostrada proviene de señales transmitidas públicamente y sensores civiles abiertos — es legal, pero la capa debe presentarse como información, no como inteligencia operativa.

---

## 3-ter. Sistema de alarmas: apagado de AIS + log de eventos

Feature confirmada. Diseño:

### Fuentes de detección

1. **GFW Events API, tipo "gaps":** apagados de AIS considerados intencionales, de alta confianza (el buque debe tener ≥14 posiciones satelitales en las 12 hs previas al gap — el filtro lo hace GFW). Cubre ZEE + borde de milla 201. **Delay 72 hs**: es una alarma forense ("este buque apagó el AIS el martes"), no táctica. La UI lo declara.
2. **Detector propio sobre el AIS costero/fluvial** que ya ingerimos: si un buque que veníamos viendo en la Hidrovía/litoral deja de transmitir sin llegar a puerto ni salir del área de cobertura, se genera un evento propio — este sí **near real-time**, con la cautela de que la pérdida de señal terrestre tiene causas inocentes (sombra de cobertura, clima). Se etiqueta con confianza menor que los de GFW.

### El log: registro intuitivo y permanente

- Cada evento (apagado, reaparición, encuentro, loitering) se persiste con: buque (identidad + disclaimer), posición del último contacto, timestamp, duración del gap, zona (ZEE / milla 201 / FICZ / Hidrovía), fuente y nivel de confianza.
- UI: panel "últimos apagones" en el mapa + **cronología navegable** filtrable por zona, buque, bandera y fecha, con **permalink por evento** (citable por periodistas) y mini-mapa del último track conocido.
- Persistencia: tabla en Postgres (es chica: decenas de eventos/día) + export mensual a R2 y al repo. El log nunca se borra: es la memoria del proyecto.

---

## 4. Stack tecnológico recomendado

| Capa | Elección | Alternativas descartadas y por qué |
|---|---|---|
| Mapa frontend | **MapLibre GL JS** | *Mapbox GL JS*: licencia paga desde v2. *Leaflet*: se ahoga con miles de puntos móviles, sin vector tiles nativo decente. *OpenLayers*: capaz pero DX más áspera. *deck.gl*: como overlay futuro sobre MapLibre, no como base |
| Framework UI | **React + Vite, SPA estática** | *Next.js/SSR*: el contenido es un canvas, SSR suma infra sin beneficio. *Svelte*: válido; el ecosistema de componentes de mapas inclina a React, pero no es pelea que valga la pena |
| Hosting frontend | **Vercel free** | *Cloudflare Pages*: equivalente y válido como plan B; Vercel elegido por preferencia del usuario y porque la cuenta ya existe |
| Backend / API | **Python + FastAPI en la VM Oracle always-free** | *Funciones serverless de Vercel*: no sostienen el websocket de ingesta ni PostGIS. *Node/Go*: pierden el ecosistema geoespacial de Python sin ganar nada necesario |
| Jobs batch | **GitHub Actions cron (repo público, gratis)** | *Celery/Airflow*: absurdo para ~6 jobs. *Cron en la VM*: válido, pero Actions deja los pipelines versionados y con logs públicos — transparencia también del proceso |
| Base de datos | **Supabase free (Postgres + PostGIS, 500 MB)**, hot data solamente | *Neon*: similar, PostGIS menos llave en mano. *Postgres en la VM Oracle*: el plan B natural si el límite de 500 MB aprieta (elimina un proveedor). *Mongo/Elastic*: geoespacial de segunda vs PostGIS |
| Archivo frío | **Cloudflare R2 free (10 GB)** en parquet/PMTiles + copias en el repo | *Pagar S3*: viola la restricción $0. *Solo el repo*: GitHub no es object storage; se usa como respaldo, no como primario |
| Tiles dinámicos | **ST_AsMVT desde PostGIS** servido por FastAPI, caché Cloudflare | *martin/pg_tileserv*: otro proceso que operar; migrable después si hace falta |
| Tiles estáticos | **PMTiles en R2 + CDN** | Tile server para capas que cambian una vez al año: no |
| Basemap | **Protomaps (OSM, PMTiles) + EOX Sentinel-2 cloudless** | *Google/Mapbox*: costo. *Tiles públicos de OSM*: prohibidos para producción |
| Observabilidad | **Uptime Kuma en la VM + healthchecks de Actions** | Stack Prometheus completo: después, si hay equipo |

**Justificación transversal:** la restricción de USD 0 ya no es una preferencia sino un requisito; cada elección la respeta y además minimiza el daño si un proveedor gratuito cambia las reglas (todo dato persistente vive en R2 + repo, toda pieza es recreable por código en <1 hora).

---

## 5. Riesgos y limitaciones conocidos

### Técnicos
- **Dependencia crítica de GFW** (SAR + altamar + alarma de gaps). Mitigación: archivo local de todo, fallback documentado, buscar relación formal con GFW.
- **Fragilidad doble: servicios comunitarios + free tiers.** aisstream.io y adsb.lol no tienen SLA; Oracle/Supabase/Vercel pueden cambiar condiciones. Mitigación: ingesta agnóstica de fuente, infra como código, datos siempre en R2 + repo, keep-alives.
- **Límite de 500 MB en Postgres**: obliga a disciplina de retención desde el día 1 (hot 7-14 días, resto a parquet). Plan B: PostGIS en la VM.
- **Rate limits**: presupuesto de requests por job + circuit breaker para no quemar la cuota diaria de GFW por un bug.

### De datos (a comunicar en la UI)
- AIS es **autoreportado y falsificable** (spoofing de posición e identidad es práctica conocida de la flota observada). El mapa muestra "lo que los barcos dicen", no "lo que es".
- SAR/VIIRS tienen **falsos positivos** y la revisita de Sentinel-1 deja días sin cobertura — ausencia de detección ≠ ausencia de barco.
- La alarma de gaps de GFW llega con 72 hs: **forense, no táctica**.
- La capa militar muestra **solo la fracción observable**: buques de guerra sin AIS, aeronaves con transponder apagado no aparecen.

### Legales y de uso
- Licencias no-comerciales de GFW/OpenSky: **compatibles** con la decisión $0/sin publicidad/sin cobro. Atribución obligatoria en todo.
- **Riesgo de difamación práctica**: el mapa muestra *actividad aparente*, no delitos. Identidad de buques se muestra (decisión tomada) con disclaimer prominente y nombres de capas cuidados ("detección no correlacionada con AIS", no "barco pirata").
- **Sensibilidad geopolítica**: milla 201, flota mayormente china, Malvinas, y ahora una capa militar explícita. Amparo: cartografía oficial del IGN, señales transmitidas públicamente, sensores civiles abiertos. Aún así: el proyecto va a incomodar; documentar la legalidad de cada fuente en la página de metodología.
- **Aeronaves estatales/militares**: política decidida — todo lo captable, sin filtrar, incluidas las argentinas. Es la posición coherente con la transparencia; el costo de fricción se asume.

### De sostenibilidad
- El riesgo real n.º 1: **proyecto de una persona que se queda sin tiempo**. Mitigación: stack mínimo, código abierto desde el día 1, pipelines visibles en Actions, documentación de operación, y buscar socio institucional antes de la fase 3.

---

## 6. Roadmap de implementación

Fases con criterios de completitud verificables, sin fechas.

**Fase 0 — Fundaciones y permisos.**
Completa cuando: tokens de GFW, EOG (VIIRS) y aisstream.io obtenidos y probados sobre la ZEE; cuentas free tier creadas (Vercel, Supabase, Oracle, R2) y cada pieza levantada vacía por código; repo público con licencia; ToS de GFW verificados contra el modelo $0.

**Fase 1 — Mapa base con contexto y soberanía.**
Completa cuando: sitio público en Vercel con basemap, ZEE, milla 200, Hidrovía, puertos, **bases militares, FICZ/FOCZ, AMPs y Agujero Azul** como PMTiles desde R2; carga <3 s en móvil mediocre; página de metodología publicada.

**Fase 2 — Capas satelitales (el diferencial).**
Completa cuando: jobs de Actions (GFW heatmap, SAR detections, eventos, VIIRS) corren solos hace 2 semanas; capas visibles con timestamp; click en detección SAR distingue *matched* vs *dark*; vista dedicada Malvinas/Atlántico Sur funcionando; atribuciones correctas.

**Fase 3 — AIS en vivo + alarma de apagado + memoria.**
Completa cuando: posiciones de aisstream.io en el mapa con <2 min de latencia, archivadas hace 2 semanas sin pérdida y con retención/export a R2 funcionando; **log de eventos navegable publicado, alimentado por los gaps de GFW, con permalinks**; ficha de buque con identidad cruzada GFW + disclaimer; el sistema sobrevivió una caída del websocket reconectando solo.

**Fase 4 — Capa aérea (incl. militar) + profundidad temporal.**
Completa cuando: tráfico ADS-B (adsb.lol primario, OpenSky fallback) visible con identificación de aeronaves militares por hex/base de datos y disclaimer de cobertura; **detector propio de gaps costeros near real-time alimentando el log**; alturas del Paraná en los puertos de la Hidrovía; selector temporal sobre el histórico SAR/VIIRS/heatmap; quicklinks a imágenes Copernicus.

**Fase 5 — Independencia y comunidad.**
Completa cuando: ≥2 receptores AIS propios alimentando (AISHub desbloqueado de bonus); guía publicada para montar receptores; conversación formal iniciada con CONAE (SAOCOM) y/o GFW. Opcional y condicionada a tracción real.

---

## 6-bis. Ideas para sumar utilidad (propuestas, a priorizar después del MVP)

Pedido explícito del usuario: cosas que encajan con la idea y no estaban en la lista original.

1. **Alturas del Paraná + bajante** (ya incorporada, §3.11): correlacionar nivel del río con tráfico de la Hidrovía — la bajante es noticia recurrente y nadie la muestra junto al tráfico.
2. **Cruce con listas IUU públicas**: marcar buques que figuran en las listas de pesca ilegal de las ORPs (CCAMLR, etc.) y registros públicos de infractores. Convierte "un punto en el mapa" en "un punto con prontuario", con fuentes citables.
3. **Panel de estadísticas**: buques *dark* esta semana vs histórica, intensidad de la zafra del calamar, apagones de AIS por mes. Los números agregados son lo que los medios citan.
4. **Datos abiertos de salida**: export GeoJSON/CSV de cada capa y una API pública documentada. El proyecto consume datos abiertos; debe producirlos también — multiplica el impacto sin multiplicar el trabajo.
5. **Widgets embebibles**: un iframe del mapa con una capa/zona preconfigurada para que medios y ONGs lo incrusten. Distribución gratis.
6. **Capa de prospección sísmica/petrolera offshore**: los buques sísmicos transmiten AIS y las áreas concesionadas son públicas (Secretaría de Energía). Tema ambiental caliente (Mar Argentino) que encaja con la misión.
7. **Modo educativo**: "¿qué es la milla 201?", "¿por qué la flota se estaciona justo afuera?", "¿qué es un buque dark?" — tooltips y una página narrativa. Para el ciudadano que llega por primera vez, el contexto vale más que el dato.
8. **Efemérides georreferenciadas**: capa curada de incidentes históricos (hundimientos de pesqueros ilegales, ARA San Juan, incidentes en la milla 201) con fuentes. Convierte el mapa en memoria, no solo presente.

---

## 7. Preguntas que siguen abiertas

Resueltas en v2: financiamiento ($0, sin publicidad, sin cobro), identidad de buques (sí, con disclaimer), capa militar (todo lo captable + capas estáticas de soberanía), alarmas (mapa + log). Quedan:

1. **Audiencia primaria.** ¿Ciudadano general, periodistas, ONGs? Cambia el lenguaje de la UI y si hace falta inglés además del castellano.
2. **Compromiso público de histórico.** Guardar todo es barato; *prometer* acceso público a todo el histórico es un compromiso. ¿Histórico navegable prometido o archivo interno hasta ver costos reales en R2?
3. **Nombre, dominio y marca.** "Soberana" es el repo — ¿es el nombre del producto? Define dominio (el dominio es el único costo anual inevitable, ~USD 10-15/año, salvo subdominio gratuito de Vercel) y cómo se presenta el proyecto ante GFW/CONAE.
4. **¿Apetito institucional?** ¿Llegada a alguna universidad, ONG o medio que co-firme? Cambia la fase 5 y la conversación con CONAE de "imposible" a "posible".
5. **Priorización de las ideas de §6-bis** una vez que el MVP esté en producción.

---

## Apéndice — Referencias verificadas (junio 2026)

- GFW API: 50 K req/día, delay 72 hs, atribución obligatoria; Events API incluye gaps de AIS de alta confianza considerados intencionales (≥14 posiciones satelitales en las 12 hs previas).
- GFW SAR detections: dataset Sentinel-1 2017→presente (~5 días de lag), vía 4Wings API.
- aisstream.io: websocket gratuito, cobertura ~200 km de costa.
- ADS-B Exchange: API solo paga desde 2023/2025; adsb.lol/airplanes.live exponen APIs gratuitas compatibles y sin filtrar.
- OpenSky: 400/4.000/8.000 créditos/día (anónimo/registrado/feeder); cobertura sudamericana con huecos.
- Puente aéreo RAF Brize Norton ↔ Mount Pleasant: A330 Voyager (AirTanker), ~2 vuelos/semana, visible en trackers ADS-B (MPN/EGYP listado en Flightradar24).
- SAOCOM: catálogo navegable sin registro; descarga requiere registro + licencia CONAE; adquisiciones nuevas, convenio.
- VIIRS Boat Detection: producto diario de EOG (Colorado School of Mines), registro gratuito.
- Alturas de ríos: Prefectura (contenidosweb.prefecturanaval.gob.ar/alturas), INA (alerta hidrológico), AGP (59 hidrómetros en la Vía Navegable Troncal).
