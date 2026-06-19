export default function Metodologia() {
  return (
    <div className="metodologia">
      <h2>Lo que se viene</h2>
      <p className="log-intro">
        Soberana está en construcción activa. Estas son las capacidades que se están desarrollando.
        Todo es software libre, sin publicidad y sin costo.
      </p>

      <section>
        <h3>AIS en tiempo real · aguas exteriores</h3>
        <p>
          El AIS costero llega hasta ~200 km de la costa. Para cubrir la milla 201 y alta mar necesitamos
          receptores satelitales. Se está integrando cobertura satelital de bajo costo para ver toda la ZEE
          y la FOCZ con minutos de retraso, no solo el litoral.
        </p>
      </section>

      <section>
        <h3>Detector propio de apagados AIS</h3>
        <p>
          En lugar de depender exclusivamente del retraso de 72 horas de GFW, Soberana está desarrollando
          su propio detector de pérdidas de señal en tiempo casi real: si un buque deja de transmitir en zona
          sensible, la alarma aparece en minutos, no días.
        </p>
      </section>

      <section>
        <h3>Radar SAR en tiempo casi real</h3>
        <p>
          Las detecciones actuales de Sentinel-1 llegan con ~5 días de retraso a través de GFW. Se está
          explorando el acceso directo a los datos SAR de la ESA para reducir ese lag a menos de 24 horas y
          ampliar la cobertura satelital al Atlántico Sur.
        </p>
      </section>

      <section>
        <h3>Histórico descargable</h3>
        <p>
          Todas las posiciones, eventos y detecciones históricas van a estar disponibles para descarga en
          formato CSV y GeoJSON. El objetivo es que investigadores, periodistas y ciudadanos puedan auditar
          los datos sin depender de esta interfaz.
        </p>
      </section>

      <section>
        <h3>Alertas por zona y tipo de buque</h3>
        <p>
          Suscripción a alertas cuando se detecta actividad relevante en zonas específicas: apagones de AIS
          en la milla 201, encuentros buque-a-buque fuera de puertos conocidos, o presencia de flotas
          extranjeras en áreas protegidas. Sin rastreo de usuarios, sin publicidad.
        </p>
      </section>

      <section>
        <h3>Hidrovía: tráfico fluvial completo</h3>
        <p>
          La Hidrovía Paraná-Paraguay concentra el 80% del comercio exterior argentino. Se está trabajando
          en cobertura AIS continua de todo el tramo, integración con los datos de calado y alturas de
          Prefectura Naval, y cruce con el padrón de buques habilitados.
        </p>
      </section>

      <section>
        <h3>Malvinas: cobertura dedicada</h3>
        <p>
          Las Islas Malvinas (territorio argentino actualmente bajo administración británica, conforme a la
          cartografía oficial del IGN) tienen un espacio marítimo con actividad pesquera intensiva fuera de
          cualquier control argentino. Se está trabajando en una vista dedicada que muestre qué se captura
          en esas aguas y quién lo captura.
        </p>
      </section>

      <section>
        <h3>API pública</h3>
        <p>
          El backend de Soberana va a exponer una API pública y documentada para que otros proyectos,
          medios de comunicación y organismos del Estado puedan consultar los datos directamente.
          Sin límites de uso, sin clave de API, sin costo.
        </p>
      </section>

      <section>
        <h3>Sobre el proyecto</h3>
        <p>
          Soberana es software libre, sin fines de lucro, sin publicidad y gratuito a perpetuidad.
          El código, los pipelines de datos y este sitio son públicos y auditables.
          Si querés contribuir — datos, código, financiamiento o difusión — visitá la pestaña{" "}
          <b>[ COLABORÁ ]</b>.
        </p>
      </section>
    </div>
  );
}
