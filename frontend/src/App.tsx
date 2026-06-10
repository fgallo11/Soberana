import { useCallback, useMemo, useState } from "react";
import { HAY_BACKEND } from "./config";
import { CAPAS } from "./layers";
import MapView from "./MapView";
import EventLog from "./EventLog";
import Metodologia from "./Metodologia";

type Pestania = "mapa" | "eventos" | "metodologia";

export default function App() {
  const [pestania, setPestania] = useState<Pestania>(
    location.hash.startsWith("#evento") ? "eventos" : "mapa",
  );
  const [demo, setDemo] = useState(false);
  const [visibles, setVisibles] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(CAPAS.map((c) => [c.id, c.defaultOn && !(c.requiereBackend && !HAY_BACKEND)])),
  );
  const onDemo = useCallback(() => setDemo(true), []);

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
          <h1>Soberana</h1>
          <span className="lema">qué pasa en el mar argentino — datos abiertos, sin publicidad, para siempre</span>
        </div>
        <nav className="pestanias">
          <button className={pestania === "mapa" ? "activa" : ""} onClick={() => setPestania("mapa")}>Mapa</button>
          <button className={pestania === "eventos" ? "activa" : ""} onClick={() => setPestania("eventos")}>
            Registro de eventos
          </button>
          <button className={pestania === "metodologia" ? "activa" : ""} onClick={() => setPestania("metodologia")}>
            Qué estás viendo (y qué no)
          </button>
        </nav>
      </header>

      {demo && pestania === "mapa" && (
        <div className="banner-demo">
          ⚠ Algunas capas muestran <b>datos de demostración</b> (no representan buques ni eventos reales).
          Se reemplazan automáticamente cuando los jobs de ingesta corren con credenciales configuradas.
        </div>
      )}

      {pestania === "mapa" && (
        <div className="cuerpo">
          <aside className="panel">
            {grupos.map(([grupo, capas]) => (
              <section key={grupo}>
                <h3>{grupo}</h3>
                {capas.map((c) => {
                  const deshabilitada = Boolean(c.requiereBackend && !HAY_BACKEND);
                  return (
                    <label key={c.id} className={`capa ${deshabilitada ? "deshabilitada" : ""}`}>
                      <input
                        type="checkbox"
                        checked={visibles[c.id] && !deshabilitada}
                        disabled={deshabilitada}
                        onChange={(e) => setVisibles((v) => ({ ...v, [c.id]: e.target.checked }))}
                      />
                      <span className="capa-titulo">
                        {c.titulo} <em className={`badge b-${c.badge.replace(/[^a-z0-9]+/gi, "")}`}>{c.badge}</em>
                      </span>
                      <small>
                        {c.descripcion}
                        {deshabilitada && " (requiere el backend desplegado — ver docs/despliegue.md)"}
                      </small>
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
          <MapView visibles={visibles} onDemo={onDemo} />
        </div>
      )}

      {pestania === "eventos" && <EventLog />}
      {pestania === "metodologia" && <Metodologia />}
    </div>
  );
}
