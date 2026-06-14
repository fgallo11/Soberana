import { useMemo, useState } from "react";
import { CAPAS } from "./layers";
import MapView, { type Info } from "./MapView";
import InfoCard from "./InfoCard";
import Colaborar from "./Colaborar";
import EventLog from "./EventLog";
import Metodologia from "./Metodologia";
import PixelFlag from "./PixelFlag";
import TimeBar, { type Tiempo } from "./TimeBar";

type Pestania = "mapa" | "eventos" | "metodologia" | "colaborar";

export default function App() {
  const [pestania, setPestania] = useState<Pestania>(
    location.hash.startsWith("#evento") ? "eventos" : "mapa",
  );
  const [tiempo, setTiempo] = useState<Tiempo | null>(null); // null = en vivo (hoy: deshabilitado)
  const [panelAbierto, setPanelAbierto] = useState(false); // cajón de capas (móvil)
  const [info, setInfo] = useState<Info | null>(null); // ficha del feature tocado
  const [visibles, setVisibles] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(CAPAS.map((c) => [c.id, c.defaultOn && !c.proximamente])),
  );

  const grupos = useMemo(() => {
    const g = new Map<string, typeof CAPAS>();
    for (const c of CAPAS) {
      if (!g.has(c.grupo)) g.set(c.grupo, [] as unknown as typeof CAPAS);
      (g.get(c.grupo) as any).push(c);
    }
    return [...g.entries()];
  }, []);

  return (
    <div className="app">
      <header className="cabecera">
        <div className="marca">
          <PixelFlag escala={2} />
          <div>
            <h1>SOBERANA<span className="cursor">█</span></h1>
            <span className="lema">&gt;&gt; soberanía argentina a la vista · mar · ríos · aire · territorio · datos abiertos · sin publicidad</span>
          </div>
        </div>
        <nav className="pestanias">
          <button className={pestania === "mapa" ? "activa" : ""} onClick={() => setPestania("mapa")}>[ MAPA ]</button>
          <button className={pestania === "eventos" ? "activa" : ""} onClick={() => setPestania("eventos")}>
            [ EVENTOS ]
          </button>
          <button className={pestania === "metodologia" ? "activa" : ""} onClick={() => setPestania("metodologia")}>
            [ QUÉ ESTÁS VIENDO ]
          </button>
          <button
            className={`tab-colaborar ${pestania === "colaborar" ? "activa" : ""}`}
            onClick={() => setPestania("colaborar")}
          >
            [ COLABORÁ ]
          </button>
        </nav>
      </header>

      {pestania === "mapa" && (
        <div className="cuerpo">
          <button
            className="toggle-capas"
            onClick={() => setPanelAbierto((v) => !v)}
            aria-expanded={panelAbierto}
          >
            {panelAbierto ? "✕ CERRAR" : "▣ CAPAS"}
          </button>
          {panelAbierto && <div className="panel-backdrop" onClick={() => setPanelAbierto(false)} />}
          <aside className={`panel ${panelAbierto ? "abierto" : ""}`}>
            {grupos.map(([grupo, capas]) => (
              <section key={grupo}>
                <h3>{grupo}</h3>
                {capas.map((c) => {
                  const prox = Boolean(c.proximamente);
                  return (
                    <label key={c.id} className={`capa ${prox ? "deshabilitada" : ""}`}>
                      <input
                        type="checkbox"
                        checked={Boolean(visibles[c.id]) && !prox}
                        disabled={prox}
                        onChange={(e) => setVisibles((v) => ({ ...v, [c.id]: e.target.checked }))}
                      />
                      <span className="capa-titulo">
                        {c.titulo}{" "}
                        {prox
                          ? <em className="badge b-proximamente">próximamente</em>
                          : <em className={`badge b-${c.badge.replace(/[^a-z0-9]+/gi, "")}`}>{c.badge}</em>}
                      </span>
                      <small>{c.descripcion}</small>
                    </label>
                  );
                })}
              </section>
            ))}
            <p className="atribucion">
              Datos: Global Fishing Watch · EOG/NOAA (VIIRS) · adsb.lol · aisstream.io · Prefectura Naval ·
              IGN · OpenStreetMap. Geometrías marcadas “aproximadas” son provisorias.
            </p>
          </aside>
          <div className="mapa-zona">
            <MapView visibles={visibles} tiempo={tiempo} onSelect={setInfo} />
            {info && <InfoCard info={info} onClose={() => setInfo(null)} />}
            <TimeBar tiempo={tiempo} onTiempo={setTiempo} proximamente />
          </div>
        </div>
      )}

      {pestania === "eventos" && <EventLog />}
      {pestania === "metodologia" && <Metodologia />}
      {pestania === "colaborar" && <Colaborar />}
    </div>
  );
}
