"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/*
 * Texto animado al montarse. Dos variantes:
 *
 *   variant="bounce"  -> divide por LETRAS, easing back-out (cubic-bezier
 *                        0.34, 1.56, 0.64, 1). Cada letra "salta" a su
 *                        lugar con un overshoot sutil. Apropiado para
 *                        titulos de marca y headlines protagonistas.
 *
 *   variant="smooth"  -> divide por PALABRAS, easing expo-out (cubic-bezier
 *                        0.16, 1, 0.3, 1). Cada palabra emerge con un fade
 *                        + ligera elevacion + leve blur que se difumina.
 *                        Sin rebote. Editorial, elegante, calmado.
 *                        Apropiado para subtitulos, parrafos descriptivos
 *                        y cualquier texto que no sea el foco principal.
 */

type Variant = "bounce" | "smooth";

interface Props {
  text: string;
  className?: string;
  as?: "h1" | "h2" | "h3" | "p" | "span";
  variant?: Variant;
  delayStart?: number; // ms antes de la primera unidad
  stagger?: number;    // ms entre unidades (letras o palabras)
  duration?: number;   // ms de cada unidad
}

export function AnimatedHeadline({
  text,
  className,
  as: Tag = "h2",
  variant = "bounce",
  delayStart,
  stagger,
  duration,
}: Props) {
  const isBounce = variant === "bounce";

  const cfg = {
    delayStart: delayStart ?? (isBounce ? 200 : 1700),
    stagger: stagger ?? (isBounce ? 70 : 110),
    duration: duration ?? (isBounce ? 900 : 1100),
    keyframe: isBounce ? "letter-rise" : "word-veil",
    easing: isBounce
      ? "cubic-bezier(0.34, 1.56, 0.64, 1)" // back-out, overshoot sutil
      : "cubic-bezier(0.16, 1, 0.3, 1)",     // expo-out, sin rebote
  };

  const words = React.useMemo(() => text.split(" "), [text]);

  // BOUNCE: anima letra por letra, palabras no rompibles
  if (isBounce) {
    let charIndex = 0;
    return (
      <Tag className={cn(className)}>
        {words.map((word, wIdx) => {
          const wordSpan = (
            <span key={`w-${wIdx}`} className="inline-block whitespace-nowrap">
              {word.split("").map((char) => {
                const i = charIndex++;
                return (
                  <span
                    key={`c-${i}`}
                    className="inline-block opacity-0 will-change-transform"
                    style={{
                      animation: `${cfg.keyframe} ${cfg.duration}ms ${cfg.easing} both`,
                      animationDelay: `${cfg.delayStart + i * cfg.stagger}ms`,
                    }}
                  >
                    {char}
                  </span>
                );
              })}
            </span>
          );
          return (
            <React.Fragment key={`f-${wIdx}`}>
              {wordSpan}
              {wIdx < words.length - 1 && " "}
            </React.Fragment>
          );
        })}
      </Tag>
    );
  }

  // SMOOTH: anima palabra por palabra, fade + blur + ligera elevacion
  return (
    <Tag className={cn(className)}>
      {words.map((word, wIdx) => (
        <React.Fragment key={`w-${wIdx}`}>
          <span
            className="inline-block opacity-0 will-change-transform"
            style={{
              animation: `${cfg.keyframe} ${cfg.duration}ms ${cfg.easing} both`,
              animationDelay: `${cfg.delayStart + wIdx * cfg.stagger}ms`,
            }}
          >
            {word}
          </span>
          {wIdx < words.length - 1 && " "}
        </React.Fragment>
      ))}
    </Tag>
  );
}
