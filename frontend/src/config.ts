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

/** Basemap: OpenFreeMap — vector tiles libres, sin API key, uso en producción permitido. */
export const ESTILO_BASE = "https://tiles.openfreemap.org/styles/liberty";

/** Centro inicial: el Mar Argentino completo, con la milla 201 a la vista. */
export const VISTA_INICIAL = { center: [-58.5, -44.0] as [number, number], zoom: 3.6 };

/** Latencia declarada por capa: el usuario SIEMPRE sabe qué tan viejo es el dato. */
export type Badge = "en vivo" | "~24 h" | "72 h" | "~5 días" | "estático" | "horas";
