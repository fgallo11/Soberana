# Soberana — Plan de proyecto

**Mapa público de actividad marítima, fluvial y aérea en territorio argentino**
Foco: Hidrovía Paraná-Paraguay, Zona Económica Exclusiva (ZEE) y milla 201.
Objetivo: transparencia ciudadana — cualquier persona abre el mapa y entiende qué está pasando, sin cuenta ni conocimiento técnico.

> Documento de planificación. No hay código todavía. Fecha: junio 2026.

---

## 0. La verdad incómoda primero

Antes del plan, tres realidades que condicionan todo lo demás. Si no las aceptamos, el proyecto promete algo que no puede cumplir:

1. **"Tiempo real" en la milla 201 no existe gratis.** El AIS terrestre llega a ~200 km de la costa como máximo; la milla 201 está a ~370 km. Lo que pasa ahí solo se ve por AIS satelital (Spire, ORBCOMM — comercial, miles de USD/mes) o por las fuentes derivadas que publica Global Fishing Watch **con 72 horas de retraso**. El mapa va a ser *near real-time* en la Hidrovía y la costa, y *delayed* (72 hs a 5 días) en altamar. Hay que decirlo en la UI, no esconderlo.

2. **Los barcos que más interesan son justamente los que no transmiten.** La flota potera que pesca pegada a la milla 201 apaga el AIS o transmite intermitentemente. Para verlos hacen falta sensores que no dependen de cooperación del buque: SAR (Sentinel-1) y luces nocturnas (VIIRS). Ambos existen gratis y procesados — esa es la apuesta central del proyecto, no el AIS.

3. **Las fuentes "oficiales" argentinas no tienen APIs.** Prefectura no publica posiciones. El sistema Guardacostas no es público. SAOCOM requiere licencia y casi seguro prohíbe republicación. El plan no puede depender de que el Estado coopere; si después coopera, mejor.

---

## 1. Alcance y definición del MVP

### Qué ES el producto

Un mapa web estático-más-API, público, sin login, que superpone capas de actividad sobre el territorio marítimo/fluvial argentino, con la fecha/hora de cada dato visible y un selector temporal simple. No es una plataforma de inteligencia, no tiene alertas, no identifica "culpables".

### MVP (primera versión funcional)

| Incluye | Detalle |
|---|---|
| Capas estáticas de contexto | ZEE, límite milla 200/201, línea de base, traza de la Hidrovía troncal, puertos principales, límites IGN |
| Esfuerzo pesquero (GFW) | Heatmap de actividad pesquera aparente, últimos 30 días, delay 72 hs |
| **Detecciones SAR (GFW)** | Buques detectados por Sentinel-1, clasificados *matched* (con AIS) vs *dark* (sin AIS) — la capa estrella para milla 201 |
| **Luces nocturnas (VIIRS VBD)** | Detección de luces de barcos (flota potera) — actualización diaria |
| AIS en vivo costero/fluvial | Posiciones vía aisstream.io para Hidrovía + litoral, websocket → mapa |
| Ficha de buque básica | Nombre, MMSI, bandera, tipo — de los metadatos AIS y la API de vessels de GFW |
| Transparencia metodológica | Página "qué estás viendo y qué no": fuentes, delays, cobertura, limitaciones |

### Explícitamente FUERA del MVP (y por qué)

- **Capa aérea (ADS-B):** la cobertura comunitaria en Argentina es rala y sobre el mar es prácticamente nula (no hay receptores en altamar; ADS-B satelital es Aireon = comercial). Sumarla al MVP agrega complejidad y entrega poco valor sobre la zona de interés. → Fase 4.
- **Procesamiento SAR propio (Sentinel-1 crudo → detección de barcos):** pipeline pesado (SNAP/CFAR o deep learning, decenas de GB por escena). GFW ya lo hace y lo publica por API. Construirlo nosotros sería reinventar peor algo que existe. → Solo si algún día GFW corta el acceso.
- **SAOCOM:** la licencia de uso de CONAE casi seguro impide republicar productos en un mapa público; requiere convenio. → Fase de partnership, no técnica.
- **Histórico navegable / playback temporal completo:** valioso pero no mínimo. Eso sí: **se almacena todo desde el día 1** (el dato AIS en vivo que no guardás hoy no lo recuperás nunca).
- **Alertas/notificaciones, cuentas de usuario, análisis automático de comportamiento sospechoso:** terreno resbaladizo legal y editorialmente; requiere definiciones del punto 7.
- **MarineTraffic:** descartado (ver §3).

