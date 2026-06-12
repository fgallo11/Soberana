import { useEffect, useMemo, useRef, useState } from "react";
import { HAY_BACKEND } from "./config";

/** Barra de tiempo estilo videocasetera: EN VIVO ↔ archivo de los últimos
 * 30 días, con PLAY: parado en cualquier día del pasado, reproduce el
 * avance del tiempo (1 día por tick) a velocidad seleccionable, como ver
 * los movimientos en película. Al llegar al presente vuelve a EN VIVO.
 * `fecha` null = en vivo; "YYYY-MM-DD" = modo archivo. */

export const DIAS_ARCHIVO = 30;
const VELOCIDADES = [1, 2, 4]; // días por segundo

interface Props {
  fecha: string | null;
  onFecha: (f: string | null) => void;
}

function diaISO(offset: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - offset);
  return d.toISOString().slice(0, 10);
}

function fechaLegible(iso: string): string {
  return new Date(`${iso}T12:00:00Z`).toLocaleDateString("es-AR", {
    weekday: "short", day: "2-digit", month: "short", year: "numeric",
  });
}

export default function TimeBar({ fecha, onFecha }: Props) {
  const [reproduciendo, setReproduciendo] = useState(false);
  const [velocidad, setVelocidad] = useState(1);

  // offset 0 = hoy (vivo); 1..DIAS_ARCHIVO = días hacia atrás
  const offset = useMemo(() => {
    if (!fecha) return 0;
    const ms = Date.now() - new Date(`${fecha}T12:00:00Z`).getTime();
    return Math.min(DIAS_ARCHIVO, Math.max(1, Math.round(ms / 86_400_000)));
  }, [fecha]);
  const offsetRef = useRef(offset);
  offsetRef.current = offset;

  const mover = (nuevo: number) => {
    const o = Math.min(DIAS_ARCHIVO, Math.max(0, nuevo));
    if (o === 0) setReproduciendo(false); // llegar al presente corta la reproducción
    onFecha(o === 0 ? null : diaISO(o));
  };

  // motor de reproducción: avanza un día por tick hasta alcanzar el presente
  useEffect(() => {
    if (!reproduciendo) return;
    const id = window.setInterval(() => {
      const o = offsetRef.current;
      if (o <= 1) {
        setReproduciendo(false);
        onFecha(null); // llegó al presente: vuelve a EN VIVO
      } else {
        onFecha(diaISO(o - 1));
      }
    }, 1000 / velocidad);
    return () => window.clearInterval(id);
  }, [reproduciendo, velocidad, onFecha]);

  const togglePlay = () => {
    if (reproduciendo) {
      setReproduciendo(false);
      return;
    }
    // play desde EN VIVO: arranca la película desde el fondo del archivo
    if (offsetRef.current === 0) onFecha(diaISO(DIAS_ARCHIVO));
    setReproduciendo(true);
  };

  const cambiarVelocidad = () => {
    setVelocidad((v) => VELOCIDADES[(VELOCIDADES.indexOf(v) + 1) % VELOCIDADES.length]);
  };

  return (
    <div className="timebar" role="group" aria-label="Viaje en el tiempo">
      <div className="tb-controles">
        <button onClick={() => mover(offset + 1)} disabled={offset >= DIAS_ARCHIVO} title="Un día atrás">
          ◀◀
        </button>
        <button
          className={`tb-play ${reproduciendo ? "activo" : ""}`}
          onClick={togglePlay}
          title={reproduciendo ? "Pausar" : "Reproducir el paso del tiempo desde este punto"}
        >
          {reproduciendo ? "❚❚" : "▶"}
        </button>
        <button onClick={() => mover(offset - 1)} disabled={offset === 0} title="Un día adelante">
          ▶▶
        </button>
        <button onClick={cambiarVelocidad} title="Velocidad de reproducción (días por segundo)">
          ×{velocidad}
        </button>
        <button className={`tb-live ${fecha ? "" : "activo"}`} onClick={() => mover(0)} title="Volver al presente">
          ● VIVO
        </button>
      </div>
      <input
        type="range"
        min={0}
        max={DIAS_ARCHIVO}
        step={1}
        // el slider corre de izquierda (pasado) a derecha (presente)
        value={DIAS_ARCHIVO - offset}
        onChange={(e) => mover(DIAS_ARCHIVO - Number(e.target.value))}
        aria-label={`Día mostrado: ${fecha ?? "en vivo"}`}
      />
      <div className="tb-estado">
        {fecha ? (
          <>
            <span className="tb-modo archivo">{reproduciendo ? "▶ REPRODUCIENDO" : "⏪ ARCHIVO"}</span>
            <span className="tb-fecha">{fechaLegible(fecha)}</span>
          </>
        ) : (
          <>
            <span className="tb-modo vivo">● EN VIVO</span>
            <span className="tb-fecha">señal actual (pseudovivo)</span>
          </>
        )}
      </div>
      {fecha && (
        <div className="tb-nota">
          {reproduciendo
            ? `reproduciendo a ${velocidad} día${velocidad > 1 ? "s" : ""} por segundo — al llegar a hoy vuelve a EN VIVO`
            : <>satélites: día seleccionado · AIS: {HAY_BACKEND ? "estado de ese día (retención 14 d)" : "requiere backend"} · aeronaves: solo en vivo</>}
        </div>
      )}
    </div>
  );
}
