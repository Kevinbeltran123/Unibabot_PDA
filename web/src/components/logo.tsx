import * as React from "react";
import { cn } from "@/lib/utils";

/*
 * Escudo institucional de la Universidad de Ibagué. Triángulo con la
 * silueta humana en negativo (cabeza circular + cuerpo en forma de
 * campana). Implementado con un solo path + fill-rule="evenodd" para
 * que los recortes sean huecos reales y dejen ver el fondo del padre.
 *
 * Funciona en cualquier color de fondo: usa currentColor para el
 * trazo, los huecos siempre revelan el fondo natural del contenedor.
 *
 * Proporciones ajustadas para que la cabeza y el cuerpo ocupen una
 * proporción visualmente fiel al logo original (cabeza ~24% del ancho,
 * cuerpo se extiende casi hasta las esquinas inferiores del triángulo).
 */

interface Props {
  className?: string;
  title?: string;
}

const SHIELD_PATH = `
  M 100 8
  L 190 168
  Q 194 178 184 178
  L 16 178
  Q 6 178 10 168
  Z
  M 100 22
  a 22 22 0 1 0 0.01 0
  Z
  M 68 78
  Q 60 78 60 86
  L 32 158
  Q 30 168 40 168
  L 160 168
  Q 170 168 168 158
  L 140 86
  Q 140 78 132 78
  Z
`;

const INNER_FIGURE_PATH = `
  M 86 96
  Q 80 96 80 102
  L 64 156
  Q 63 162 69 162
  L 131 162
  Q 137 162 136 156
  L 120 102
  Q 120 96 114 96
  Z
`;

export function Logo({ className, title }: Props) {
  return (
    <svg
      viewBox="0 0 200 184"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("text-foreground", className)}
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
      fill="currentColor"
    >
      <path fillRule="evenodd" clipRule="evenodd" d={SHIELD_PATH} />
      <path d={INNER_FIGURE_PATH} />
    </svg>
  );
}
