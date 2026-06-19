import { useEffect, useMemo, useRef, useState } from "react";

/** Línea de tiempo v3
 *  · SIEMPRE usable para navegar fotos SAR/VIIRS (aunque AIS esté próximamente)
 *  · Colapsable: minimizado muestra una tira fina en el fondo del mapa
 *  · Panel de fuentes: muestra a qué momento temporal apunta cada capa
 *  · Los controles AIS (play / slider de minuto) siguen en próximamente */

export const DIAS_ARCHIVO = 30;
const VELOCIDADES = [1, 2, 5, 10];

export interface Tiempo {
  fecha: string;   // YYYY-MM-DD (UTC)
  minuto: number;  // 0..1439.99
}

interface Props {
  tiempo: Tiempo | null;
  onTiempo: (t: Tiempo | null) => void;
  /** true mientras AIS no esté activo: bloquea play y slider de minuto, pero NO el navegador de fechas */
  proximamente?: boolean;
}

// ─── helpers de fecha ───────────────────────────────────────────────────────

function hoyISO(): string {
  return new Date().toISOString().slice(0, 10);
}
function diaISO(offsetDias: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - offsetDias);
  return d.toISOString().slice(0, 10);
}
function sumarDias(iso: string, n: number): string {
  const d = new Date(`${iso}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}
function fechaLegible(iso: string): string {
  return new Date(`${iso}T12:00:00Z`).toLocaleDateString("es-AR", {
    weekday: "short", day: "2-digit", month: "short",
  });
}
function fechaCorta(iso: string): string {
  return new Date(`${iso}T12:00:00Z`).toLocaleDateString("es-AR", {
    day: "2-digit", month: "short",
  });
}
function reloj(minuto: number): string {
  return `${String(Math.floor(minuto / 60)).padStart(2, "0")}:${String(Math.floor(minuto % 60)).padStart(2, "0")}`;
}
function minutoAhoraUTC(): number {
  const d = new Date();
  return d.getUTCHours() * 60 + d.getUTCMinutes();
}

// ─── panel de fuentes ────────────────────────────────────────────────────────

interface Fuente { icono: string; nombre: string; valor: string; prox?: boolean }

function calcFuentes(fecha: string | null): Fuente[] {
  const ref = fecha ?? hoyISO();
  const off = (iso: string, d: number) =>
    fechaCorta(sumarDias(iso, d));

  return [
    {
      icono: "📷",
      nombre: "SAR Sentinel-1",
      valor: `foto ~${off(ref, -5)} (retraso ~5 días)`,
    },
    {
      icono: "⚠️",
      nombre: "GFW apagones / eventos",
      valor: `datos hasta ~${off(ref, -3)} (retraso 72 h)`,
    },
    {
      icono: "📷",
      nombre: "VIIRS luces nocturnas",
      valor: "noche del día elegido",
      prox: true,
    },
    {
      icono: "🎬",
      nombre: "AIS buques",
      valor: fecha ? `película del ${fechaLegible(fecha)}` : "señal en vivo",
      prox: true,
    },
    {
      icono: "✈️",
      nombre: "Aeronaves ADS-B",
      valor: "solo en vivo, sin histórico",
      prox: true,
    },
  ];
}

// ─── componente ─────────────────────────────────────────────────────────────

export default function TimeBar({ tiempo, onTiempo, proximamente }: Props) {
  const [minimizado, setMinimizado] = useState(() =>
    localStorage.getItem("soberana_tb_min") === "1",
  );
  const [reproduciendo, setReproduciendo] = useState(false);
  const [velocidad, setVelocidad] = useState(1);

  const tiempoRef = useRef(tiempo);
  tiempoRef.current = tiempo;

  const hoy = hoyISO();
  const minFecha = diaISO(DIAS_ARCHIVO);

  const toggleMin = () =>
    setMinimizado((v) => {
      localStorage.setItem("soberana_tb_min", !v ? "1" : "0");
      return !v;
    });

  const irA = (t: Tiempo | null) => {
    if (t === null) { setReproduciendo(false); onTiempo(null); return; }
    let { fecha, minuto } = t;
    if (fecha < minFecha) fecha = minFecha;
    if (fecha > hoy) fecha = hoy;
    minuto = Math.max(0, Math.min(1439.99, minuto));
    if (fecha === hoy) minuto = Math.min(minuto, minutoAhoraUTC());
    onTiempo({ fecha, minuto });
  };

  const irDia = (n: number) => {
    setReproduciendo(false);
    const base = tiempo?.fecha ?? hoy;
    irA({ fecha: sumarDias(base, n), minuto: tiempo?.minuto ?? 12 * 60 });
  };

  // motor de reproducción AIS
  useEffect(() => {
    if (!reproduciendo) return;
    const id = window.setInterval(() => {
      const t = tiempoRef.current;
      if (!t) { setReproduciendo(false); return; }
      let minuto = t.minuto + velocidad / 60;
      let fecha = t.fecha;
      if (fecha === hoyISO() && minuto >= minutoAhoraUTC()) {
        setReproduciendo(false); onTiempo(null); return;
      }
      if (minuto >= 1440) {
        const sig = sumarDias(fecha, 1);
        if (sig > hoyISO()) { setReproduciendo(false); onTiempo(null); return; }
        fecha = sig; minuto -= 1440;
      }
      onTiempo({ fecha, minuto });
    }, 1000);
    return () => window.clearInterval(id);
  }, [reproduciendo, velocidad, onTiempo]);

  const cambiarVelocidad = () =>
    setVelocidad((v) => VELOCIDADES[(VELOCIDADES.indexOf(v) + 1) % VELOCIDADES.length]);

  const minutoMax = useMemo(
    () => (tiempo?.fecha === hoy ? minutoAhoraUTC() : 1439),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [tiempo?.fecha, hoy],
  );

  const fechaRef = tiempo?.fecha ?? hoy;
  const fuentes = calcFuentes(tiempo?.fecha ?? null);
  const modoLabel = tiempo ? (reproduciendo ? `▶ ×${velocidad}` : "ARCHIVO") : "EN VIVO";

  // ── MINIMIZADO ─────────────────────────────────────────────────────────────
  if (minimizado) {
    return (
      <div className="timebar timebar-min" role="group" aria-label="Línea de tiempo (minimizada)">
        <span className={`tb-modo-mini ${tiempo ? "archivo" : "vivo"}`}>
          {tiempo ? "⏪" : "●"} {modoLabel}
        </span>
        <span className="tb-fecha-mini">{fechaLegible(fechaRef)}</span>
        <span className="tb-sep">·</span>
        <span className="tb-srcs-mini">
          SAR ~{fechaCorta(sumarDias(fechaRef, -5))}
          <span className="tb-sep">·</span>
          GFW hasta ~{fechaCorta(sumarDias(fechaRef, -3))}
        </span>
        <button className="tb-toggle-min" onClick={toggleMin} title="Expandir">▲ EXPANDIR</button>
      </div>
    );
  }

  // ── EXPANDIDO ──────────────────────────────────────────────────────────────
  return (
    <div className="timebar" role="group" aria-label="Línea de tiempo">

      {/* fila 1: navegación de fecha */}
      <div className="tb-controles">
        <button
          onClick={() => irA({ fecha: minFecha, minuto: 12 * 60 })}
          disabled={(tiempo?.fecha ?? hoy) <= minFecha}
          title={`Ir al día más antiguo (${fechaCorta(minFecha)})`}
          className="tb-btn-nav"
        >⟪</button>
        <button
          onClick={() => irDia(-1)}
          disabled={(tiempo?.fecha ?? hoy) <= minFecha}
          title="Día anterior"
          className="tb-btn-nav"
        >◀ día</button>

        <input
          type="date"
          className="tb-fecha-input"
          value={tiempo?.fecha ?? ""}
          min={minFecha}
          max={hoy}
          onChange={(e) => {
            if (!e.target.value) return;
            setReproduciendo(false);
            irA({ fecha: e.target.value, minuto: tiempo?.minuto ?? 12 * 60 });
          }}
          aria-label="Elegir fecha"
        />

        <button
          onClick={() => irDia(1)}
          disabled={!tiempo || tiempo.fecha >= hoy}
          title="Día siguiente"
          className="tb-btn-nav"
        >día ▶</button>
        <button
          onClick={() => irA(null)}
          title="Volver a hoy (en vivo)"
          className={`tb-live ${!tiempo ? "activo" : ""}`}
        >● HOY</button>
      </div>

      {/* fila 2: controles AIS (play / velocidad / slider) */}
      <div className={`tb-ais ${proximamente ? "tb-ais-prox" : ""}`}>
        <div className="tb-ais-controles">
          <button
            className={`tb-play ${reproduciendo ? "activo" : ""}`}
            onClick={() => setReproduciendo((r) => !r)}
            disabled={proximamente || !tiempo}
            title={proximamente ? "AIS próximamente" : !tiempo ? "Elegí una fecha para reproducir" : reproduciendo ? "Pausar" : "Reproducir"}
          >{reproduciendo ? "❚❚" : "▶"}</button>
          <button onClick={cambiarVelocidad} disabled={proximamente || !tiempo}>×{velocidad}</button>
          {proximamente && <em className="badge b-proximamente" style={{ alignSelf: "center" }}>AIS próximamente</em>}
          {!proximamente && tiempo && (
            <span className="tb-hora">{reloj(tiempo.minuto)} UTC</span>
          )}
        </div>
        <input
          type="range"
          min={0}
          max={minutoMax}
          step={1}
          value={tiempo ? Math.floor(tiempo.minuto) : minutoMax}
          disabled={proximamente || !tiempo}
          onChange={(e) => irA({ fecha: tiempo?.fecha ?? hoy, minuto: Number(e.target.value) })}
          aria-label="Hora del día (AIS)"
        />
      </div>

      {/* fila 3: panel de fuentes */}
      <div className="tb-fuentes">
        {fuentes.map((f) => (
          <div key={f.nombre} className={`tb-fuente ${f.prox ? "tb-fuente-prox" : ""}`}>
            <span className="tb-fuente-icono">{f.icono}</span>
            <span className="tb-fuente-nombre">{f.nombre}</span>
            {f.prox
              ? <em className="badge b-proximamente">próximamente</em>
              : <span className="tb-fuente-valor">{f.valor}</span>}
          </div>
        ))}
      </div>

      {/* fila 4: estado + minimizar */}
      <div className="tb-footer">
        <span className={`tb-modo ${tiempo ? "archivo" : "vivo"}`}>
          {tiempo ? "⏪" : "●"} {modoLabel}
          {tiempo && ` · ${fechaLegible(tiempo.fecha)}`}
        </span>
        <button className="tb-toggle-min" onClick={toggleMin} title="Minimizar">▼ MINIMIZAR</button>
      </div>

    </div>
  );
}
