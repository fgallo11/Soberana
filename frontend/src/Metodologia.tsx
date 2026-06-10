export default function Metodologia() {
  return (
    <div className="metodologia">
      <h2>Qué estás viendo (y qué no)</h2>

      <section>
        <h3>La regla de oro</h3>
        <p>
          Este mapa muestra <b>actividad aparente</b> según sensores abiertos y señales transmitidas públicamente.
          No muestra delitos, no identifica culpables, y la ausencia de un buque en el mapa <b>no</b> significa que
          no esté ahí. Cada capa declara su retraso real.
        </p>
      </section>

      <section>
        <h3>Por qué “tiempo real” tiene letra chica</h3>
        <ul>
          <li>
            <b>AIS costero/fluvial (en vivo):</b> el AIS terrestre llega a ~200 km de la costa. La Hidrovía y el
            litoral se ven con minutos de retraso. <b>La milla 201 (a ~370 km) no se ve por AIS terrestre: nadie
            la ve gratis en vivo.</b>
          </li>
          <li>
            <b>Global Fishing Watch (72 hs):</b> posiciones satelitales, esfuerzo pesquero y eventos llegan con
            tres días de retraso. Sirven para entender patrones, no para reaccionar.
          </li>
          <li>
            <b>Radar satelital SAR (~5 días):</b> Sentinel-1 ve cualquier casco metálico, transmita o no. Pero pasa
            cada 6–12 días por cada punto: entre pasadas, no hay datos.
          </li>
          <li>
            <b>Luces nocturnas VIIRS (~24 hs):</b> detecta las lámparas de la flota potera. Solo de noche; nubes y
            luna llena lo degradan.
          </li>
        </ul>
      </section>

      <section>
        <h3>Sobre los buques “dark”</h3>
        <p>
          Un punto rojo (detección SAR sin AIS) o un evento de apagado de AIS indican que un buque estaba presente
          sin transmitir su posición. Hay causas ilegítimas (pesca ilegal, transbordos) y causas técnicas o legales
          (fallas, buques no obligados a transmitir). <b>El dato es evidencia para investigar, no una condena.</b>
          Además, el AIS es autoreportado: la posición y la identidad pueden falsearse (spoofing).
        </p>
      </section>

      <section>
        <h3>Sobre la capa militar</h3>
        <p>
          Mostramos toda aeronave que la red comunitaria ADS-B capte, de cualquier fuerza, sin filtrar — incluido el
          puente aéreo de la RAF a la base de Mount Pleasant, en las Islas Malvinas (territorio argentino ocupado,
          conforme a la cartografía oficial del IGN). Limitación honesta: <b>los buques de guerra no transmiten AIS</b>
          (solo pueden aparecer como detecciones SAR sin identificar) y muchas aeronaves militares vuelan con el
          transponder apagado. Lo visible es una fracción.
        </p>
      </section>

      <section>
        <h3>Fuentes y licencias</h3>
        <ul>
          <li>Actividad pesquera, detecciones SAR y eventos: <a href="https://globalfishingwatch.org">Global Fishing Watch</a> (atribución obligatoria).</li>
          <li>Luces de barcos: VIIRS Boat Detection, <a href="https://eogdata.mines.edu">Earth Observation Group</a> (Colorado School of Mines / NOAA).</li>
          <li>AIS costero: <a href="https://aisstream.io">aisstream.io</a> (red comunitaria).</li>
          <li>Tráfico aéreo: <a href="https://adsb.lol">adsb.lol</a> (red comunitaria, datos sin filtrar).</li>
          <li>Alturas de los ríos: <a href="https://contenidosweb.prefecturanaval.gob.ar/alturas/">Prefectura Naval Argentina</a>.</li>
          <li>Cartografía: <a href="https://www.ign.gob.ar">IGN</a>, <a href="https://www.openstreetmap.org">OpenStreetMap</a>, basemap de <a href="https://openfreemap.org">OpenFreeMap</a>.</li>
        </ul>
        <p>
          Las geometrías marcadas “aproximadas” (ZEE, FOCZ, AMPs, traza de la Hidrovía) son provisorias y se
          reemplazan por las fuentes de referencia (Marine Regions, IGN). La FICZ responde a su definición publicada:
          círculo de 150 millas náuticas centrado en 51°40′S 59°30′W.
        </p>
      </section>

      <section>
        <h3>El proyecto</h3>
        <p>
          Soberana es software libre, sin fines de lucro, sin publicidad y gratuito a perpetuidad. Su único objetivo
          es que cualquier persona pueda ver qué pasa en los mares y ríos argentinos. El código, los pipelines de
          datos y este sitio son públicos y auditables en el repositorio del proyecto.
        </p>
      </section>
    </div>
  );
}
