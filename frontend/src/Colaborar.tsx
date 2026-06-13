const REPO = "https://github.com/fgallo11/Soberana";

export default function Colaborar() {
  return (
    <div className="metodologia colaborar">
      <h2>Construyamos esto entre todos</h2>

      <section>
        <h3>El objetivo</h3>
        <p>
          Soberana es una herramienta <b>soberana y nuestra</b>: un mapa público, gratuito a perpetuidad,
          sin publicidad y de código abierto, para que cualquier persona pueda ver más claro{" "}
          <b>dónde nos invaden, dónde nos sacan, cuándo y cómo</b> — en el mar, en los ríos, en el aire
          y en el territorio. Ninguna fuente aislada dice mucho; combinadas sobre un mismo mapa revelan
          patrones, <b>incluyendo lo que NO aparece</b>: el buque que apaga su señal, el radar que detecta
          un casco donde nadie dice estar.
        </p>
        <p>
          Nadie es dueño de esto. El código, los pipelines de datos y cada decisión están a la vista en{" "}
          <a href={REPO} target="_blank" rel="noreferrer">github.com/fgallo11/Soberana</a> — auditables,
          criticables y mejorables por cualquiera.
        </p>
      </section>

      <section>
        <h3>Qué estamos buscando incorporar ahora</h3>
        <ul>
          <li>
            <b>AIS en vivo 24/7:</b> falta desplegar el servidor permanente (hay guía paso a paso en{" "}
            <code>docs/despliegue.md</code>, costo $0). Quien sepa de Linux/servidores puede ayudar a operarlo.
          </li>
          <li>
            <b>Datos y acceso a datos:</b> esto es lo que más suma. ¿Ya operás un receptor AIS o de ADS-B?
            ¿Trabajás en un puerto, una terminal, un organismo con datos que deberían ser públicos? ¿Tenés
            acceso legítimo a una fuente que nos falta? Compartir el feed o el dato es la colaboración más
            valiosa que existe para este proyecto.
          </li>
          <li>
            <b>Verificación de geometrías:</b> varias capas están marcadas “aproximadas” (ZEE, AMPs, FOCZ).
            Si trabajás con SIG, ayudanos a reemplazarlas por las fuentes de referencia (Marine Regions, IGN).
          </li>
          <li>
            <b>Luces nocturnas VIIRS:</b> en trámite la credencial de descarga de EOG; cuando llegue, la capa
            pasa de demostración a datos reales sin tocar código.
          </li>
          <li>
            <b>Nuevos dominios de soberanía</b> (ver la visión en <code>docs/vision.md</code>): fronteras y
            presencia militar extranjera, energía (litio, hidrocarburos), infraestructura digital (cables
            submarinos), tráfico aéreo. Cada dominio arranca igual: encontrar la fuente abierta, documentarla,
            convertirla en capa.
          </li>
        </ul>
      </section>

      <section>
        <h3>Cómo colaborar</h3>
        <ul>
          <li>
            <b>Con código:</b> el repo usa issues y pull requests comunes de GitHub. Abrí un{" "}
            <a href={`${REPO}/issues`} target="_blank" rel="noreferrer">issue</a> para proponer o reclamar
            algo, o mandá un PR directo — el CI corre los tests solo. Python (ingesta/API) y
            TypeScript/React (mapa).
          </li>
          <li>
            <b>Con datos:</b> ¿conocés una fuente pública que no estamos usando? ¿Un dataset oficial, un
            organismo que publica algo enterrado en PDFs? Abrí un issue con el link — convertir fuentes en
            capas es exactamente lo que este proyecto hace.
          </li>
          <li>
            <b>Sin código:</b> verificar que lo que muestra el mapa sea correcto, mejorar los textos,
            documentar limitaciones, difundir, usar el mapa para periodismo. Señalar un error nuestro vale
            tanto como una capa nueva: la credibilidad es el único capital de esta herramienta.
          </li>
          <li>
            <b>Con pedidos de acceso a la información</b> (ley 27.275): hay datos del Estado que existen y no
            se publican (traza balizada de la VNT, datos de Prefectura). Los pedidos formales son una forma de
            colaboración concreta.
          </li>
        </ul>
      </section>

      <section>
        <h3>Las reglas del juego (no negociables)</h3>
        <ul>
          <li><b>Gratuito para siempre, sin publicidad, sin cuentas.</b> Infraestructura de costo cero.</li>
          <li>
            <b>No pedimos plata.</b> Colaborar acá no cuesta dinero y no invitamos a nadie a gastarlo. Si
            alguien, por su propia voluntad, quiere bancar un servidor o el acceso a una base de datos paga,
            bienvenido sea — pero ese no es el objetivo ni lo vamos a pedir. Lo que buscamos son datos,
            tiempo y ojos.
          </li>
          <li>
            <b>Evidencia, no condena:</b> el mapa muestra actividad <i>aparente</i> con su nivel de confianza
            y su retraso declarado. Nunca acusamos; documentamos para que se pueda investigar.
          </li>
          <li>
            <b>Honestidad sobre los límites:</b> cada capa dice qué tan vieja es, qué cobertura tiene y qué
            no puede ver. No prometemos “tiempo real” donde no existe.
          </li>
          <li>
            <b>Todo abierto:</b> código MIT, datos con sus licencias de origen y atribución (GFW, OSM,
            Copernicus, EOG, IGN), pipelines visibles corriendo en público.
          </li>
        </ul>
      </section>

      <section>
        <h3>Por dónde empezar hoy</h3>
        <p>
          Entrá al <a href={REPO} target="_blank" rel="noreferrer">repositorio</a>, leé el{" "}
          <code>PLAN.md</code> (el estado real del proyecto, sin humo) y los issues abiertos. Si algo te
          indigna lo suficiente como para querer verlo en el mapa, ese es tu primer issue.
        </p>
      </section>
    </div>
  );
}
