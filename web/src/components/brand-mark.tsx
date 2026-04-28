import * as React from "react";
import { cn } from "@/lib/utils";
import { Logo } from "./logo";

/*
 * Wordmark institucional. Reusa el escudo de Unibague (Logo) en todas las
 * variantes para garantizar consistencia visual de marca.
 *
 *  - default: escudo + nombre, alineado horizontal
 *  - mono: solo el escudo dentro de un cuadrado tinta (avatar de chat)
 *  - text: solo el wordmark sin escudo
 *  - hero: escudo grande para pantallas de bienvenida
 */

interface Props {
  variant?: "default" | "mono" | "text" | "hero";
  className?: string;
}

export function BrandMark({ variant = "default", className }: Props) {
  if (variant === "mono") {
    return (
      <span
        aria-hidden
        className={cn(
          "inline-flex h-8 w-8 items-center justify-center rounded-md",
          "bg-foreground p-1.5",
          className,
        )}
      >
        <Logo className="h-full w-full text-background" />
      </span>
    );
  }

  if (variant === "text") {
    return (
      <span
        className={cn(
          "text-base font-medium tracking-tight text-foreground",
          className,
        )}
      >
        UnibaBot
      </span>
    );
  }

  if (variant === "hero") {
    return (
      <Logo className={cn("h-16 w-16 text-foreground", className)} title="UnibaBot" />
    );
  }

  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <Logo className="h-7 w-7 text-foreground shrink-0" />
      <span className="flex flex-col leading-none">
        <span className="text-[0.95rem] font-medium tracking-tight">UnibaBot</span>
        <span className="text-[0.625rem] uppercase tracking-institutional text-muted-foreground mt-0.5">
          PDA
        </span>
      </span>
    </span>
  );
}
