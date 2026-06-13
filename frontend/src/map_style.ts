import type { StyleSpecification } from "maplibre-gl";

/** Estilo propio del mapa: "sala de operaciones" — oscuro, fósforo verde y ámbar,
 * acorde a la estética de la página. Construido directo sobre los vector tiles
 * libres de OpenFreeMap (esquema OpenMapTiles), sin API key. Deliberadamente
 * minimalista: tierra, agua, límites y topónimos; el protagonismo es de las
 * capas de datos. */
export const ESTILO_ESPIA: StyleSpecification = {
  version: 8,
  name: "soberana-ops",
  glyphs: "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf",
  sources: {
    omt: {
      type: "vector",
      url: "https://tiles.openfreemap.org/planet",
      attribution: "© OpenStreetMap · tiles OpenFreeMap",
    },
    // tierra propia (Natural Earth, commiteada al repo): el territorio se ve
    // SIEMPRE, incluso si el servidor de tiles externo está caído
    tierra: { type: "geojson", data: "/data/tierra.geojson" },
    territorio: { type: "geojson", data: "/data/territorio_argentino.geojson" },
    // territorios argentinos bajo ocupación británica (Malvinas, Georgias y
    // Sandwich del Sur): se pintan en rojo para que quede claro
    ocupados: { type: "geojson", data: "/data/territorios_ocupados.geojson" },
  },
  layers: [
    // Modelo: el océano es el fondo. La tierra propia (Natural Earth) se
    // dibuja como RELLENO de respaldo, SIN su propia línea de costa: la costa
    // visible la define el agua de OpenFreeMap (alta resolución) dibujada
    // encima, que recorta el relleno grueso a la costa real. Así no hay dos
    // litorales superpuestos. Si OFM no carga, el relleno solo ya muestra la
    // tierra (modo degradado).
    { id: "fondo", type: "background", paint: { "background-color": "#04111a" } },
    {
      id: "tierra-fill",
      type: "fill",
      source: "tierra",
      paint: { "fill-color": "#15241a" },
    },
    {
      id: "territorio-arg",
      type: "fill",
      source: "territorio",
      paint: { "fill-color": "#245130", "fill-opacity": 0.45 },
    },
    // territorios ocupados: silueta ROJA (relleno; el agua de OFM la recorta
    // a la costa real de cada isla)
    {
      id: "ocupados-fill",
      type: "fill",
      source: "ocupados",
      paint: { "fill-color": "#c0392b", "fill-opacity": 0.8 },
    },
    {
      // agua de OpenFreeMap: define la costa de alta resolución y recorta los
      // rellenos de arriba. Mismo color que el fondo para que el recorte sea
      // invisible (no genera una segunda línea de costa).
      id: "agua",
      type: "fill",
      source: "omt",
      "source-layer": "water",
      paint: { "fill-color": "#04111a" },
    },
    {
      id: "rios",
      type: "line",
      source: "omt",
      "source-layer": "waterway",
      minzoom: 5,
      paint: { "line-color": "#0c2e3a", "line-width": 1 },
    },
    {
      id: "limites-pais",
      type: "line",
      source: "omt",
      "source-layer": "boundary",
      filter: ["all", ["==", ["get", "admin_level"], 2], ["!=", ["get", "maritime"], 1]],
      paint: {
        "line-color": "#2bd96a",
        "line-opacity": 0.45,
        "line-width": 1.1,
        "line-dasharray": [3, 2],
      },
    },
    {
      id: "limites-provincia",
      type: "line",
      source: "omt",
      "source-layer": "boundary",
      filter: ["all", ["==", ["get", "admin_level"], 4], ["!=", ["get", "maritime"], 1]],
      minzoom: 4,
      paint: { "line-color": "#1c4a2c", "line-opacity": 0.5, "line-width": 0.7 },
    },
    {
      id: "nombre-mar",
      type: "symbol",
      source: "omt",
      "source-layer": "water_name",
      layout: {
        "text-field": ["coalesce", ["get", "name:es"], ["get", "name"]],
        "text-font": ["Noto Sans Italic"],
        "text-size": 11,
        "text-transform": "uppercase",
        "text-letter-spacing": 0.2,
      },
      paint: { "text-color": "#16566b", "text-halo-color": "#04131c", "text-halo-width": 1 },
    },
    {
      id: "nombre-pais",
      type: "symbol",
      source: "omt",
      "source-layer": "place",
      filter: ["==", ["get", "class"], "country"],
      layout: {
        "text-field": ["coalesce", ["get", "name:es"], ["get", "name"]],
        "text-font": ["Noto Sans Bold"],
        "text-size": 12,
        "text-transform": "uppercase",
        "text-letter-spacing": 0.25,
      },
      paint: { "text-color": "#3f7a52", "text-halo-color": "#0a0f0b", "text-halo-width": 1.2 },
    },
    {
      id: "nombre-ciudad",
      type: "symbol",
      source: "omt",
      "source-layer": "place",
      filter: ["in", ["get", "class"], ["literal", ["city", "town"]]],
      minzoom: 4.5,
      layout: {
        "text-field": ["coalesce", ["get", "name:es"], ["get", "name"]],
        "text-font": ["Noto Sans Regular"],
        "text-size": 10,
        "text-transform": "uppercase",
        "text-letter-spacing": 0.1,
      },
      paint: { "text-color": "#56705d", "text-halo-color": "#0a0f0b", "text-halo-width": 1 },
    },
  ],
};
