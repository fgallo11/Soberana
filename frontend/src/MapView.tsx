import maplibregl, { GeoJSONSource, Map as MLMap, Popup } from "maplibre-gl";
import { useEffect, useRef } from "react";
import { API_URL, HAY_BACKEND, LIMITES, VISTA_INICIAL_BOUNDS, ZOOM_MAX, ZOOM_MIN } from "./config";
import { CAPAS } from "./layers";
import { ESTILO_ESPIA } from "./map_style";

const FUENTE_TEXTO = ["Noto Sans Regular"];

import type { Tiempo } from "./TimeBar";

interface Props {
  visibles: Record<string, boolean>;
  /** null = en vivo; {fecha, minuto} = modo archivo (barra de tiempo) */
  tiempo: Tiempo | null;
  onDemo: () => void;
}

/** Recorridos de un día: mmsi -> {name, flag, pts: [[minuto, lon, lat], ...]} */
type ReplayDia = Record<string, { name?: string; flag?: string; pts: [number, number, number][] }>;

/** Posiciones interpoladas al minuto pedido → la "película" fluida.
 * Entre muestras (cada ~10 min) se interpola linealmente; si el hueco
 * supera 45 min (sombra de cobertura) el buque se oculta hasta reaparecer. */
function fotograma(buques: ReplayDia, fecha: string, minuto: number) {
  const features: any[] = [];
  for (const [mmsi, b] of Object.entries(buques)) {
    const pts = b.pts;
    if (!pts.length || minuto < pts[0][0] - 30 || minuto > pts[pts.length - 1][0] + 30) continue;
    let lon: number, lat: number;
    let i = pts.findIndex((p) => p[0] > minuto);
    if (i === -1) { [, lon, lat] = pts[pts.length - 1]; }
    else if (i === 0) { [, lon, lat] = pts[0]; }
    else {
      const [m0, lo0, la0] = pts[i - 1];
      const [m1, lo1, la1] = pts[i];
      if (m1 - m0 > 45) continue; // hueco grande: no inventar trayectoria
      const f = (minuto - m0) / (m1 - m0 || 1e-9);
      lon = lo0 + (lo1 - lo0) * f;
      lat = la0 + (la1 - la0) * f;
    }
    features.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: [lon, lat] },
      properties: {
        mmsi, name: b.name, flag: b.flag,
        ts: `${fecha} ${String(Math.floor(minuto / 60)).padStart(2, "0")}:${String(Math.floor(minuto % 60)).padStart(2, "0")} UTC (reconstruido)`,
      },
    });
  }
  return { type: "FeatureCollection" as const, features };
}

