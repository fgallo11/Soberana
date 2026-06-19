function Prox() {
  return <em className="badge b-proximamente">próximamente</em>;
}

export default function Metodologia() {
  return (
    <div className="metodologia">
      <h2>Qué estás viendo (y qué no)</h2>

      <section>
        <h3>La regla de oro</h3>
        <p>
          Este mapa muestra <b>actividad aparente</b> según sensores abiertos y señales transmitidas
          públicamente. No muestra delitos, no identifica culpables, y la ausencia de un buque en el mapa{" "}
          <b>no</b> significa que no esté ahí. Cada capa declara su retraso real.
        </p>
      </section>

      <section>
        <h3>Las capas del mapa</h3>
        <ul>
          <li>
            <b>Soberanía territorial:</b> ZEE, FICZ/FOCZ (Malvinas), Antártida, bases militares, áreas
            protegidas, infraestructura crítica en manos extranjeras y extranjerización de tierras.
            Todo estático, basado en cartografía del IGN y datos del RNTR.
          </li>
          <li>
            <b>Radar satelital SAR (Sentinel-1) · ~5 días de retraso:</b> una foto por pasada del
            satélite, no una película. Detecta cualquier casco metálico transmita o no AIS. Rojo = buque
            sin AIS ("dark"); gris = con AIS. Fuente: Global Fishing Watch.
          </li>
          <li>
            <b>Apagones de AIS (alarmas) · ~72 h:</b> última posición conocida de buques que dejaron de
            transmitir. Indica dónde desapareció la señal, no necesariamente dónde está el buque ahora.
          </li>
          <li>
            <b>Hidrovía y puertos:</b> traza de la Vía Navegable Troncal Paraná–Paraguay con puertos
            de la Dirección Nacional de Puertos. Estático.
          </li>
          <li>
            <b>Luces nocturnas VIIRS · ~24 h:</b> detecta los reflectores de la flota potera aunque
            apague el AIS — solo de noche; nubes y luna llena lo degradan. <Prox />
          </li>
          <li>
            <b>Esfuerzo pesquero GFW:</b> heatmap de actividad pesquera aparente de los últimos 30 días
            según AIS satelital. <Prox />
          </li>
          <li>
            <b>Buques AIS en vivo / archivo · minutos de retraso:</b> posiciones AIS de la Hidrovía y el
            litoral en tiempo casi real, y reproducción de días anteriores fotograma a fotograma. El AIS
            terrestre <b>no llega a la milla 201</b>: lo que ocurre allá solo aparece en las fotos
            satelitales. <Prox />
          </li>
          <li>
            <b>Alturas del río:</b> nivel del Paraná en cada puerto. Fuente: Prefectura Naval. <Prox />
          </li>
          <li>
            <b>Aeronaves (incl. militares) · en vivo:</b> tráfico captado por la red comunitaria ADS-B,
            sin filtrar. Incluye el puente aéreo RAF a la base de Mount Pleasant en las Islas Malvinas. <Prox />
          </li>
        </ul>
      </section>

      <section>
        <h3>Por qué "tiempo real" tiene letra chica</h3>
        <p>
          "En vivo" en este mapa significa distintas cosas según la capa. El AIS costero demora minutos
          pero <b>no cubre la milla 201</b> (a ~370 km de la costa). El radar SAR ve toda el agua pero
          llega con 5 días de retraso. GFW procesa el AIS satelital con 72 horas de demora. Ninguna
          fuente muestra todo en tiempo real: el mapa combina lo mejor de cada una y declara el retraso
          honestamente en cada capa.
        </p>
      </section>

      <section>
        <h3>Sobre los buques "dark"</h3>
        <p>
          Un punto rojo (detección SAR sin AIS) o un evento de apagado de AIS indica que un buque estaba
          presente sin transmitir su posición. Hay causas ilegítimas (pesca ilegal, transbordos) y causas
          técnicas o legales (fallas, buques no obligados a transmitir).{" "}
          <b>El dato es evidencia para investigar, no una condena.</b> Además, el AIS es autoreportado:
          posición e identidad pueden falsearse (spoofing).
        </p>
      </section>

      <section>
        <h3>Sobre la capa militar</h3>
        <p>
          Las aeronaves militares visibles son las que la red comunitaria ADS-B captura con el transponder
          encendido — una fracción del total. Los buques de guerra no transmiten AIS (solo pueden aparecer
          como detecciones SAR sin identificar). <b>Lo visible es una fracción de lo que existe.</b>
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
          Las geometrías marcadas "aproximadas" (ZEE, FOCZ, AMPs, traza de la Hidrovía) son provisorias
          y se reemplazan por las fuentes de referencia oficiales (Marine Regions, IGN).
        </p>
      </section>

      <section>
        <h3>El proyecto</h3>
        <p>
          Soberana es software libre, sin fines de lucro, sin publicidad y gratuito a perpetuidad. Su único
          objetivo es que cualquier persona pueda ver qué pasa en los mares y ríos argentinos. El código,
          los pipelines de datos y este sitio son públicos y auditables.
        </p>
      </section>
    </div>
  );
}
