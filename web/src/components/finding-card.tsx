"use client";

import * as React from "react";
import { CheckCircle2, ChevronDown, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Hallazgo } from "@/lib/types";

export function FindingCard({ h }: { h: Hallazgo }) {
  const [open, setOpen] = React.useState(false);
  const ok = h.estado === "CUMPLE";
  return (
    <div
      className={cn(
        "rounded-lg border bg-card p-4 transition-shadow hover:shadow-sm",
        ok ? "border-success/30" : "border-destructive/30",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          {ok ? (
            <CheckCircle2 className="h-5 w-5 text-success shrink-0 mt-0.5" />
          ) : (
            <XCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
          )}
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={ok ? "success" : "destructive"}>{h.estado}</Badge>
              <code className="text-xs font-mono text-muted-foreground">{h.regla_id}</code>
            </div>
            <div className="mt-2 text-sm font-medium leading-snug">{h.regla}</div>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-label={open ? "Ocultar detalles" : "Ver detalles"}
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />
        </button>
      </div>
      {open && (
        <div className="mt-4 space-y-3 pl-8 animate-fade-in">
          <Section label="Evidencia" body={h.evidencia} />
          {!ok && h.correccion_enriquecida && (
            <Section label="Correccion sugerida" body={h.correccion_enriquecida} highlight />
          )}
          {!ok && !h.correccion_enriquecida && h.correccion && (
            <Section label="Correccion sugerida" body={h.correccion} />
          )}
        </div>
      )}
    </div>
  );
}

function Section({ label, body, highlight }: { label: string; body: string; highlight?: boolean }) {
  return (
    <div>
      <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">{label}</div>
      <p
        className={cn(
          "text-sm leading-relaxed whitespace-pre-wrap",
          highlight && "rounded-md bg-primary/[0.04] border border-primary/10 px-3 py-2",
        )}
      >
        {body}
      </p>
    </div>
  );
}
