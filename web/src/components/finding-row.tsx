"use client";

import * as React from "react";
import { ChevronDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Hallazgo } from "@/lib/types";

/*
 * Hallazgo en formato fila editorial. Inspirado en tablas de auditoria
 * regulatoria: indicador a la izquierda (barra vertical 2px), id en
 * mono, regla en sans, expand discreto a la derecha. NO es una card.
 */

export function FindingRow({ h }: { h: Hallazgo }) {
  const [open, setOpen] = React.useState(false);
  const ok = h.estado === "CUMPLE";

  return (
    <div
      className={cn(
        "group relative border-b border-border last:border-b-0 transition-colors",
        "hover:bg-paper-warm/60",
      )}
    >
      {/* Barra indicadora vertical */}
      <span
        aria-hidden
        className={cn(
          "absolute left-0 top-0 bottom-0 w-[2px]",
          ok ? "bg-success" : "bg-destructive",
        )}
      />

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left flex items-start gap-3 pl-4 pr-3 py-3.5 focus:outline-none focus-visible:bg-paper-tint"
      >
        <span className="mt-0.5 shrink-0 flex items-center gap-2 min-w-[6.5rem]">
          <span
            className={cn(
              "text-[0.625rem] font-medium uppercase tracking-institutional",
              ok ? "text-success" : "text-destructive",
            )}
          >
            {ok ? "Cumple" : "No cumple"}
          </span>
        </span>
        <span className="shrink-0 mt-0.5 font-mono text-[0.7rem] text-muted-foreground min-w-[5rem]">
          {h.regla_id}
        </span>
        <span className="flex-1 min-w-0 text-sm leading-snug text-foreground">
          {h.regla}
        </span>
        <ChevronDown
          className={cn(
            "h-3.5 w-3.5 mt-1 text-muted-foreground transition-transform shrink-0",
            open && "rotate-180",
          )}
        />
      </button>

      {open && (
        <div className="pl-[7rem] pr-6 pb-4 space-y-3 animate-fade-in">
          <Field label="Evidencia" body={h.evidencia} />
          {!ok && h.correccion_enriquecida && (
            <Field label="Corrección sugerida" body={h.correccion_enriquecida} highlight />
          )}
          {!ok && !h.correccion_enriquecida && h.correccion && (
            <Field label="Corrección sugerida" body={h.correccion} />
          )}
          {!h.evidencia && !h.correccion && (
            <p className="text-xs text-muted-foreground italic flex items-center gap-1.5">
              <Minus className="h-3 w-3" />
              Sin detalles adicionales
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function Field({ label, body, highlight }: { label: string; body: string; highlight?: boolean }) {
  return (
    <div>
      <div className="text-[0.625rem] uppercase tracking-institutional text-muted-foreground mb-1">
        {label}
      </div>
      <p
        className={cn(
          "text-sm leading-relaxed text-foreground/90 whitespace-pre-wrap",
          highlight && "border-l-2 border-gold pl-3",
        )}
      >
        {body}
      </p>
    </div>
  );
}