### Criterio de éxito del MVP

Una persona sin contexto abre el sitio, ve la ZEE, ve la mancha de la flota pesquera sobre la milla 201 (SAR + VIIRS + heatmap GFW), ve barcos moviéndose en vivo por el Paraná, y entiende —porque la UI se lo dice— qué dato es de hace 5 minutos y cuál de hace 3 días.

---

## 2. Arquitectura del sistema

### Principio rector

**Un monolito modesto con jobs programados.** No hay Kafka, no hay Kubernetes, no hay microservicios. Los volúmenes lo justifican: la Hidrovía + litoral son cientos a pocos miles de buques simultáneos; las capas satelitales se actualizan entre 1 vez por día y 1 vez cada 72 hs. Esto entra cómodo en un VPS de USD 20/mes. Cada capa de infraestructura extra es costo de mantenimiento para un proyecto que probablemente sostenga una persona o un grupo chico.

### Componentes

```
┌─────────────────────────────────────────────────────────────┐
│ INGESTA (procesos en el mismo host)                          │
│                                                              │
│  [ws-consumer]  aisstream.io websocket ──► normaliza ──┐     │
│  [job 6h]      GFW 4Wings (heatmap, SAR detections) ──►│     │
│  [job 6h]      GFW events (encuentros, loitering) ────►│     │
│  [job 24h]     VIIRS VBD (luces nocturnas) ───────────►│     │
│  [job semanal] catálogos estáticos (IGN, puertos) ────►│     │
└────────────────────────────────────────────────────────┼─────┘
                                                         ▼
                                          ┌──────────────────────┐
                                          │ PostgreSQL + PostGIS │
                                          │  - posiciones (hot)   │
                                          │  - histórico (cold,   │
                                          │    particionado/día)  │
                                          │  - detecciones SAR/   │
                                          │    VIIRS, eventos     │
                                          └──────────┬───────────┘
                                                     ▼
┌─────────────────────────────────────────────────────────────┐
│ SERVING                                                      │
│  API HTTP (FastAPI):                                         │
│   - GET /vessels?bbox=...        → GeoJSON posiciones vivas  │
│   - GET /detections/{layer}/{z}/{x}/{y}.mvt → tiles vector   │
│   - WS  /live                    → push de posiciones        │
│   - proxy autenticado a tiles GFW (el token NUNCA al cliente)│
│  Archivos estáticos:                                         │
│   - capas de contexto como PMTiles en CDN (sin tile server)  │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
              ┌─────────────────────────┐
              │ FRONTEND (SPA estática)  │
              │ MapLibre GL JS           │
              │ basemap: OSM/Protomaps + │
              │ EOX Sentinel-2 cloudless │
              └─────────────────────────┘
```

### Flujo de datos punta a punta (ejemplo: capa SAR)

1. Job cada 6 hs llama a la 4Wings API de GFW pidiendo detecciones SAR de los últimos N días sobre un bbox que cubre ZEE + margen.
2. Normalización a un esquema propio (`detection{source, ts, geom, matched, score, vessel_ref}`) e inserción idempotente en PostGIS.
3. El endpoint de tiles genera MVT directamente desde PostGIS (`ST_AsMVT`), con caché HTTP agresivo (los datos cambian cada 6 hs, el tile puede cachearse 1 h en CDN).
4. El frontend pinta la capa con estilo distinto para *matched* (gris) vs *dark* (rojo), y muestra el timestamp de la detección al clickear.

### Decisiones de arquitectura y sus trade-offs

