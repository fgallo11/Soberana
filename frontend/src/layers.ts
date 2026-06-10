import type { Badge } from "./config";

export interface CapaDef {
  id: string;
  grupo: "Soberanía" | "Mar y milla 201" | "Hidrovía" | "Aéreo";
  titulo: string;
  descripcion: string;
  badge: Badge;
  /** ids de capas de estilo MapLibre que este toggle controla */
  mapLayers: string[];
  defaultOn: boolean;
  /** requiere backend desplegado (API_URL) */
  requiereBackend?: boolean;
}

export const CAPAS: CapaDef[] = [
  {
    id: "zee",
    grupo: "Soberanía",
    titulo: "ZEE y milla 200",
    descripcion: "Zona Económica Exclusiva argentina y su límite exterior (geometría aproximada).",
    badge: "estático",
    mapLayers: ["zee-fill", "zee-line"],
    defaultOn: true,
  },
  {
    id: "ficz",
    grupo: "Soberanía",
    titulo: "FICZ / FOCZ (Malvinas)",
    descripcion:
      "Zonas de pesca administradas por el gobierno británico de ocupación, dentro de la ZEE argentina.",
    badge: "estático",
    mapLayers: ["ficz-fill", "ficz-line"],
    defaultOn: true,
  },
  {
    id: "bases",
    grupo: "Soberanía",
    titulo: "Bases militares",
    descripcion: "Instalaciones militares propias y extranjeras de conocimiento público.",
    badge: "estático",
    mapLayers: ["bases-circle", "bases-label"],
    defaultOn: true,
  },
  {
    id: "amps",
    grupo: "Soberanía",
    titulo: "Áreas protegidas y Agujero Azul",
    descripcion: "AMP Namuncurá–Burdwood, Yaganes y el Agujero Azul (aproximadas).",
    badge: "estático",
    mapLayers: ["amps-fill", "amps-line"],
    defaultOn: false,
  },
  {
    id: "sar",
    grupo: "Mar y milla 201",
    titulo: "Detecciones por radar satelital (SAR)",
    descripcion:
      "Buques detectados por Sentinel-1, transmitan o no AIS. Rojo: detección no correlacionada con AIS (buque 'dark'). Fuente: Global Fishing Watch.",
    badge: "~5 días",
    mapLayers: ["sar-circle"],
    defaultOn: true,
  },
  {
    id: "viirs",
    grupo: "Mar y milla 201",
    titulo: "Luces nocturnas de barcos (VIIRS)",
    descripcion:
      "Luces de la flota pesquera detectadas de noche por satélite: la flota potera se ve aunque apague el AIS. Fuente: EOG/NOAA.",
    badge: "~24 h",
    mapLayers: ["viirs-circle"],
    defaultOn: true,
  },
  {
    id: "pesca",
    grupo: "Mar y milla 201",
    titulo: "Esfuerzo pesquero (heatmap GFW)",
    descripcion: "Actividad pesquera aparente de los últimos 30 días según AIS. Fuente: Global Fishing Watch.",
    badge: "72 h",
    mapLayers: ["gfw-pesca"],
    defaultOn: false,
    requiereBackend: true,
  },
  {
    id: "ais",
    grupo: "Hidrovía",
    titulo: "Buques en vivo (AIS costero)",
    descripcion:
      "Posiciones AIS en la Hidrovía y el litoral. El AIS terrestre NO llega a la milla 201: lo que pasa allá se ve en las capas satelitales.",
    badge: "en vivo",
    mapLayers: ["ais-circle", "ais-label"],
    defaultOn: true,
    requiereBackend: true,
  },
  {
    id: "hidrovia",
    grupo: "Hidrovía",
    titulo: "Vía Navegable Troncal y puertos",
    descripcion: "Traza aproximada de la Hidrovía Paraná–Paraguay y puertos principales.",
    badge: "estático",
    mapLayers: ["hidrovia-line", "puertos-circle", "puertos-label"],
    defaultOn: true,
  },
  {
    id: "alturas",
    grupo: "Hidrovía",
    titulo: "Alturas del río",
    descripcion: "Altura del Paraná en cada puerto. Fuente: Prefectura Naval Argentina.",
    badge: "horas",
    mapLayers: ["alturas-label"],
    defaultOn: false,
  },
  {
    id: "aereo",
    grupo: "Aéreo",
    titulo: "Aeronaves (incl. militares)",
    descripcion:
      "Tráfico captado por la red comunitaria ADS-B, sin filtrar. Naranja: aeronave militar (p. ej. el puente aéreo RAF a Mount Pleasant). Cobertura limitada: muchas aeronaves militares vuelan sin transponder.",
    badge: "en vivo",
    mapLayers: ["adsb-circle", "adsb-label"],
    defaultOn: true,
  },
];
