"use client";

import * as React from "react";
import { Check, Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import type { ProgressEvent } from "@/lib/types";

const ETAPAS: { key: string; label: string; doneEvent: string }[] = [
  { key: "parsing", label: "Parseando PDF", doneEvent: "parsing_done" },
  { key: "structural", label: "Reglas estructurales", doneEvent: "structural_done" },
  { key: "extract", label: "Extraccion LLM", doneEvent: "extract_done" },
  { key: "llm_prep", label: "Preparando evaluacion", doneEvent: "llm_prep_done" },
  { key: "section_eval", label: "Evaluando secciones", doneEvent: "done" },
  { key: "enrichment", label: "Enriqueciendo correcciones (opt)", doneEvent: "enrichment_done" },
  { key: "summary", label: "Generando resumenes (opt)", doneEvent: "summary_done" },
];

interface Props {
  events: ProgressEvent[];
  status: "connecting" | "open" | "closed" | "error";
}

export function ProgressTimeline({ events, status }: Props) {
  const reachedKeys = new Set<string>();
  let activeKey: string | null = null;
  let sectionProgress: { idx: number; total: number; name: string } | null = null;

  for (const e of events) {
    for (const etapa of ETAPAS) {
      if (e.event === `${etapa.key}_start`) {
        activeKey = etapa.key;
      }
      if (e.event === etapa.doneEvent) {
        reachedKeys.add(etapa.key);
        if (activeKey === etapa.key) activeKey = null;
      }
    }
    if (e.event === "section_eval_start" || e.event === "section_eval_done") {
      const d = e.data as { index: number; total: number; name: string };
      sectionProgress = { idx: d.index, total: d.total, name: d.name };
    }
  }

  const visibleEtapas = ETAPAS.filter((e) => {
    if (e.key === "enrichment" || e.key === "summary") {
      return events.some((ev) => ev.event === `${e.key}_start`);
    }
    return true;
  });

  const completedCount = visibleEtapas.filter((e) => reachedKeys.has(e.key)).length;
  const overallPct = (completedCount / visibleEtapas.length) * 100;

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="font-medium">Progreso global</span>
          <span className="text-muted-foreground">
            {completedCount} / {visibleEtapas.length}
          </span>
        </div>
        <Progress value={overallPct} />
      </div>

      <ul className="space-y-2.5">
        {visibleEtapas.map((etapa) => {
          const done = reachedKeys.has(etapa.key);
          const active = activeKey === etapa.key;
          return (
            <li
              key={etapa.key}
              className={cn(
                "flex items-center gap-3 rounded-lg border px-4 py-3 transition-colors",
                done && "bg-success/5 border-success/20",
                active && "bg-primary/5 border-primary/30",
                !done && !active && "bg-muted/30 border-border/50 text-muted-foreground",
              )}
            >
              <div className="shrink-0">
                {done ? (
                  <Check className="h-4 w-4 text-success" />
                ) : active ? (
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                ) : (
                  <div className="h-4 w-4 rounded-full border-2 border-muted-foreground/30" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium">{etapa.label}</div>
                {active && etapa.key === "section_eval" && sectionProgress && (
                  <div className="text-xs text-muted-foreground mt-0.5 truncate">
                    {sectionProgress.idx} / {sectionProgress.total}: {sectionProgress.name}
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ul>

      {status === "error" && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
          Conexion al servidor de eventos perdida. Recarga la pagina para reintentar.
        </div>
      )}
    </div>
  );
}