- **Guardar copia local de todo vs. proxear APIs de terceros:** se guarda copia local (salvo el heatmap de GFW, que conviene proxear como tiles). Razones: resiliencia ante caídas/cambios de ToS de los proveedores, capacidad de histórico propio, y control de rate limits (un usuario del mapa no consume cuota de GFW; la consume nuestro job una vez). Costo: hay que mantener jobs y migraciones de esquema. Vale la pena.
- **Websocket propio para AIS vivo vs. polling del frontend:** MVP arranca con **polling cada 30-60 s** (`GET /vessels?bbox`). Un websocket propio es mejor UX pero suma estado en el servidor y reconexión en el cliente; se agrega en fase 3 si el polling queda corto. No optimizar antes de tener usuarios.
- **PMTiles para capas estáticas:** un solo archivo en un bucket/CDN, sin tile server corriendo. Para ZEE, límites y la traza de la Hidrovía (que cambian nunca o casi nunca) es la opción de menor mantenimiento que existe.

---

## 3. Análisis de cada fuente de datos

Orden: de más a menos útil para este proyecto.

### 3.1 Global Fishing Watch — ⭐ columna vertebral

| Aspecto | Realidad |
|---|---|
| Acceso | API REST v3 gratuita con registro y token. Rate limit: **50.000 req/día, 1.55 M/mes** — sobra para jobs server-side, jamás exponer el token al navegador |
| Datos | 4Wings (rásteres de esfuerzo pesquero, presencia AIS, **detecciones SAR de Sentinel-1 2017→hace ~5 días, clasificadas con deep learning, matcheadas contra AIS**), eventos (encuentros entre buques, *loitering*, visitas a puerto, gaps de AIS), identidad de buques |
| Frecuencia | AIS con **delay de 72 hs**; SAR según revisita de Sentinel-1 sobre el Atlántico Sur (~6-12 días por punto) |
| Formato | JSON, tiles 4Wings (PNG/MVT), CSV por data portal |
| Restricciones | Atribución obligatoria en todo lo publicado. Términos orientados a uso no comercial / bien público — **hay que leer los ToS con el modelo de financiamiento decidido** (ver §7) |
| Trade-off brutal | Es una dependencia única para lo más valioso del mapa (SAR + eventos + altamar). Si GFW cambia términos o cierra la API, perdemos la capa estrella. Mitigación: guardar todo lo descargado; el fallback (pipeline SAR propio sobre Copernicus) existe pero es un proyecto en sí mismo |

### 3.2 VIIRS Boat Detection (NOAA/EOG, Colorado School of Mines) — propuesta nuestra, no estaba en tu lista

Detección nocturna de luces de barcos. La flota potera que opera en la milla 201 pesca con lámparas de miles de watts: **VIIRS la ve aunque apague el AIS**. Producto diario, gratuito con registro en EOG. Formato CSV/GeoJSON por fecha y región. Limitaciones: solo de noche, lo arruinan las nubes y la luna llena, no identifica buques individuales. Es el complemento perfecto del SAR: barato de ingerir (un CSV por día) y de altísimo valor narrativo para el público.

### 3.3 aisstream.io — AIS vivo, gratis de verdad

Websocket gratuito de AIS terrestre agregado, con API key, sin tarjeta. Filtrable por bounding box y tipo de mensaje. Cobertura: **~200 km de costa donde haya estaciones** — el Río de la Plata, el litoral y buena parte de la Hidrovía tienen cobertura razonable; la milla 201, cero. Riesgos: es un servicio comunitario sin SLA; puede degradarse o desaparecer. Mitigación: el esquema de ingesta debe ser agnóstico de la fuente AIS (mensajes NMEA/AIVDM normalizados), para poder enchufar AISHub o receptores propios después sin tocar nada río abajo.

### 3.4 AISHub — solo si ponemos fierros

Requiere **contribuir datos de una estación AIS propia** para acceder al feed agregado. Una estación cuesta ~USD 100-200 (RTL-SDR + antena) y necesita techo con vista al agua. No es MVP, pero una red de 3-5 receptores propios en Rosario, San Lorenzo, Zárate, Buenos Aires y Bahía Blanca daría independencia total de terceros para la capa fluvial, acceso a AISHub de yapa, y es una historia linda de ciencia ciudadana (gente donando cobertura). → Fase 5.

