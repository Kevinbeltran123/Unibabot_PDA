"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import type { ProgressEvent } from "@/lib/types";

/*
 * Indicador de "pensando" estilo Claude: una sola línea de texto que va
 * cambiando según la etapa activa, con un shimmer sutil aplicado por
 * gradiente animado sobre el color del texto. Sin barras de progreso ni
 * checklists verticales — solo el estado actual, dicho con calma.
 */

const ETAPAS: { key: string; label: string; doneEvent: string }[] = [
  { key: "parsing", label: "Leyendo el documento", doneEvent: "parsing_done" },
  { key: "structural", label: "Verificando la estructura", doneEvent: "structural_done" },
  { key: "extract", label: "Extrayendo declaraciones del PDA", doneEvent: "extract_done" },
  { key: "llm_prep", label: "Preparando la evaluación", doneEvent: "llm_prep_done" },
  { key: "section_eval", label: "Evaluando secciones una por una", doneEvent: "done" },
  { key: "enrichment", label: "Enriqueciendo las correcciones", doneEvent: "enrichment_done" },
  { key: "summary", label: "Redactando los resúmenes", doneEvent: "summary_done" },
];

interface Props {
  events: ProgressEvent[];
  status: "connecting" | "open" | "closed" | "error";
}

export function ProgressTimeline({ events, status }: Props) {
  // Determina la etapa activa actual. Si la última cosa que pasó fue un
  // *_start, esa es la activa. Si fue un *_done, la activa es la siguiente
  // que aún no haya empezado, o la misma si no hay siguiente.
  const { activeLabel, sectionDetail } = React.useMemo(() => {
    let activeKey: string | null = null;
    const reached = new Set<string>();
    let sectionDetail: string | null = null;

    for (const e of events) {
      for (const etapa of ETAPAS) {
        if (e.event === `${etapa.key}_start`) activeKey = etapa.key;
        if (e.event === etapa.doneEvent) {
          reached.add(etapa.key);
          if (activeKey === etapa.key) activeKey = null;
        }
      }
      if (e.event === "section_eval_start" || e.event === "section_eval_done") {
        const d = e.data as { index: number; total: number; name: string };
        sectionDetail = `${d.index} de ${d.total}: ${d.name}`;
      }
    }

    let label: string;
    if (activeKey) {
      const etapa = ETAPAS.find((e) => e.key === activeKey);
      label = etapa ? etapa.label : "Procesando";
    } else if (reached.size === 0) {
      label = "Iniciando";
    } else {
      // Si no hay etapa activa, mostrar la última completada como "todavía trabajando"
      label = "Procesando";
    }

    return { activeLabel: label, sectionDetail };
  }, [events]);

  if (status === "error") {
    return (
      <div className="border-l-2 border-destructive bg-destructive/5 px-3 py-2 text-xs text-destructive leading-relaxed">
        Conexión al servidor de eventos perdida. El análisis sigue corriendo en
        segundo plano. Recarga la página si quieres reconectar.
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <p
        className={cn(
          "text-base font-medium leading-snug",
          // Shimmer: gradient móvil sobre el texto.
          "bg-clip-text text-transparent",
          "[background-image:linear-gradient(90deg,hsl(var(--foreground)/0.45)_0%,hsl(var(--foreground)/0.95)_50%,hsl(var(--foreground)/0.45)_100%)]",
          "[background-size:200%_100%]",
          "animate-shimmer-text",
        )}
      >
        {activeLabel}…
      </p>
      {sectionDetail && (
        <p className="text-xs text-muted-foreground leading-relaxed truncate">
          {sectionDetail}
        </p>
      )}
    </div>
  );
}
