"use client";

import * as React from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

/*
 * Jerarquía tipográfica del dialog (todo Inter, sin emojis ni iconos
 * decorativos, distinguido solo por peso, tamaño y color):
 *
 *   - DialogTitle        text-xl, font-semibold, foreground   (1)
 *   - DialogDescription  text-sm, normal,        muted        (2)
 *   - Section title      text-sm, font-medium,   foreground   (3)
 *   - Helper text        text-xs, normal,        muted        (4)
 *   - Section divider    border-t hairline                    (separador entre grupos)
 */

export interface AnalysisOptions {
  codigoCurso: string;
  dispatcher: "rule" | "rag";
  enriquecer: boolean;
  generarResumen: boolean;
}

export const DEFAULT_OPTIONS: AnalysisOptions = {
  codigoCurso: "",
  dispatcher: "rule",
  enriquecer: false,
  generarResumen: false,
};

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  initial: AnalysisOptions;
  onApply: (opts: AnalysisOptions) => void;
}

export function AttachOptionsDialog({ open, onOpenChange, initial, onApply }: Props) {
  const [opts, setOpts] = React.useState<AnalysisOptions>(initial);

  React.useEffect(() => {
    if (open) setOpts(initial);
  }, [open, initial]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Opciones del análisis</DialogTitle>
          <DialogDescription>
            Configura cómo UnibaBot procesará este PDA. Todo es opcional.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-7">
          {/* Sección 1: Código del curso */}
          <Section>
            <Label htmlFor="codigo">Código del curso</Label>
            <Input
              id="codigo"
              placeholder="ej: 22A14"
              value={opts.codigoCurso}
              onChange={(e) => setOpts({ ...opts, codigoCurso: e.target.value })}
            />
            <Helper>
              Activa las reglas específicas del curso. Si lo omites se evalúan solo
              las reglas generales.
            </Helper>
          </Section>

          {/* Sección 2: Dispatcher */}
          <Section>
            <SectionLabel>Arquitectura del dispatcher</SectionLabel>
            <div className="grid grid-cols-2 gap-2">
              <DispatcherOption
                value="rule"
                label="Rule-driven"
                hint="Cobertura 100%, reproducible"
                active={opts.dispatcher === "rule"}
                onSelect={() => setOpts({ ...opts, dispatcher: "rule" })}
              />
              <DispatcherOption
                value="rag"
                label="RAG semántico"
                hint="Top-k por similitud"
                active={opts.dispatcher === "rag"}
                onSelect={() => setOpts({ ...opts, dispatcher: "rag" })}
              />
            </div>
          </Section>

          {/* Sección 3: Enriquecimientos */}
          <div className="border-t border-border pt-6 space-y-5">
            <div>
              <SectionLabel>Enriquecimientos LLM</SectionLabel>
              <Helper className="mt-1">
                Pasos opcionales que añaden texto generado al reporte. Cada uno
                suma alrededor de 15 segundos.
              </Helper>
            </div>
            <ToggleRow
              label="Correcciones enriquecidas"
              hint="Texto prescriptivo para cada hallazgo NO CUMPLE"
              checked={opts.enriquecer}
              onChange={(v) => setOpts({ ...opts, enriquecer: v })}
            />
            <ToggleRow
              label="Resúmenes ejecutivo y didáctico"
              hint="Dos párrafos: oficina del programa y docente"
              checked={opts.generarResumen}
              onChange={(v) => setOpts({ ...opts, generarResumen: v })}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button
            onClick={() => {
              onApply(opts);
              onOpenChange(false);
            }}
          >
            Aplicar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* --- Helpers tipográficos internos --- */

function Section({ children }: { children: React.ReactNode }) {
  return <div className="space-y-2">{children}</div>;
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-sm font-medium text-foreground leading-none">{children}</div>
  );
}

function Helper({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <p className={cn("text-xs text-muted-foreground leading-relaxed", className)}>
      {children}
    </p>
  );
}

function DispatcherOption({
  value,
  label,
  hint,
  active,
  onSelect,
}: {
  value: "rule" | "rag";
  label: string;
  hint: string;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      data-value={value}
      className={cn(
        "flex flex-col items-start text-left rounded-md border p-3.5 transition-colors",
        active
          ? "border-foreground bg-paper-warm"
          : "border-border bg-background hover:bg-paper-warm",
      )}
    >
      <span className="text-sm font-medium text-foreground leading-none">{label}</span>
      <span className="text-xs text-muted-foreground mt-2 leading-relaxed">{hint}</span>
    </button>
  );
}

function ToggleRow({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0">
        <div className="text-sm font-medium text-foreground leading-tight">{label}</div>
        <div className="text-xs text-muted-foreground mt-1 leading-relaxed">{hint}</div>
      </div>
      <Switch checked={checked} onCheckedChange={onChange} className="mt-0.5 shrink-0" />
    </div>
  );
}