### 3.5 MarineTraffic — descartado

No tiene API gratuita: es de pago por créditos, cara, y sus ToS prohíben explícitamente el scraping y la republicación. El widget embebible no se integra con nuestras capas. Cualquier camino con MarineTraffic es plata o juicio. Fuera.

### 3.6 OpenSky Network — ADS-B, fase 4

API REST gratuita: 400 créditos/día anónimo, 4.000 registrado, 8.000 si alimentás con receptor propio. Con polling de un bbox argentino cada ~60 s, la cuota registrada alcanza justo. Cobertura en Sudamérica: pobre — depende de receptores voluntarios concentrados en AMBA y algunas ciudades. Sobre el mar: nada. Licencia: uso no comercial/investigación. Honesto: la capa aérea va a mostrar tráfico comercial sobre el continente y poco más; los vuelos de patrullado marítimo lejos de la costa no van a aparecer salvo suerte.

### 3.7 ADS-B Exchange — descartado; alternativas comunitarias sí

Desde su venta a JETNET, la API es paga (RapidAPI, ~USD 10/mes por 10 K requests, sin tier gratuito). La comunidad que se fue de ADSBx armó **adsb.lol, adsb.fi y airplanes.live**: APIs gratuitas, compatibles con el formato ADSBx (drop-in), datos sin filtrar. Misma limitación de cobertura que OpenSky (son los mismos voluntarios). Plan: adsb.lol como fuente primaria de la fase 4, OpenSky como secundaria, y un receptor propio (~USD 50) si queremos cuota mejorada y cobertura local garantizada.

### 3.8 Sentinel-1 / Sentinel-2 (Copernicus Data Space Ecosystem)

Acceso gratuito vía CDSE: APIs STAC/OData para descarga, y un tier gratuito de Sentinel Hub APIs (con cuotas de processing units) para tiles al vuelo. **No vamos a procesar Sentinel-1 crudo en el MVP** (ver §1). Uso realista:
- **Sentinel-2 cloudless de EOX** como capa base satelital (WMTS gratuito con atribución, mosaico anual — contexto, no actualidad).
- Quicklooks de escenas recientes S-1/S-2 sobre un punto de interés, linkeando al Copernicus Browser ("mirá la imagen vos mismo"), como feature de fase 4: barato y útil.
- Pipeline SAR propio: solo como plan de contingencia documentado si GFW desaparece.

### 3.9 SAOCOM / CONAE

El catálogo es navegable sin registro (búsqueda + thumbnails), pero descargar productos exige registro y **aceptar una licencia de uso**; adquisiciones nuevas requieren convenio con CONAE. La banda L de SAOCOM es excelente para mar, pero: (a) la licencia casi seguro prohíbe republicar derivados en un mapa público sin convenio, (b) no hay API de programación amigable para automatizar. Camino realista: **gestión institucional** — proponerle a CONAE un convenio de colaboración (el objetivo de soberanía sobre el mar argentino les es afín). Hasta que eso exista, SAOCOM no entra en el roadmap técnico. No prometer esta capa.

### 3.10 Prefectura Naval, IGN, datos.gob.ar

- **Prefectura:** sin API pública; Guardacostas no es abierto. Lo único aprovechable: normativa, jurisdicciones, y eventualmente pedidos de acceso a la información pública (ley 27.275) para datasets puntuales. No es una fuente de datos en vivo y el plan no depende de ella.
- **IGN:** geoservicios WMS/WFS públicos y estables — límites, línea de costa, toponimia. Para la ZEE conviene cruzar con Marine Regions (VLIZ) que publica los polígonos de ZEE del mundo en formatos cómodos. Ingesta única, capa estática.
- **datos.gob.ar / Min. Transporte:** datasets estáticos de puertos, tráfico de la Hidrovía, cargas. Útiles para contexto y fichas de puertos; frecuencia de actualización errática. Capa estática refrescada por job semanal/mensual con tolerancia a que el endpoint se caiga (pasa seguido).

### Resumen de la matriz fuente → capa

