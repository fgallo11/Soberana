import { useEffect, useState } from "react";
import { API_URL, HAY_BACKEND } from "./config";

interface Evento {
  id: string;
  type: string;
  src: string;
  confidence: string;
  mmsi?: string;
  vessel_name?: string;
  flag?: string;
  lat?: number;
  lon?: number;
  started_at?: string;
  ended_at?: string | null;
  zone?: string;
  demo?: boolean;
}

const TIPOS: Record<string, string> = {
  ais_gap_gfw: "Apagado de AIS (GFW, alta confianza)",
  ais_gap_local: "Pérdida de señal AIS costera (detector propio)",
  encounter: "Encuentro entre buques",
  loitering: "Buque merodeando (loitering)",
  reaparicion: "Reaparición de buque",
};

const ZONAS: Record<string, string> = {
  milla_201: "Milla 201",
  ZEE: "ZEE",
  hidrovia: "Hidrovía",
  costero: "Litoral",
  FICZ: "FICZ",
};

const STORAGE_KEY = "soberana_eventos_acumulados";

function cargarAcumulados(): Evento[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
  } catch {
    return [];
  }
}

function guardarAcumulados(eventos: Evento[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(eventos));
  } catch { /* quota exceeded: no-op, seguimos mostrando */ }
}

function fusionar(acumulados: Evento[], nuevos: Evento[]): Evento[] {
  const ids = new Set(acumulados.map((e) => e.id));
  const agregados = nuevos.filter((e) => !ids.has(e.id));
  return [...acumulados, ...agregados];
}

function csvEscape(v: unknown): string {
  if (v == null) return "";
  const s = String(v);
  if (s.includes(",") || s.includes('"') || s.includes("\n")) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function descargarCSV(eventos: Evento[]) {
  const cols: Array<keyof Evento> = [
    "id", "type", "src", "confidence", "mmsi", "vessel_name",
    "flag", "lat", "lon", "started_at", "ended_at", "zone",
  ];
  const encabezado = cols.join(",");
  const filas = eventos.map((e) => cols.map((c) => csvEscape(e[c])).join(","));
  const csv = [encabezado, ...filas].join("\n");
  const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `soberana_eventos_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
}

function fecha(iso?: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es-AR", { dateStyle: "medium", timeStyle: "short" });
}

export default function EventLog() {
  const [acumulados, setAcumulados] = useState<Evento[]>(cargarAcumulados);
  const [demo, setDemo] = useState(false);
  const [filtroTipo, setFiltroTipo] = useState("");
  const [filtroZona, setFiltroZona] = useState("");
  const [error, setError] = useState("");
  const destacado = location.hash.startsWith("#evento=") ? decodeURIComponent(location.hash.slice(8)) : "";

  useEffect(() => {
    const cargar = async () => {
      try {
        const url = HAY_BACKEND ? `${API_URL}/api/events?limit=500` : "/data/events.json";
        const data = await fetch(url).then((r) => r.json());
        const nuevos: Evento[] = data.events ?? [];
        setDemo(Boolean(data.demo) || nuevos.some((e) => e.demo));
        setAcumulados((prev) => {
          const merged = fusionar(prev, nuevos);
          guardarAcumulados(merged);
          return merged;
        });
      } catch {
        setError("No se pudo cargar el registro de eventos.");
      }
    };
    cargar();
  }, []);

  const filtrados = acumulados.filter(
    (e) => (!filtroTipo || e.type === filtroTipo) && (!filtroZona || e.zone === filtroZona),
  );

  return (
    <div className="log">
      <h2>Registro de eventos</h2>
      <p className="log-intro">
        La memoria del proyecto: cada apagado de AIS, encuentro o merodeo detectado queda registrado acá,
        con permalink. Los eventos de GFW llegan con <b>72 horas de retraso</b> (registro forense, no alerta
        táctica). Un apagado de AIS <b>no implica por sí solo actividad ilegal</b>. El registro se acumula
        localmente en tu navegador y nunca se borra.
      </p>
      {demo && (
        <div className="banner-demo">⚠ Incluye <b>datos de demostración</b>: no representan eventos reales.</div>
      )}
      {error && <div className="banner-demo">{error}</div>}

      <div className="filtros">
        <select value={filtroTipo} onChange={(e) => setFiltroTipo(e.target.value)}>
          <option value="">Todos los tipos</option>
          {Object.entries(TIPOS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={filtroZona} onChange={(e) => setFiltroZona(e.target.value)}>
          <option value="">Todas las zonas</option>
          {Object.entries(ZONAS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <span className="conteo">{filtrados.length} / {acumulados.length} eventos</span>
        <button
          className="btn-csv"
          onClick={() => descargarCSV(acumulados)}
          title="Descargar todos los eventos acumulados como CSV"
        >
          ⬇ CSV
        </button>
      </div>

      <div className="eventos">
        {filtrados.map((e) => (
          <article key={e.id} id={`evento-${e.id}`} className={`evento ${destacado === e.id ? "destacado" : ""}`}>
            <header>
              <span className={`tipo t-${e.type}`}>{TIPOS[e.type] ?? e.type}</span>
              <span className={`conf c-${e.confidence}`}>confianza {e.confidence}</span>
              {e.demo && <span className="tipo t-demo">DEMO</span>}
            </header>
            <h4>{e.vessel_name || (e.mmsi ? `MMSI ${e.mmsi}` : "buque no identificado")}{e.flag ? ` · ${e.flag}` : ""}</h4>
            <dl>
              <div><dt>Inicio</dt><dd>{fecha(e.started_at)}</dd></div>
              <div><dt>Fin</dt><dd>{e.ended_at ? fecha(e.ended_at) : "⏳ sin reaparición registrada"}</dd></div>
              <div><dt>Zona</dt><dd>{ZONAS[e.zone ?? ""] ?? e.zone ?? "—"}</dd></div>
              {e.lat != null && (
                <div><dt>Última posición</dt><dd>{e.lat.toFixed(2)}, {e.lon?.toFixed(2)}</dd></div>
              )}
              <div><dt>Fuente</dt><dd>{e.src === "gfw" ? "Global Fishing Watch" : "detector propio (Soberana)"}</dd></div>
            </dl>
            <a className="permalink" href={`#evento=${encodeURIComponent(e.id)}`}>permalink</a>
          </article>
        ))}
        {filtrados.length === 0 && <p>No hay eventos para esos filtros.</p>}
      </div>
    </div>
  );
}
