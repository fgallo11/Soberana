import type { Info } from "./MapView";

function fmtCoord(lng: number, lat: number): string {
  const ns = lat < 0 ? "S" : "N";
  const ew = lng < 0 ? "O" : "E";
  return `${Math.abs(lat).toFixed(4)}°${ns}, ${Math.abs(lng).toFixed(4)}°${ew}`;
}

/** Ficha de información de un feature del mapa.
 * En escritorio: tarjeta acotada abajo a la izquierda, con scroll interno.
 * En móvil: panel inferior (hoja) que nunca se desborda de la pantalla.
 * Reemplaza al popup anclado de MapLibre, que con textos largos se iba
 * fuera de pantalla. */
export default function InfoCard({ info, onClose }: { info: Info; onClose: () => void }) {
  const filas = info.filas.filter(([, v]) => v !== null && v !== undefined && v !== "");
  return (
    <div className={`infocard ${info.alerta ? "alerta" : ""}`} role="dialog" aria-label={info.titulo}>
      <header>
        <h3>{info.titulo}</h3>
        <button className="ic-cerrar" onClick={onClose} aria-label="Cerrar">✕</button>
      </header>
      <div className="ic-cuerpo">
        {filas.length > 0 && (
          <dl className="ic-datos">
            {filas.map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{String(v)}</dd>
              </div>
            ))}
          </dl>
        )}
        {info.descripcion && <p className="ic-desc">{info.descripcion}</p>}
        {info.nota && <p className="ic-nota">{info.nota}</p>}
        {info.coord && (
          <div className="ic-coord">📍 {fmtCoord(info.coord[0], info.coord[1])}</div>
        )}
        {info.fuente && <div className="ic-fuente">fuente: {info.fuente}</div>}
      </div>
    </div>
  );
}