| Capa del mapa | Fuente | Latencia real | Costo |
|---|---|---|---|
| AIS vivo Hidrovía/costa | aisstream.io | segundos-minutos | $0 |
| Esfuerzo pesquero ZEE | GFW 4Wings | 72 hs | $0 + atribución |
| Buques *dark* milla 201 | GFW SAR detections | ~5 días | $0 + atribución |
| Luces flota potera | VIIRS VBD | ~24 hs | $0 + registro |
| Eventos (encuentros, gaps) | GFW events | 72 hs | $0 + atribución |
| Tráfico aéreo (fase 4) | adsb.lol / OpenSky | segundos | $0 |
| Contexto (ZEE, límites, puertos) | IGN, Marine Regions, datos.gob.ar | estático | $0 |

---

## 4. Stack tecnológico recomendado

| Capa | Elección | Alternativas descartadas y por qué |
|---|---|---|
| Mapa frontend | **MapLibre GL JS** | *Mapbox GL JS*: licencia paga desde v2, mismo origen de código. *Leaflet*: se ahoga renderizando miles de puntos en movimiento y no tiene vector tiles nativo decente. *OpenLayers*: capaz pero DX más áspera y comunidad menor para este caso de uso. *deck.gl*: excelente para visualización masiva, pero como overlay sobre MapLibre cuando haga falta (fase de histórico), no como base |
| Framework UI | **React + Vite, SPA estática** | *Next.js/SSR*: el contenido es un mapa, no hay nada que renderizar en servidor; SSR suma infra sin beneficio SEO real para un canvas. *Svelte*: válido y más liviano, pero el ecosistema de componentes de mapas (react-map-gl, etc.) inclina la balanza. Si el equipo prefiere Svelte, no es una pelea que valga la pena dar |
| Backend / API | **Python + FastAPI** | *Node*: empata en websockets, pierde en ecosistema geoespacial (shapely, pyproj, rasterio) que vamos a necesitar para normalización. *Go*: performance que no necesitamos al costo de velocidad de desarrollo. *Django*: ORM y admin no aportan; GeoDjango es pesado para una API fina |
| Base de datos | **PostgreSQL + PostGIS**, particionado por día en la tabla de posiciones | *TimescaleDB*: tentador para series temporales, pero es una extensión más que administrar y el particionado nativo de Postgres alcanza para los volúmenes esperados (~1-5 M posiciones/día peor caso). Revisar si el histórico crece 10×. *MongoDB/Elastic*: geoespacial de segunda categoría vs PostGIS, que es el estándar de oro |
| Tiles dinámicos | **ST_AsMVT desde PostGIS** servido por FastAPI, caché en CDN | *martin/pg_tileserv*: otro proceso que operar; con 4-5 capas dinámicas, una query MVT en el propio backend es menos piezas. Migrar a martin si el tileado se vuelve cuello de botella (es un cambio barato después) |
| Tiles estáticos | **PMTiles en object storage + CDN** | *Tile server propio para capas que cambian una vez por año*: no |
| Jobs | **APScheduler dentro del proceso (o systemd timers)** | *Celery + Redis*: broker, workers, monitoreo — para correr 4 cron jobs es absurdo. *Airflow*: lo mismo elevado al cubo |
| Basemap | **Protomaps (OSM, self-hosted PMTiles) + EOX Sentinel-2 cloudless** | *Google/Mapbox tiles*: costo y términos. *OSM tile servers públicos*: prohibido para tráfico de producción por su política de uso |
| Hosting | **1 VPS (Hetzner/DO ~USD 20/mes) + Cloudflare gratis delante + object storage para PMTiles/backups** | *AWS/GCP serverless*: el websocket de ingesta AIS es un proceso permanente, no encaja en lambdas; y el costo se vuelve impredecible justo cuando el mapa sale en la prensa y explota el tráfico. Con CDN agresivo delante, un VPS aguanta picos de lectura tranquilamente |
| Observabilidad | **Uptime Kuma + logs estructurados; Grafana si duele** | Stack Prometheus completo: después, si hay equipo |

