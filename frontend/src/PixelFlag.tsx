import { useEffect, useRef } from "react";

/** Bandera argentina de 8 bits flameando: canvas chico (36×24 "píxeles")
 * con onda senoidal por columna, escalado con image-rendering: pixelated. */

const ANCHO = 36;
const ALTO = 24;
const CELESTE = "#75aadb";
const CELESTE_SOMBRA = "#5a8cbf";
const BLANCO = "#f4f7fb";
const BLANCO_SOMBRA = "#cfd9e6";
const SOL = "#f6b40e";
const SOL_SOMBRA = "#d9990a";

export default function PixelFlag({ escala = 3 }: { escala?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let vivo = true;
    let raf = 0;

    const dibujar = (t: number) => {
      if (!vivo) return;
      ctx.clearRect(0, 0, ANCHO, ALTO + 6);
      for (let x = 0; x < ANCHO; x++) {
        // onda: desplazamiento vertical por columna, amplitud creciente hacia la punta
        const fase = t / 220 - x * 0.38;
        const amp = 1 + (x / ANCHO) * 2.2;
        const dy = Math.round(Math.sin(fase) * amp);
        const sombra = Math.cos(fase) < -0.35; // "pliegue" de la tela
        for (let y = 0; y < ALTO; y++) {
          const franja = y < ALTO / 3 ? 0 : y < (2 * ALTO) / 3 ? 1 : 2;
          let color: string;
          if (franja === 1) {
            // franja blanca con sol de mayo (cuadrado 4×4 al centro)
            const enSol = x >= ANCHO / 2 - 2 && x < ANCHO / 2 + 2 && y >= ALTO / 2 - 2 && y < ALTO / 2 + 2;
            color = enSol ? (sombra ? SOL_SOMBRA : SOL) : sombra ? BLANCO_SOMBRA : BLANCO;
          } else {
            color = sombra ? CELESTE_SOMBRA : CELESTE;
          }
          ctx.fillStyle = color;
          ctx.fillRect(x, y + 3 + dy, 1, 1);
        }
      }
      raf = requestAnimationFrame(dibujar);
    };
    raf = requestAnimationFrame(dibujar);
    return () => {
      vivo = false;
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <canvas
      ref={ref}
      width={ANCHO}
      height={ALTO + 6}
      className="bandera-pixel"
      style={{ width: ANCHO * escala, height: (ALTO + 6) * escala }}
      aria-label="Bandera argentina (pixel art)"
    />
  );
}
