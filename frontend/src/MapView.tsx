import maplibregl, { GeoJSONSource, Map as MLMap, Popup } from "maplibre-gl";
import { useEffect, useRef } from "react";
import { API_URL, HAY_BACKEND, LIMITES, VISTA_INICIAL_BOUNDS, ZOOM_MAX, ZOOM_MIN } from "./config";
import { CAPAS } from "./layers";
import { ESTILO_ESPIA } from "./map_style";

const FUENTE_TEXTO = ["Noto Sans Regular"];

interface Props {
  visibles: Record<string, boolean>;
  onDemo: () => void;
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

function popupHTML(titulo: string, filas: Array<[string, unknown]>, nota?: string): string {
  const cuerpo = filas
    .filter(([, v]) => v !== null && v !== undefined && v !== "")
    .map(([k, v]) => `<div class="pp-row"><span>${k}</span><b>${v}</b></div>`)
    .join("");
  return `<div class="pp"><h4>${titulo}</h4>${cuerpo}${nota ? `<p class="pp-nota">${nota}</p>` : ""}</div>`;
}

export default function MapView({ visibles, onDemo }: Props) {
  const contRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const visRef = useRef(visibles);
  visRef.current = visibles;

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
        id: "hidrovia-line", type: "line", source: "hidrovia",
        paint: { "line-color": "#00b894", "line-width": 2 },
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
          try {
            const data = await fetch(`${API_URL}/api/vessels`).then((r) => r.json());
            (map.getSource("ais") as GeoJSONSource | undefined)?.setData(data);
          } catch { /* backend caído: la capa queda vacía, sin romper el mapa */ }
        };
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
      const conPopup: Array<[string, (p: any) => string]> = [
        ["bases-circle", (p) => popupHTML(p.nombre, [["Fuerza", p.fuerza], ["País", p.pais]], p.nota)],
        ["puertos-circle", (p) => popupHTML(`Puerto ${p.nombre}`, [["Tipo", p.tipo]])],
        ["sar-circle", (p) =>
          popupHTML(
            p.matched ? "Detección SAR (correlacionada con AIS)" : "Detección SAR no correlacionada con AIS",
            [["Fecha", p.fecha], ["Fuente", p.fuente ?? "GFW / Sentinel-1"]],
            p.matched ? undefined :
              "Un buque presente que no transmitía AIS. NO implica por sí solo actividad ilegal.",
          )],
        ["viirs-circle", (p) => popupHTML("Luz de barco (VIIRS)", [["Fecha", p.fecha]],
          "Detección nocturna por luz. Típicamente flota potera. No identifica al buque.")],
        ["ais-circle", (p) =>
          popupHTML(p.name || `MMSI ${p.mmsi}`, [
            ["MMSI", p.mmsi], ["Bandera", p.flag], ["Velocidad", p.sog != null ? `${p.sog} kn` : null],
            ["Último contacto", fechaLocal(p.ts)],
          ], "Posición autoreportada por AIS: puede ser falseada.")],
        ["adsb-circle", (p) =>
          popupHTML(p.callsign || p.hex, [
            ["Matrícula", p.reg], ["Tipo", p.type],
            ["Altitud", p.alt_ft != null ? `${p.alt_ft} ft` : null],
            ["Militar", p.mil ? "sí" : "no"],
          ], p.mil ? "Aeronave militar captada por la red comunitaria ADS-B." : undefined)],
        ["ficz-fill", (p) => popupHTML(p.nombre, [], p.detalle)],
        ["amps-fill", (p) => popupHTML(p.nombre, [], p.detalle)],
      ];
      for (const [layerId, html] of conPopup) {
        map.on("click", layerId, (e) => {
          const f = e.features?.[0];
          if (!f) return;
          new Popup({ closeButton: true, maxWidth: "320px" })
            .setLngLat(e.lngLat)
            .setHTML(html(f.properties))
            .addTo(map);
        });
        map.on("mouseenter", layerId, () => { map.getCanvas().style.cursor = "pointer"; });
        map.on("mouseleave", layerId, () => { map.getCanvas().style.cursor = ""; });
      }

      aplicarVisibilidad(map, visRef.current);
    });

    return () => {
      timers.forEach(clearInterval);
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (map && map.isStyleLoaded()) aplicarVisibilidad(map, visibles);
  }, [visibles]);

  return (
    <div className="mapa-marco">
      <div ref={contRef} className="mapa" />
      <div className="crt-overlay" aria-hidden="true" />
    </div>
  );
}

function aplicarVisibilidad(map: MLMap, visibles: Record<string, boolean>) {
  for (const capa of CAPAS) {
    const v = visibles[capa.id] ? "visible" : "none";
    for (const layerId of capa.mapLayers) {
      if (map.getLayer(layerId)) map.setLayoutProperty(layerId, "visibility", v);
    }
  }
}