**Justificación transversal:** cada elección minimiza piezas operativas, porque el riesgo número uno de un proyecto cívico sin financiamiento es morir por costo de mantenimiento, no por falta de features. Todo lo descartado es re-incorporable más adelante sin reescritura: martin reemplaza al endpoint MVT, deck.gl se monta sobre MapLibre, Timescale se instala sobre el mismo Postgres.

---

## 5. Riesgos y limitaciones conocidos

### Técnicos
- **Dependencia crítica de GFW** (single point of failure para SAR + altamar). Mitigación: archivo local de todo, fallback documentado, relación formal con GFW (tienen programa de partners).
- **Fragilidad de servicios comunitarios** (aisstream.io, adsb.lol) — sin SLA, pueden morir un martes. Mitigación: capa de ingesta agnóstica de la fuente + plan de receptores propios.
- **Rate limits**: bien manejados server-side, pero un bug en un job puede quemar la cuota diaria de GFW. Mitigación: presupuesto de requests por job, circuit breaker.
- **Crecimiento del histórico**: AIS guardado desde el día 1 crece sin parar. Mitigación: particionado + degradación a posiciones submuestreadas después de N meses + parquet en object storage frío.

### De datos (los que hay que comunicar en la UI)
- AIS es **autoreportado y falsificable**: spoofing de posición e identidad es práctica conocida de la flota que justamente queremos observar. El mapa muestra "lo que los barcos dicen", no "lo que es".
- Detecciones SAR/VIIRS tienen **falsos positivos** (rocas, oleaje, ruido) y la revisita de Sentinel-1 en el Atlántico Sur deja días sin cobertura — ausencia de detección ≠ ausencia de barco.
- El delay de 72 hs de GFW significa que el mapa **no sirve para reaccionar**, sirve para entender patrones. Decirlo.

### Legales y de uso
- **ToS de GFW y OpenSky son no-comerciales**: si el proyecto se financia con publicidad, se rompe el permiso. Donaciones/grants parecen seguros, pero hay que leerlo con el modelo decidido (§7).
- **Riesgo de difamación práctica**: usuarios van a señalar buques concretos como "ilegales" basándose en el mapa. El mapa muestra *actividad aparente*, no delitos. Hace falta disclaimer prominente y cuidado editorial en los nombres de las capas ("detección no correlacionada con AIS", no "barco pirata").
- **Sensibilidad geopolítica**: milla 201, flota mayormente china, Malvinas dentro de la ZEE en disputa. Decisiones cartográficas (qué límites se dibujan y cómo se rotulan) tienen carga política — usar cartografía oficial del IGN ayuda a ampararse en la posición oficial argentina.
- **Datos de aeronaves**: mostrar vuelos estatales/militares que la comunidad ADS-B capta es legal pero puede generar fricción. Definir política antes de la fase 4.

### De sostenibilidad
- El riesgo real número uno: **proyecto de una persona que se aburre o se queda sin tiempo**. Mitigación honesta: stack mínimo (ya está), código abierto desde el día 1, documentación de operación, y buscar un socio institucional (universidad, ONG ambiental, medio de periodismo de datos) antes de la fase 3.

---

## 6. Roadmap de implementación

Fases con criterios de completitud verificables, sin fechas.

**Fase 0 — Fundaciones y permisos.**
Completa cuando: tokens de GFW, EOG (VIIRS) y aisstream.io obtenidos y probados con requests reales sobre la ZEE; ToS de GFW y OpenSky leídos contra el modelo de financiamiento elegido; repo público con licencia; decisión documentada de las preguntas del §7 que bloquean (modelo de financiamiento y política editorial).

**Fase 1 — Mapa base con contexto.**
Completa cuando: sitio público desplegado con basemap, polígono de ZEE, milla 200, traza de Hidrovía y puertos como PMTiles servidos por CDN; carga en <3 s en una conexión móvil mediocre; página de metodología publicada aunque esté corta.

**Fase 2 — Capas satelitales (el diferencial).**
Completa cuando: jobs de GFW (heatmap, SAR detections, eventos) y VIIRS corren solos hace 2 semanas sin intervención manual; las capas se ven en el mapa con su timestamp; un click en una detección SAR muestra si matchea con un buque AIS o es *dark*; atribuciones correctas visibles.