function restarDias(iso: string, n: number): string {
  const d = new Date(`${iso}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() - n);
  return d.toISOString().slice(0, 10);
}

function hoyISO(): string {
  return new Date().toISOString().slice(0, 10);
}

/** bbox aéreo (debe coincidir con el backend): continente + Malvinas + corredor
 * Atlántico Sur hasta Georgias/Sandwich */
const BBOX_AEREO = { lonMin: -76, latMin: -58, lonMax: -25, latMax: -21 };

function acAFeature(ac: any, mil: boolean) {
  return {
    type: "Feature" as const,
    geometry: { type: "Point" as const, coordinates: [ac.lon, ac.lat] },
    properties: {
      hex: ac.hex,
      callsign: (ac.flight ?? "").trim(),
      reg: ac.r ?? "",
      type: ac.t ?? "",
      alt_ft: ac.alt_baro ?? null,
      gs_kt: ac.gs ?? null,
      mil,
    },
  };
}

async function fetchAeronaves(): Promise<any> {
  if (HAY_BACKEND) {
    const r = await fetch(`${API_URL}/api/aircraft`);
    if (!r.ok) throw new Error(`API ${r.status}`);
    return r.json();
  }
  // modo estático: directo contra adsb.lol (comunitario, sin token)
  const [punto, mil] = await Promise.all([
    fetch("https://api.adsb.lol/v2/point/-40/-62/250").then((r) => r.json()),
    fetch("https://api.adsb.lol/v2/mil").then((r) => r.json()),
  ]);
  const features = new Map<string, any>();
  for (const ac of punto.ac ?? []) {
    if (ac.lat == null || ac.lon == null) continue;
    features.set(ac.hex, acAFeature(ac, Boolean((ac.dbFlags ?? 0) & 1)));
  }
  for (const ac of mil.ac ?? []) {
    if (ac.lat == null || ac.lon == null) continue;
    const dentro =
      ac.lon >= BBOX_AEREO.lonMin && ac.lon <= BBOX_AEREO.lonMax &&
      ac.lat >= BBOX_AEREO.latMin && ac.lat <= BBOX_AEREO.latMax;
    if (dentro) features.set(ac.hex, acAFeature(ac, true));
  }
  return { type: "FeatureCollection", features: [...features.values()] };
}

function fechaLocal(iso?: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("es-AR", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

function fmtCoord(lng: number, lat: number): string {
  const ns = lat < 0 ? "S" : "N";
  const ew = lng < 0 ? "O" : "E";
  return `${Math.abs(lat).toFixed(4)}°${ns}, ${Math.abs(lng).toFixed(4)}°${ew}`;
}

interface PopupOpts {
  descripcion?: string;
  nota?: string;
  fuente?: string;
  coord?: [number, number]; // [lng, lat]
}

/** Renderizador único de info: título + datos + descripción + nota + fuente + coordenadas. */
function infoHTML(titulo: string, filas: Array<[string, unknown]>, opts: PopupOpts = {}): string {
  const cuerpo = filas
    .filter(([, v]) => v !== null && v !== undefined && v !== "")
    .map(([k, v]) => `<div class="pp-row"><span>${k}</span><b>${v}</b></div>`)
    .join("");
  const desc = opts.descripcion ? `<p class="pp-desc">${opts.descripcion}</p>` : "";
  const nota = opts.nota ? `<p class="pp-nota">${opts.nota}</p>` : "";
  const coord = opts.coord ? `<div class="pp-coord">📍 ${fmtCoord(opts.coord[0], opts.coord[1])}</div>` : "";
  const fuente = opts.fuente ? `<div class="pp-fuente">fuente: ${opts.fuente}</div>` : "";
  return `<div class="pp"><h4>${titulo}</h4>${cuerpo}${desc}${nota}${coord}${fuente}</div>`;
}

/** Popup genérico para features estáticas (zonas, puntos de contexto): toma los
 * campos conocidos que existan en las properties. */
function infoGenerico(p: any, coord: [number, number]): string {
  const filas: Array<[string, unknown]> = [
    ["País", p.pais],
    ["Fuerza", p.fuerza],
    ["Tipo", p.tipo && !["isla", "base", "sector", "curso", "troncal", "milla_200"].includes(p.tipo) ? p.tipo : null],
    ["Río", p.rio],
  ];
  const titulo = p.extranjera || (p.pais && p.pais !== "Argentina") ? `🔴 ${p.nombre}` : p.nombre;
  return infoHTML(titulo, filas, {
    descripcion: p.descripcion,
    nota: p.detalle && p.detalle !== p.descripcion ? p.detalle : undefined,
    fuente: p.fuente,
    coord,
  });
}

export default function MapView({ visibles, tiempo, onDemo }: Props) {
  const contRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const visRef = useRef(visibles);
  visRef.current = visibles;
  const tiempoRef = useRef(tiempo);
  tiempoRef.current = tiempo;
  const cargarAISRef = useRef<() => void>(() => {});
  // película del día cargada: { fecha, buques }
  const replayRef = useRef<{ fecha: string; buques: ReplayDia } | null>(null);
  const replayDemoRef = useRef<Record<string, ReplayDia> | null>(null);
  // true cuando el handler de 'load' terminó de armar fuentes y capas.
  // (no usar map.isStyleLoaded(): con un tile server caído puede dar false
  // en cualquier momento y los efectos se perderían sin reintento)
  const listoRef = useRef(false);

  useEffect(() => {
    if (!contRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: contRef.current,
      style: ESTILO_ESPIA,
      bounds: VISTA_INICIAL_BOUNDS,
      fitBoundsOptions: { padding: 24 },
      maxBounds: LIMITES,   // navegación limitada: Argentina (con Antártida e islas) y una porción más
      minZoom: ZOOM_MIN,
      maxZoom: ZOOM_MAX,
      attributionControl: { compact: true },
    });
    mapRef.current = map;
    (window as unknown as { __soberanaMap?: MLMap }).__soberanaMap = map; // handle para tests/debug
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }));

    const timers: number[] = [];

    map.on("load", async () => {
      // ---------- capas estáticas (archivos en /data, regenerados por Actions) ----------
      map.addSource("zee", { type: "geojson", data: "/data/zee.geojson" });
      map.addLayer({
        id: "zee-fill", type: "fill", source: "zee",
        filter: ["!=", ["get", "tipo"], "milla_200"],
        paint: { "fill-color": "#2e86de", "fill-opacity": 0.05 },
      });
      map.addLayer({
        id: "zee-line", type: "line", source: "zee",
        filter: ["==", ["get", "tipo"], "milla_200"],
        paint: { "line-color": "#4aa3ff", "line-width": 1.6, "line-dasharray": [4, 2] },
      });

      map.addSource("antartida", { type: "geojson", data: "/data/antartida.geojson" });
      map.addLayer({
        id: "antartida-fill", type: "fill", source: "antartida",
        filter: ["==", ["get", "tipo"], "sector"],
        paint: { "fill-color": "#75aadb", "fill-opacity": 0.06 },
      });
      map.addLayer({
        id: "antartida-line", type: "line", source: "antartida",
        filter: ["==", ["get", "tipo"], "sector"],
        paint: { "line-color": "#75aadb", "line-width": 1.2, "line-dasharray": [5, 3], "line-opacity": 0.7 },
      });
      map.addLayer({
        id: "antartida-label", type: "symbol", source: "antartida",
        filter: ["in", ["get", "tipo"], ["literal", ["isla", "etiqueta"]]],
        layout: {
          "text-field": ["get", "nombre"], "text-font": FUENTE_TEXTO,
          "text-size": ["case", ["==", ["get", "tipo"], "etiqueta"], 13, 10],
          "text-transform": "uppercase", "text-letter-spacing": 0.15,
        },
        paint: { "text-color": "#75aadb", "text-halo-color": "#04131c", "text-halo-width": 1.2 },
      });
      map.addLayer({
        id: "antartida-bases", type: "circle", source: "antartida",
        filter: ["==", ["get", "tipo"], "base"],
        paint: {
          "circle-radius": 5,
          "circle-color": ["case", ["get", "argentina"], "#2ecc71", "#ff5e57"],
          "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.2,
        },
      });
      map.addLayer({
        id: "antartida-bases-label", type: "symbol", source: "antartida", minzoom: 3.4,
        filter: ["==", ["get", "tipo"], "base"],
        layout: {
          "text-field": ["get", "nombre"], "text-font": FUENTE_TEXTO,
          "text-size": 9.5, "text-offset": [0, 1], "text-anchor": "top",
        },
        paint: { "text-color": "#dfe6e9", "text-halo-color": "#000", "text-halo-width": 1 },
      });

      map.addSource("ficz", { type: "geojson", data: "/data/ficz_focz.geojson" });
      map.addLayer({
        id: "ficz-fill", type: "fill", source: "ficz",
        paint: { "fill-color": "#e74c3c", "fill-opacity": 0.07 },
      });
      map.addLayer({
        id: "ficz-line", type: "line", source: "ficz",
        paint: { "line-color": "#e74c3c", "line-width": 1.2, "line-dasharray": [2, 2] },
      });

      map.addSource("amps", { type: "geojson", data: "/data/amps.geojson" });
      map.addLayer({
        id: "amps-fill", type: "fill", source: "amps",
        paint: { "fill-color": "#2ecc71", "fill-opacity": 0.08 },
      });
      map.addLayer({
        id: "amps-line", type: "line", source: "amps",
        paint: { "line-color": "#2ecc71", "line-width": 1, "line-dasharray": [3, 2] },
      });

      map.addSource("bases", { type: "geojson", data: "/data/bases_militares.geojson" });
      map.addLayer({
        id: "bases-circle", type: "circle", source: "bases",
        paint: {
          "circle-radius": 6,
          "circle-color": ["case", ["get", "extranjera"], "#ff5e57", "#2ecc71"],
          "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.5,
        },
      });
      map.addLayer({
        id: "bases-label", type: "symbol", source: "bases", minzoom: 5,
        layout: {
          "text-field": ["get", "nombre"], "text-font": FUENTE_TEXTO,
          "text-size": 10, "text-offset": [0, 1.1], "text-anchor": "top",
        },
        paint: { "text-color": "#dfe6e9", "text-halo-color": "#000000", "text-halo-width": 1 },
      });

      map.addSource("hidrovia", { type: "geojson", data: "/data/hidrovia.geojson" });
      map.addLayer({
        id: "hidrovia-curso", type: "line", source: "hidrovia",
        filter: ["==", ["get", "tipo"], "curso"],
        paint: { "line-color": "#0d5c4d", "line-width": 1.2, "line-opacity": 0.8 },
      });
      map.addLayer({
        id: "hidrovia-troncal", type: "line", source: "hidrovia",
        filter: ["==", ["get", "tipo"], "troncal"],
        paint: { "line-color": "#00b894", "line-width": 2.2 },
      });

      map.addSource("puertos", { type: "geojson", data: "/data/puertos.geojson" });
      map.addLayer({
        id: "puertos-circle", type: "circle", source: "puertos",
        paint: { "circle-radius": 3, "circle-color": "#74b9ff", "circle-stroke-color": "#fff", "circle-stroke-width": 0.8 },
      });
      map.addLayer({
        id: "puertos-label", type: "symbol", source: "puertos", minzoom: 6,
        layout: {
          "text-field": ["get", "nombre"], "text-font": FUENTE_TEXTO,
          "text-size": 10, "text-offset": [0, 0.9], "text-anchor": "top",
        },
        paint: { "text-color": "#74b9ff", "text-halo-color": "#000", "text-halo-width": 1 },
      });

      // ---------- capas satelitales (archivos regenerados por jobs) ----------
      const sar: any = await fetch("/data/sar_detections.geojson").then((r) => r.json()).catch(() => null);
      if (sar) {
        if (sar.metadata?.demo) onDemo();
        map.addSource("sar", { type: "geojson", data: sar });
        map.addLayer({
          id: "sar-circle", type: "circle", source: "sar",
          paint: {
            "circle-radius": 4,
            "circle-color": ["case", ["coalesce", ["get", "matched"], false], "#9aa7b3", "#ff3b30"],
            "circle-opacity": 0.85,
          },
        });
      }

      const viirs: any = await fetch("/data/viirs_boats.geojson").then((r) => r.json()).catch(() => null);
      if (viirs) {
        if (viirs.metadata?.demo) onDemo();
        map.addSource("viirs", { type: "geojson", data: viirs });
        map.addLayer({
          id: "viirs-circle", type: "circle", source: "viirs",
          paint: { "circle-radius": 2.5, "circle-color": "#ffd166", "circle-blur": 0.6, "circle-opacity": 0.9 },
        });
      }

      const alturas: any = await fetch("/data/alturas.json").then((r) => r.json()).catch(() => null);
      if (alturas?.alturas?.length) {
        map.addSource("alturas", {
          type: "geojson",
          data: {
            type: "FeatureCollection",
            features: alturas.alturas.map((a: any) => ({
              type: "Feature",
              geometry: { type: "Point", coordinates: [a.lon, a.lat] },
              properties: { texto: `${a.puerto}: ${a.altura_m} m` },
            })),
          },
        });
        map.addLayer({
          id: "alturas-label", type: "symbol", source: "alturas", minzoom: 5,
          layout: {
            "text-field": ["get", "texto"], "text-font": FUENTE_TEXTO,
            "text-size": 11, "text-offset": [0, -1.2],
          },
          paint: { "text-color": "#81ecec", "text-halo-color": "#000", "text-halo-width": 1.2 },
        });
      }

      // ---------- heatmap de pesca GFW (raster proxiado por el backend) ----------
      if (HAY_BACKEND) {
        map.addSource("gfw-pesca", {
          type: "raster",
          tiles: [`${API_URL}/api/tiles/gfw/pesca/{z}/{x}/{y}.png`],
          tileSize: 256,
          attribution: "Actividad pesquera: Global Fishing Watch",
        });
        map.addLayer({ id: "gfw-pesca", type: "raster", source: "gfw-pesca", paint: { "raster-opacity": 0.7 } });
      }

      // ---------- alarmas: apagones de AIS sobre el mapa ----------
      try {
        const ev = await fetch(HAY_BACKEND ? `${API_URL}/api/events?limit=500` : "/data/events.json")
          .then((r) => r.json());
        if (ev.demo || (ev.events ?? []).some((e: any) => e.demo)) onDemo();
        map.addSource("alarmas", {
          type: "geojson",
          data: {
            type: "FeatureCollection",
            features: (ev.events ?? [])
              .filter((e: any) => e.lat != null && e.lon != null && e.type.startsWith("ais_gap"))
              .map((e: any) => ({
                type: "Feature",
                geometry: { type: "Point", coordinates: [e.lon, e.lat] },
                properties: {
                  id: e.id,
                  vessel: e.vessel_name || (e.mmsi ? `MMSI ${e.mmsi}` : "no identificado"),
                  flag: e.flag,
                  confianza: e.confidence,
                  inicio: e.started_at,
                  fin: e.ended_at,
                  dia: (e.started_at ?? "").slice(0, 10),
                  demo: Boolean(e.demo),
                },
              })),
          },
        });
        map.addLayer({
          id: "alarmas-halo", type: "circle", source: "alarmas",
          paint: {
            "circle-radius": 11,
            "circle-color": "transparent",
            "circle-stroke-width": 1.5,
            "circle-stroke-color": ["case", ["==", ["get", "confianza"], "alta"], "#ff9f1a", "#9aa7b3"],
            "circle-stroke-opacity": 0.55,
          },
        });
        map.addLayer({
          id: "alarmas-circle", type: "circle", source: "alarmas",
          paint: {
            "circle-radius": 4.5,
            "circle-color": ["case", ["==", ["get", "confianza"], "alta"], "#ff9f1a", "#9aa7b3"],
            "circle-stroke-color": "#000",
            "circle-stroke-width": 1,
          },
        });
        // latido de radar: el halo pulsa para llamar la atención sin sonido
        let creciendo = true;
        timers.push(window.setInterval(() => {
          if (!map.getLayer("alarmas-halo")) return;
          creciendo = !creciendo;
          map.setPaintProperty("alarmas-halo", "circle-radius", creciendo ? 14 : 9);
        }, 700));
      } catch { /* sin eventos disponibles: capa ausente */ }

      // ---------- AIS en vivo (requiere backend) ----------
      map.addSource("ais", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "ais-circle", type: "circle", source: "ais",
        paint: { "circle-radius": 4, "circle-color": "#55efc4", "circle-stroke-color": "#0a3d2e", "circle-stroke-width": 1 },
      });
      map.addLayer({
        id: "ais-label", type: "symbol", source: "ais", minzoom: 8,
        layout: {
          "text-field": ["coalesce", ["get", "name"], ["get", "mmsi"]],
          "text-font": FUENTE_TEXTO, "text-size": 10, "text-offset": [0, 1], "text-anchor": "top",
        },
        paint: { "text-color": "#55efc4", "text-halo-color": "#000", "text-halo-width": 1 },
      });
      if (HAY_BACKEND) {
        const cargarAIS = async () => {
          if (tiempoRef.current) return; // en archivo manda la película, no el polling
          try {
            const data = await fetch(`${API_URL}/api/vessels`).then((r) => r.json());
            (map.getSource("ais") as GeoJSONSource | undefined)?.setData(data);
          } catch { /* backend caído: la capa queda vacía, sin romper el mapa */ }
        };
        cargarAISRef.current = cargarAIS;
        cargarAIS();
        timers.push(window.setInterval(cargarAIS, 60_000));
      }

      // ---------- tráfico aéreo (con o sin backend) ----------
      map.addSource("adsb", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "adsb-circle", type: "circle", source: "adsb",
        paint: {
          "circle-radius": ["case", ["get", "mil"], 6, 3.5],
          "circle-color": ["case", ["get", "mil"], "#ff9f1a", "#a29bfe"],
          "circle-stroke-color": "#fff",
          "circle-stroke-width": ["case", ["get", "mil"], 1.5, 0.5],
        },
      });
      map.addLayer({
        id: "adsb-label", type: "symbol", source: "adsb", minzoom: 5,
        filter: ["==", ["get", "mil"], true],
        layout: {
          "text-field": ["coalesce", ["get", "callsign"], ["get", "hex"]],
          "text-font": FUENTE_TEXTO, "text-size": 10, "text-offset": [0, 1], "text-anchor": "top",
        },
        paint: { "text-color": "#ff9f1a", "text-halo-color": "#000", "text-halo-width": 1 },
      });
      const cargarAeronaves = async () => {
        try {
          const data = await fetchAeronaves();
          (map.getSource("adsb") as GeoJSONSource | undefined)?.setData(data);
        } catch { /* fuente comunitaria caída: capa vacía */ }
      };
      cargarAeronaves();
      timers.push(window.setInterval(cargarAeronaves, 30_000));

      // ---------- popups ----------
      // c = [lng, lat] del punto a mostrar (geometría del feature si es Point, si no el click)
      // El ORDEN define prioridad: primero puntos (targets chicos), después
      // líneas, y al final los rellenos grandes (que si no taparían todo).
      const renderers: Array<[string, (p: any, c: [number, number]) => string]> = [
        // --- puntos dinámicos ---
        ["sar-circle", (p, c) =>
          infoHTML(
            p.matched ? "Detección SAR (correlacionada con AIS)" : "Detección SAR no correlacionada con AIS",
            [["Fecha", p.fecha], ["Fuente", p.fuente ?? "GFW / Sentinel-1"]],
            { coord: c, nota: p.matched ? undefined :
              "Un buque presente que no transmitía AIS. NO implica por sí solo actividad ilegal." })],
        ["viirs-circle", (p, c) => infoHTML("Luz de barco (VIIRS)", [["Fecha", p.fecha]],
          { coord: c, nota: "Detección nocturna por luz. Típicamente flota potera. No identifica al buque." })],
        ["ais-circle", (p, c) =>
          infoHTML(p.name || `MMSI ${p.mmsi}`, [
            ["MMSI", p.mmsi], ["Bandera", p.flag], ["Velocidad", p.sog != null ? `${p.sog} kn` : null],
            ["Último contacto", fechaLocal(p.ts)],
          ], { coord: c, nota: "Posición autoreportada por AIS: puede ser falseada." })],
        ["adsb-circle", (p, c) =>
          infoHTML((p.callsign || p.hex) + (p.mil ? " 🔶" : ""), [
            ["Matrícula", p.reg], ["Tipo", p.type],
            ["Altitud", p.alt_ft != null ? `${p.alt_ft} ft` : null],
            ["Militar", p.mil ? "sí" : "no"],
          ], { coord: c, nota: p.mil ? "Aeronave militar captada por la red comunitaria ADS-B." : undefined })],
        ["alarmas-circle", (p, c) =>
          infoHTML(`🚨 Apagón de AIS — ${p.vessel}`, [
            ["Bandera", p.flag],
            ["Confianza", p.confianza],
            ["Inicio", fechaLocal(p.inicio)],
            ["Reaparición", p.fin ? fechaLocal(p.fin) : "sin registrar"],
          ], { coord: c, nota: (p.demo ? "DATO DE DEMOSTRACIÓN. " : "") +
             "Última posición antes de dejar de transmitir. No implica por sí solo actividad ilegal. Detalle en la pestaña Registro de eventos." })],
        // --- puntos estáticos ---
        ["bases-circle", infoGenerico],
        ["antartida-bases", infoGenerico],
        ["antartida-label", infoGenerico],   // islas
        ["puertos-circle", (p, c) => infoGenerico({ ...p, nombre: `Puerto ${p.nombre}` }, c)],
        // --- líneas ---
        ["hidrovia-troncal", infoGenerico],
        ["hidrovia-curso", infoGenerico],
        ["zee-line", infoGenerico],
        // --- rellenos (al final: no deben tapar lo de arriba) ---
        ["ocupados-fill", (p, c) =>
          infoHTML(`🔴 ${p.nombre}`, [["Estado", p.estado]],
            { coord: c, descripcion: "Territorio argentino bajo ocupación británica.",
              nota: p.marco_onu || "Argentina reclama la soberanía; la ONU reconoce la disputa pendiente.",
              fuente: "Marco ONU según fuentes oficiales argentinas (Cancillería)" })],
        ["ficz-fill", infoGenerico],
        ["amps-fill", infoGenerico],
        ["zee-fill", infoGenerico],
        ["antartida-fill", infoGenerico],    // sector antártico
      ];
      // Prioridad: puntos dinámicos → puntos estáticos → líneas → rellenos.
      // Un solo handler global elige el feature más específico bajo el click,
      // así un relleno (ZEE) no tapa un punto chico (una base) ni se abren
      // dos popups a la vez.
      const rendererMap = new Map(renderers);
      const ordenPrioridad = renderers.map(([id]) => id);
      // queryRenderedFeatures lanza si una capa no existe: filtramos a las presentes
      const capasPresentes = () => ordenPrioridad.filter((id) => map.getLayer(id));

      map.on("click", (e) => {
        const feats = map.queryRenderedFeatures(e.point, { layers: capasPresentes() });
        if (!feats.length) return;
        feats.sort((a, b) => ordenPrioridad.indexOf(a.layer.id) - ordenPrioridad.indexOf(b.layer.id));
        const f = feats[0];
        const c: [number, number] = f.geometry?.type === "Point"
          ? (f.geometry.coordinates as [number, number])
          : [e.lngLat.lng, e.lngLat.lat];
        new Popup({ closeButton: true, maxWidth: "340px" })
          .setLngLat(f.geometry?.type === "Point" ? c : e.lngLat)
          .setHTML(rendererMap.get(f.layer.id)!(f.properties, c))
          .addTo(map);
      });
      map.on("mousemove", (e) => {
        const hay = map.queryRenderedFeatures(e.point, { layers: capasPresentes() }).length > 0;
        map.getCanvas().style.cursor = hay ? "pointer" : "";
      });

      listoRef.current = true;
      aplicarVisibilidad(map, visRef.current, tiempoRef.current?.fecha ?? null);
      aplicarFecha(map, tiempoRef.current?.fecha ?? null);
    });

    return () => {
      timers.forEach(clearInterval);
      map.remove();
      mapRef.current = null;
    };
  }, []);

  const fecha = tiempo?.fecha ?? null;

  useEffect(() => {
    const map = mapRef.current;
    if (map && listoRef.current) aplicarVisibilidad(map, visibles, fecha);
  }, [visibles, fecha]);

  // cambio de día: filtros satelitales ("fotos") + carga de la película del día
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !listoRef.current) return;
    aplicarFecha(map, fecha);
    if (!fecha) {
      replayRef.current = null;
      cargarAISRef.current(); // volver a la señal en vivo
      return;
    }
    let cancelado = false;
    (async () => {
      let buques: ReplayDia = {};
      try {
        if (HAY_BACKEND) {
          const r = await fetch(`${API_URL}/api/replay?fecha=${fecha}`).then((x) => x.json());
          buques = r.buques ?? {};
        } else {
          if (!replayDemoRef.current) {
            const r = await fetch("/data/replay_demo.json").then((x) => x.json());
            replayDemoRef.current = r.dias ?? {};
            if (r.demo) onDemo();
          }
          buques = replayDemoRef.current?.[fecha] ?? {};
        }
      } catch { /* sin película para ese día: capa vacía */ }
      if (cancelado) return;
      replayRef.current = { fecha, buques };
      const t = tiempoRef.current;
      if (t?.fecha === fecha) {
        (map.getSource("ais") as GeoJSONSource | undefined)?.setData(fotograma(buques, fecha, t.minuto));
      }
    })();
    return () => { cancelado = true; };
  }, [fecha, onDemo]);

  // cambio de minuto: nuevo fotograma de la película (interpolación fluida)
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !listoRef.current || !tiempo) return;
    const replay = replayRef.current;
    if (!replay || replay.fecha !== tiempo.fecha) return;
    (map.getSource("ais") as GeoJSONSource | undefined)?.setData(
      fotograma(replay.buques, tiempo.fecha, tiempo.minuto),
    );
  }, [tiempo]);

  return (
    <div className="mapa-marco">
      <div ref={contRef} className="mapa" />
      <div className="crt-overlay" aria-hidden="true" />
    </div>
  );
}

function aplicarVisibilidad(map: MLMap, visibles: Record<string, boolean>, fecha: string | null) {
  for (const capa of CAPAS) {
    let activa = visibles[capa.id];
    // en modo archivo: aeronaves solo en vivo (no retenemos su histórico)
    if (fecha && capa.id === "aereo") activa = false;
    const v = activa ? "visible" : "none";
    for (const layerId of capa.mapLayers) {
      if (map.getLayer(layerId)) map.setLayoutProperty(layerId, "visibility", v);
    }
  }
}

/** Aplica la fecha seleccionada a las capas con dimensión temporal.
 * - SAR: ventana de 7 días que termina en la fecha (la revisita de
 *   Sentinel-1 deja días sin pasada; un solo día quedaría casi vacío).
 * - VIIRS: la noche seleccionada.
 * - Heatmap GFW: 30 días que terminan en la fecha (vía el proxy).
 * En vivo, las ventanas terminan hoy. */
function aplicarFecha(map: MLMap, fecha: string | null) {
  const hasta = fecha ?? hoyISO();
  const desdeSar = restarDias(hasta, 7);

  if (map.getLayer("sar-circle")) {
    map.setFilter("sar-circle", fecha
      ? ["all", ["has", "fecha"], ["<=", ["get", "fecha"], hasta], [">", ["get", "fecha"], desdeSar]]
      // en vivo somos tolerantes con features sin fecha (no las escondemos)
      : ["any", ["!", ["has", "fecha"]], [">", ["get", "fecha"], desdeSar]]);
  }
  if (map.getLayer("viirs-circle")) {
    map.setFilter("viirs-circle", fecha
      ? ["==", ["get", "fecha"], fecha]
      // en vivo: la noche más reciente disponible (≈ ayer)
      : ["any", ["!", ["has", "fecha"]], [">", ["get", "fecha"], restarDias(hasta, 2)]]);
  }
  if (map.getLayer("alarmas-circle")) {
    // archivo: solo apagones iniciados ese día; vivo: todos los recientes
    const f = fecha ? ["==", ["get", "dia"], fecha] : null;
    map.setFilter("alarmas-circle", f as any);
    map.setFilter("alarmas-halo", f as any);
  }
  if (HAY_BACKEND && map.getSource("gfw-pesca")) {
    const src = map.getSource("gfw-pesca") as maplibregl.RasterTileSource;
    const base = `${API_URL}/api/tiles/gfw/pesca/{z}/{x}/{y}.png`;
    const url = fecha ? `${base}?desde=${restarDias(fecha, 30)}&hasta=${fecha}` : base;
    if (typeof (src as unknown as { setTiles?: unknown }).setTiles === "function") {
      src.setTiles([url]);
    }
  }
}
