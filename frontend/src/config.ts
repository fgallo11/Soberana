/** Configuración del frontend.
 *
 * VITE_API_URL: URL del backend (la VM). Si está vacía, el mapa corre en
 * "modo estático": solo capas servidas como archivos (los jobs de Actions
 * las regeneran) y tráfico aéreo directo contra adsb.lol. Las capas que
 * requieren backend (AIS vivo, tiles GFW) se muestran deshabilitadas con
 * su explicación, no desaparecen en silencio.
 */
export const API_URL: string = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export const HAY_BACKEND = API_URL !== "";

/** Vista inicial: todo el territorio a la vista — continente completo, Mar
 * Argentino, islas del Atlántico Sur y el norte del Sector Antártico —
 * ajustado al tamaño de pantalla (bounds, no centro/zoom fijos). */
export const VISTA_INICIAL_BOUNDS: [[number, number], [number, number]] = [
  [-77.0, -71.0],
  [-32.0, -22.0],
];

/** Límites de navegación: Argentina (con Antártida e islas) y una porción más.
 * El usuario puede hacer zoom y paneo libremente dentro de esta caja. */
export const LIMITES: [[number, number], [number, number]] = [
  [-95.0, -85.0], // suroeste (lat -85: límite práctico de la proyección web mercator)
  [-15.0, -10.0], // noreste
];
export const ZOOM_MIN = 2.4;
export const ZOOM_MAX = 14;

/** Latencia declarada por capa: el usuario SIEMPRE sabe qué tan viejo es el dato. */
export type Badge = "en vivo" | "~24 h" | "72 h" | "~5 días" | "estático" | "horas";