**Fase 3 — AIS en vivo + memoria.**
Completa cuando: posiciones de aisstream.io aparecen en el mapa con <2 min de latencia y se archivan en PostGIS hace 2 semanas sin pérdida; ficha de buque con identidad cruzada GFW; el sistema sobrevivió una caída del websocket reconectando solo.

**Fase 4 — Capa aérea + profundidad temporal.**
Completa cuando: tráfico ADS-B (adsb.lol primario, OpenSky fallback) visible como capa opcional con su disclaimer de cobertura; selector temporal permite ver cualquier día del histórico acumulado para SAR/VIIRS/heatmap; quicklinks a imágenes Copernicus recientes por zona.

**Fase 5 — Independencia y comunidad.**
Completa cuando: al menos 2 receptores AIS propios alimentando el sistema (y AISHub desbloqueado como bonus); guía publicada para que terceros monten receptores; conversación formal iniciada con CONAE (SAOCOM) y/o GFW (partnership). Esta fase es opcional y depende de tracción real — si nadie usa el mapa, no tiene sentido comprar antenas.

---

## 7. Preguntas abiertas — necesito que definas esto

Las dos primeras bloquean la Fase 0; el resto puede esperar a su fase.

1. **Modelo de financiamiento.** ¿Hobby de bolsillo propio (~USD 25/mes), donaciones, grant de alguna fundación, o hay intención comercial futura? Esto determina qué licencias de datos podemos aceptar (GFW/OpenSky no-comercial) y la licencia del propio código.
2. **Política editorial sobre buques individuales.** ¿El mapa muestra nombres/MMSI de buques concretos con su historial, o solo agregados y detecciones anónimas? La primera opción es más potente para transparencia y más riesgosa legalmente. Mi recomendación: mostrar identidad (es información pública por diseño del AIS) con disclaimers fuertes, pero es una decisión tuya, no mía.
3. **Audiencia primaria.** ¿Ciudadano general, periodistas de datos, ONGs ambientales? Cambia el lenguaje de la UI, si hace falta export de datos (GeoJSON/CSV) y si el inglés es necesario además del castellano.
4. **Profundidad de histórico comprometida públicamente.** Guardar todo es barato al principio; *prometer* acceso público a todo el histórico es un compromiso de infraestructura. ¿Prometemos histórico navegable o lo tratamos como archivo interno hasta ver costos?
5. **Capa aérea: ¿qué mostramos?** ¿Todo lo que capta la comunidad incluyendo vuelos estatales/militares, o filtramos algo? (Mi posición: si es transparencia, es transparencia — pero el costo de fricción lo pagás vos.)
6. **Nombre, dominio y marca.** "Soberana" es el repo — ¿es el nombre del producto? Define dominio, atribuciones y cómo se presenta el proyecto ante GFW/CONAE.
7. **¿Hay apetito institucional?** ¿Tenés llegada a alguna universidad, ONG o medio que pueda co-firmar el proyecto? Cambia el plan de la Fase 5 y la conversación con CONAE de "imposible" a "posible".

---

## Apéndice — Referencias verificadas (junio 2026)

- GFW API: docs en globalfishingwatch.org/our-apis — 50 K req/día, delay 72 hs, atribución obligatoria.
- GFW SAR detections: dataset Sentinel-1 2017→presente (~5 días de lag), vía 4Wings API.
- aisstream.io: websocket gratuito, cobertura ~200 km costa, ~300 msg/s si suscribís el mundo entero (filtrar por bbox).
- ADS-B Exchange: API solo paga vía RapidAPI desde 2023/2025; adsb.lol expone API gratuita compatible.
- OpenSky: 400/4.000/8.000 créditos/día (anónimo/registrado/feeder); cobertura sudamericana con huecos grandes.
- SAOCOM: catálogo navegable sin registro; descarga requiere registro + licencia CONAE; nuevas adquisiciones requieren convenio.
- VIIRS Boat Detection: producto diario de EOG (Colorado School of Mines), registro gratuito.
