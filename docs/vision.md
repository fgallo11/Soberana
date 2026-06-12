# Visión — Soberana

> Este documento amplía el marco del proyecto más allá de lo que describe
> [PLAN.md](../PLAN.md) (que sigue siendo el plan operativo del dominio
> marítimo/fluvial). Acá está el *para qué* completo.

## La idea

La inspiración es "World View" de Bilawal Sidhu (spatialintelligence.ai): un
mapa que combina múltiples fuentes de datos públicas —vuelos, órbitas, AIS,
cámaras— sobre un mismo globo, bajo una premisa que hacemos propia:

**Cada fuente aislada dice poco. Combinadas, revelan patrones — incluyendo
lo que NO aparece.**

Un buque sin señal AIS no es un dato; un casco detectado por radar satelital
exactamente donde nadie declara estar, sí. Esa lógica del *cruce* y de la
*ausencia* es el método de todo el proyecto (hoy: capa SAR dark + alarmas de
apagado de AIS).

## El objetivo

Soberana no es solo monitoreo marítimo ni pesca ilegal. El objetivo es dar
visibilidad a **todo lo que ayude a entender la situación de soberanía del
país**, en capas sobre un mismo mapa, para que cualquier persona pueda ver
más claro **dónde nos invaden, dónde nos sacan, cuándo y cómo** — y que esa
mirada no dependa de nadie más que de nosotros: una herramienta soberana y
nuestra, gratuita a perpetuidad, sin publicidad, de código abierto.

## Los dominios

| Dominio | Qué muestra | Estado | Fuentes candidatas |
|---|---|---|---|
| **Marítimo** (Atlántico Sur, ZEE, milla 201, Malvinas) | flota extranjera, buques dark, apagones de AIS, zonas de ocupación | ✅ implementado | aisstream, GFW (AIS+SAR), VIIRS/EOG (credencial en trámite) |
| **Hidrovía Paraná-Paraguay** | buques extranjeros operando dentro del país: rutas, movimientos, escalas en puerto | 🔨 **prioridad actual** | aisstream + traza OSM/IGN + puertos (Dir. Nac. de Puertos) + alturas (Prefectura) |
| **Territorial / fronteras** | disputas, presencia militar extranjera, bases | ◐ parcial (bases, sector antártico, FICZ/FOCZ) | fuentes públicas, OSM, cartografía IGN |
| **Energético** | litio (NOA), hidrocarburos, prospección sísmica offshore, control de infraestructura | ⏳ futuro | Secretaría de Energía (áreas concesionadas), datos.gob.ar, AIS de buques sísmicos |
| **Datos / digital** | cables submarinos, datacenters, dependencia de infraestructura | ⏳ futuro | TeleGeography/submarinecablemap (verificar licencia), OSM, puntos de amarre públicos |
| **Aéreo** | vuelos, jets privados, aeronaves militares | ◐ capa básica en vivo (adsb.lol) | adsb.lol / airplanes.live / OpenSky — ampliable a dashboard propio |

## Criterio de prioridad

1. **Hidrovía** (ahora): es donde la extracción ocurre *adentro* del país y
   donde tenemos la mejor cobertura de datos en vivo (AIS terrestre).
2. **Aéreo** después: la capa ya existe; convertirla en dominio (pestaña,
   histórico, identificación fina) es el menor esfuerzo por dominio nuevo.
3. **Energético/digital**: capas mayormente estáticas (como las de
   soberanía) — alto valor narrativo, bajo costo técnico, sin tiempo real.
4. **Territorial**: el más sensible editorialmente; requiere las reglas de
   evidencia más estrictas antes de crecer.

## Arquitectura con esta visión

Las decisiones ya tomadas se sostienen y se explican mejor con este marco:

- **Registro de capas config-driven** (`layers.ts`): cada dominio nuevo es
  agregar entradas, no reescribir el mapa.
- **Pestañas/dashboards por tema**: la estructura actual (Mapa / Eventos /
  Metodología / Colaborá) admite vistas por dominio cuando un dominio junte
  suficientes capas (p. ej. pestaña "Hidrovía" con película + alturas +
  escalas + estadísticas).
- **Ingesta agnóstica de la fuente** + jobs en Actions: una fuente nueva es
  un módulo en `server/soberana/ingest/` que escribe un archivo a
  `frontend/public/data/` — el patrón ya está establecido y documentado.
- **El log de eventos como memoria transversal**: cualquier dominio puede
  emitir eventos (un apagón de AIS hoy; mañana, un buque sísmico entrando a
  un área protegida).

## Las reglas (no cambian con la escala)

1. Gratuito para siempre, sin publicidad, costo de infraestructura $0.
2. Evidencia, no condena: actividad *aparente*, confianza declarada,
   retraso declarado. La credibilidad es el único capital.
3. Honestidad sobre los límites de cada sensor y cada fuente.
4. Todo abierto: código MIT, pipelines corriendo en público, fuentes
   atribuidas con sus licencias.
