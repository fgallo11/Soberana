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
    id: "tierras",
    grupo: "Soberanía",
    titulo: "Extranjerización de tierras",
    descripcion:
      "Tierra rural en manos extranjeras (RNTR): ~13 M ha, ~5% del país; lidera EE.UU. (2,7 M ha), luego Italia y España. Provincias coloreadas por % y, en rojo, los departamentos que superan el ex tope del 15% (San Carlos y Molinos en Salta, General Lamadrid, Lácar, Campana). Ley 26.737 derogada en 2023. Capa opcional, apagada por defecto.",
    badge: "estático",
    mapLayers: ["tierras-fill", "tierras-line", "tierras-depto", "tierras-depto-label"],
    defaultOn: false,
  },
  {
    id: "infra",
    grupo: "Soberanía",
    titulo: "Infraestructura crítica (control extranjero)",
    descripcion:
      "Litio (amarillo), minería de oro/cobre (bronce), represas (celeste), cables submarinos (violeta) y terminales portuarias (naranja) cuyo control, operación o financiamiento es extranjero. Tocá cada punto para el detalle.",
    badge: "estático",
    mapLayers: ["infra-circle", "infra-label"],
    defaultOn: true,
  },
  {
    id: "antartida",
    grupo: "Soberanía",
    titulo: "Antártida Argentina e islas",
    descripcion:
      "Sector Antártico Argentino (25°O–74°O al sur del paralelo 60°S), islas del Atlántico Sur, bases antárticas (verde: argentinas; rojo: extranjeras dentro del sector) y asentamientos como Puerto Argentino y Grytviken.",
    badge: "estático",
    mapLayers: ["antartida-fill", "antartida-line", "antartida-label", "antartida-bases", "antartida-bases-label"],
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
    titulo: "📷 Radar satelital (SAR) — foto",
    descripcion:
      "FOTO por pasada del satélite, no película: buques detectados por Sentinel-1 transmitan o no AIS. Rojo: SIN correlación con AIS (buque 'dark'); gris: con AIS; azul: sin clasificar. Elegí el día en la barra de tiempo. Fuente: Global Fishing Watch.",
    badge: "~5 días",
    mapLayers: ["sar-circle"],
    defaultOn: true,
  },
  {
    id: "viirs",
    grupo: "Mar y milla 201",
    titulo: "📷 Luces nocturnas (VIIRS) — foto",
    descripcion:
      "UNA FOTO POR NOCHE, no película: las luces de la flota potera vistas por satélite, aunque apague el AIS. Elegí la noche en la barra de tiempo. Fuente: EOG/NOAA.",
    badge: "~24 h",
    mapLayers: ["viirs-circle"],
    defaultOn: true,
  },
  {
    id: "alarmas",
    grupo: "Mar y milla 201",
    titulo: "🚨 Apagones de AIS (alarmas)",
    descripcion:
      "Última posición conocida de buques que dejaron de transmitir. Naranja: alta confianza (GFW, apagado intencional, 72 hs de retraso). Gris: pérdida de señal costera (detector propio, causas posibles inocentes). Detalle completo en la pestaña Registro de eventos.",
    badge: "72 h",
    mapLayers: ["alarmas-halo", "alarmas-circle"],
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
    titulo: "🎬 Buques (AIS costero)",
    descripcion:
      "En vivo: posiciones AIS de la Hidrovía y el litoral (requiere backend). En archivo: película del día — recorridos reconstruidos e interpolados. El AIS terrestre NO llega a la milla 201: lo que pasa allá se ve en las fotos satelitales.",
    badge: "en vivo",
    mapLayers: ["ais-circle", "ais-label"],
    defaultOn: true,
  },
  {
    id: "hidrovia",
    grupo: "Hidrovía",
    titulo: "Vía Navegable Troncal y puertos",
    descripcion:
      "Curso real de la Hidrovía Paraná–Paraguay (OSM/Natural Earth) con la traza navegable Corrientes → Recalada resaltada, y puertos (Dirección Nacional de Puertos).",
    badge: "estático",
    mapLayers: ["hidrovia-curso", "hidrovia-troncal", "puertos-circle", "puertos-label"],
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
