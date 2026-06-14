import { useEffect, useMemo, useRef, useState } from "react";

/** Barra de tiempo v2 — el modelo es "película del día":
 *  - Elegís una FECHA (hasta 30 días atrás) y un momento DENTRO del día
 *    con el slider (00:00–24:00).
 *  - PLAY reproduce el movimiento a ritmo real (×1) o acelerado ×2/×5/×10.
 *    En VIVO el play está deshabilitado: lo vivo ya corre solo.
 *  - Los buques son película (recorridos AIS interpolados); las capas
 *    satelitales (SAR/VIIRS) son FOTOS del día elegido y no se mueven.
 *  `tiempo` null = en vivo; {fecha, minuto} = modo archivo. */

export const DIAS_ARCHIVO = 30;
const VELOCIDADES = [1, 2, 5, 10]; // multiplicador sobre el ritmo real

export interface Tiempo {
  fecha: string;   // YYYY-MM-DD (UTC)
  minuto: number;  // 0..1439.99 dentro del día
}

interface Props {
  tiempo: Tiempo | null;
  onTiempo: (t: Tiempo | null) => void;
  /** modo "próximamente": el reproductor se ve pero no responde (sin datos vivos/históricos aún) */
  proximamente?: boolean;
}

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

function reloj(minuto: number): string {
  const h = Math.floor(minuto / 60);
  const m = Math.floor(minuto % 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

function minutoAhoraUTC(): number {
  const d = new Date();
  return d.getUTCHours() * 60 + d.getUTCMinutes();
}

export default function TimeBar({ tiempo, onTiempo, proximamente }: Props) {
  const [reproduciendo, setReproduciendo] = useState(false);
  const [velocidad, setVelocidad] = useState(1);

  const tiempoRef = useRef(tiempo);
  tiempoRef.current = tiempo;

  const hoy = hoyISO();
  const minFecha = diaISO(DIAS_ARCHIVO);
  const esHoy = tiempo?.fecha === hoy;

  const irA = (t: Tiempo | null) => {
    if (t === null) {
      setReproduciendo(false);
      onTiempo(null);
      return;
    }
    let { fecha, minuto } = t;
    if (fecha < minFecha) fecha = minFecha;
    if (fecha > hoy) fecha = hoy;
    minuto = Math.max(0, Math.min(1439.99, minuto));
    // no se puede mirar el futuro: hoy el día llega hasta ahora
    if (fecha === hoy) minuto = Math.min(minuto, minutoAhoraUTC());
    onTiempo({ fecha, minuto });
  };

  // motor de reproducción: ritmo real ×velocidad (tick de 1 s)
  useEffect(() => {
    if (!reproduciendo) return;
    const id = window.setInterval(() => {
      const t = tiempoRef.current;
      if (!t) { setReproduciendo(false); return; }
      let minuto = t.minuto + velocidad / 60; // +N segundos de datos por segundo real
      let fecha = t.fecha;
      if (fecha === hoyISO() && minuto >= minutoAhoraUTC()) {
        // la película alcanzó el presente: se pasa a EN VIVO, naturalmente
        setReproduciendo(false);
        onTiempo(null);
        return;
      }
      if (minuto >= 1440) {
        const siguiente = sumarDias(fecha, 1);
        if (siguiente > hoyISO()) { setReproduciendo(false); onTiempo(null); return; }
        fecha = siguiente;
        minuto -= 1440;
      }
      onTiempo({ fecha, minuto });
    }, 1000);
    return () => window.clearInterval(id);
  }, [reproduciendo, velocidad, onTiempo]);

  const cambiarVelocidad = () =>
    setVelocidad((v) => VELOCIDADES[(VELOCIDADES.indexOf(v) + 1) % VELOCIDADES.length]);

  const minutoMax = useMemo(() => (esHoy ? minutoAhoraUTC() : 1439), [esHoy, tiempo]);

  // Modo "próximamente": el reproductor sigue visible pero inerte. El viaje en
  // el tiempo y la vista en vivo de buques se activan cuando el sistema empiece
  // a registrar posiciones AIS (VM con aisstream).
  if (proximamente) {
    return (
      <div className="timebar timebar-prox" role="group" aria-label="Línea de tiempo (próximamente)">
        <div className="tb-controles">
          <input type="date" className="tb-fecha-input" value="" disabled readOnly aria-hidden />
          <button disabled>◀</button>
          <button className="tb-play" disabled>▶</button>
          <button disabled>▶</button>
          <button disabled>×1</button>
          <button className="tb-live" disabled>● VIVO</button>
        </div>
        <input type="range" min={0} max={100} value={0} disabled readOnly aria-hidden />
        <div className="tb-estado">
          <span className="tb-modo prox">⏪ ARCHIVO · próximamente</span>
          <span className="tb-fecha">vista en vivo e histórico: en preparación</span>
        </div>
        <div className="tb-nota">
          🎬 La reproducción de movimientos (AIS en vivo e histórico) se activará cuando el sistema
          empiece a registrar posiciones. Por ahora el mapa muestra el estado disponible.
        </div>
      </div>
    );
  }

  return (
    <div className="timebar" role="group" aria-label="Viaje en el tiempo">
      <div className="tb-controles">
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
          aria-label="Elegir fecha del archivo"
        />
        <button
          onClick={() => { setReproduciendo(false); irA({ fecha: sumarDias(tiempo?.fecha ?? hoy, -1), minuto: tiempo?.minuto ?? 12 * 60 }); }}
          disabled={(tiempo?.fecha ?? hoy) <= minFecha}
          title="Día anterior"
        >
          ◀
        </button>
        <button
          onClick={() => { setReproduciendo(false); irA({ fecha: sumarDias(tiempo!.fecha, 1), minuto: tiempo!.minuto }); }}
          disabled={!tiempo || tiempo.fecha >= hoy}
          title="Día siguiente"
        >
          ▶
        </button>
        <button
          className={`tb-play ${reproduciendo ? "activo" : ""}`}
          onClick={() => setReproduciendo((r) => !r)}
          disabled={!tiempo}
          title={!tiempo
            ? "El play es para el archivo: en vivo, lo que ves ya está corriendo"
            : reproduciendo ? "Pausar" : "Reproducir el movimiento desde este momento"}
        >
          {reproduciendo ? "❚❚" : "▶"}
        </button>
        <button onClick={cambiarVelocidad} disabled={!tiempo} title="Velocidad (×1 = ritmo real)">
          ×{velocidad}
        </button>
        <button className={`tb-live ${tiempo ? "" : "activo"}`} onClick={() => irA(null)} title="Volver al presente">
          ● VIVO
        </button>
      </div>

      <input
        type="range"
        min={0}
        max={minutoMax}
        step={1}
        value={tiempo ? Math.floor(tiempo.minuto) : minutoMax}
        disabled={!tiempo}
        onChange={(e) => irA({ fecha: tiempo?.fecha ?? hoy, minuto: Number(e.target.value) })}
        aria-label={tiempo ? `Hora del día: ${reloj(tiempo.minuto)}` : "Elegí una fecha para navegar el día"}
      />

      <div className="tb-estado">
        {tiempo ? (
          <>
            <span className="tb-modo archivo">{reproduciendo ? `▶ ×${velocidad}` : "⏪ ARCHIVO"}</span>
            <span className="tb-fecha">{fechaLegible(tiempo.fecha)} · {reloj(tiempo.minuto)} UTC</span>
          </>
        ) : (
          <>
            <span className="tb-modo vivo">● EN VIVO</span>
            <span className="tb-fecha">señal actual (pseudovivo)</span>
          </>
        )}
      </div>

      {tiempo && (
        <div className="tb-nota">
          🎬 buques: película del día (recorridos AIS interpolados) · 📷 SAR/VIIRS: foto del día elegido,
          no se mueven · aeronaves: solo en vivo
        </div>
      )}
    </div>
  );
}
