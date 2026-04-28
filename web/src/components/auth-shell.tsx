import * as React from "react";
import Link from "next/link";
import { ThemeToggle } from "./theme-toggle";
import { AnimatedHeadline } from "./animated-headline";

/*
 * Layout split de auth: panel izquierdo navy ~64% del viewport con la
 * marca como protagonista centrada y un subtítulo descriptivo debajo;
 * panel derecho ~36% con el formulario encuadrado en un card.
 *
 * Jerarquía visual y de animación:
 *   1. "UnibaBot PDA" (grande, centrado) -> letras saltan, lentas y apreciables
 *      t=200ms inicio, perChar=70ms, duration=900ms
 *   2. Subtítulo descriptivo (más pequeño) -> letras saltan suaves
 *      arranca cuando UnibaBot PDA está casi completo
 *      t=1700ms inicio, perChar=42ms, duration=820ms
 *   3. Form card -> sin animación, usable desde el primer frame
 */

interface Props {
  children: React.ReactNode;
}

export function AuthShell({ children }: Props) {
  return (
    <div className="min-h-screen flex">
      {/* Panel izquierdo: marca centrada como protagonista */}
      <aside className="hidden lg:flex lg:w-[62%] xl:w-[64%] flex-col bg-foreground text-background relative overflow-hidden">
        {/* Patrón sutil de puntos para textura */}
        <div
          aria-hidden
          className="absolute inset-0 opacity-[0.06]"
          style={{
            backgroundImage:
              "radial-gradient(hsl(var(--background)) 1px, transparent 1px)",
            backgroundSize: "20px 20px",
          }}
        />

        {/* Centro perfecto: marca grande + subtítulo */}
        <div className="relative flex flex-col h-full items-center justify-center px-12 xl:px-20 text-center">
          <AnimatedHeadline
            as="h1"
            variant="bounce"
            text="UnibaBot PDA"
            className="text-[5rem] xl:text-[6.5rem] font-medium leading-none tracking-tight"
            delayStart={200}
            stagger={70}
            duration={900}
          />
          <div className="mt-8 max-w-[560px] xl:max-w-[640px]">
            <AnimatedHeadline
              as="p"
              variant="smooth"
              text="Verificación automática de Planes de Desarrollo Académico."
              className="text-[1.125rem] xl:text-[1.25rem] leading-snug text-background/75 font-normal"
              delayStart={1900}
              stagger={140}
              duration={1400}
            />
          </div>
        </div>
      </aside>

      {/* Panel derecho: form encuadrado */}
      <main className="flex-1 lg:w-[38%] xl:w-[36%] flex flex-col bg-paper-warm/40">
        <div className="flex items-center justify-between px-6 py-4 lg:px-8">
          <Link href="/" className="lg:hidden text-sm font-medium tracking-tight">
            UnibaBot PDA
          </Link>
          <span className="hidden lg:block" />
          <ThemeToggle />
        </div>

        <div className="flex-1 flex items-center justify-center px-6 pb-12 lg:px-8">
          <div className="w-full max-w-[420px]">
            <div className="rounded-lg border border-border bg-background p-8 lg:p-10 shadow-[0_1px_0_hsl(var(--border)),0_24px_60px_-30px_hsl(var(--foreground)/0.18)]">
              {children}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
