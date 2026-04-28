import * as React from "react";
import { cn } from "@/lib/utils";
import { AssistantAvatar, UserAvatar } from "./avatar";

/*
 * Patrón de chat con división izquierda/derecha:
 *
 *   AssistantMessage -> avatar a la IZQUIERDA, contenido fluyendo abierto
 *                       sin burbuja (estilo claude.ai). Útil para reportes,
 *                       timelines y respuestas largas.
 *
 *   UserMessage      -> avatar a la DERECHA, contenido envuelto en una
 *                       burbuja sutil (paper-warm) alineada a la derecha.
 *                       Útil para mensajes cortos del usuario (subir un
 *                       PDA con sus opciones).
 *
 * Ambos turnos quedan separados por una hairline horizontal arriba.
 */

interface BaseProps {
  children: React.ReactNode;
  className?: string;
  withDivider?: boolean;
}

interface AssistantProps extends BaseProps {
  speaker?: string;
}

interface UserProps extends BaseProps {
  email?: string | null;
}

export function AssistantMessage({
  children,
  className,
  withDivider = true,
  speaker = "UnibaBot",
}: AssistantProps) {
  return (
    <article
      className={cn(
        "py-7",
        withDivider && "border-t border-border first:border-t-0",
        className,
      )}
    >
      <div className="flex gap-4">
        <AssistantAvatar />
        <div className="flex-1 min-w-0 pt-0.5">
          <div className="text-[0.7rem] uppercase tracking-institutional text-muted-foreground mb-2">
            {speaker}
          </div>
          <div className="text-foreground leading-relaxed">{children}</div>
        </div>
      </div>
    </article>
  );
}

export function UserMessage({
  children,
  className,
  withDivider = true,
  email,
}: UserProps) {
  return (
    <article
      className={cn(
        "py-7",
        withDivider && "border-t border-border first:border-t-0",
        className,
      )}
    >
      <div className="flex flex-row-reverse gap-4 items-start">
        <UserAvatar email={email} />
        <div className="flex flex-col items-end gap-2 max-w-[78%] min-w-0">
          <div className="text-[0.7rem] uppercase tracking-institutional text-muted-foreground">
            Tú
          </div>
          <div
            className={cn(
              "rounded-lg border border-border bg-paper-warm/70",
              "px-4 py-3 text-foreground leading-relaxed text-left",
              "shadow-[0_1px_0_hsl(var(--border)/0.5)]",
            )}
          >
            {children}
          </div>
        </div>
      </div>
    </article>
  );
}
