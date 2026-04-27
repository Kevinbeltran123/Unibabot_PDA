"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { UploadDropzone } from "@/components/upload-dropzone";
import { useCreateAnalysis } from "@/hooks/use-analyses";
import { toast } from "@/hooks/use-toast";
import { ApiError } from "@/lib/api-client";

export default function NewAnalysisPage() {
  const router = useRouter();
  const create = useCreateAnalysis();

  const [file, setFile] = React.useState<File | null>(null);
  const [codigoCurso, setCodigoCurso] = React.useState("");
  const [dispatcher, setDispatcher] = React.useState<"rule" | "rag">("rule");
  const [enriquecer, setEnriquecer] = React.useState(false);
  const [generarResumen, setGenerarResumen] = React.useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      toast({ title: "Sube un PDF antes de analizar", variant: "destructive" });
      return;
    }
    const form = new FormData();
    form.append("file", file);
    form.append("modelo", "qwen2.5:14b");
    form.append("dispatcher", dispatcher);
    form.append("top_k", "5");
    form.append("enriquecer", String(enriquecer));
    form.append("generar_resumen", String(generarResumen));
    if (codigoCurso.trim()) form.append("codigo_curso", codigoCurso.trim());

    try {
      const r = await create.mutateAsync(form);
      router.push(`/dashboard/analyses/${r.id}/processing`);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Error inesperado";
      toast({ title: "No se pudo iniciar el analisis", description: msg, variant: "destructive" });
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Analizar nuevo PDA</h1>
        <p className="text-sm text-muted-foreground">Sube el PDF y configura el analisis</p>
      </div>

      <form onSubmit={onSubmit} className="space-y-6">
        <UploadDropzone onFileSelected={setFile} selectedFile={file} />

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Configuracion</CardTitle>
            <CardDescription>El codigo del curso activa reglas de dimension especifica</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="codigo">Codigo del curso (opcional)</Label>
              <Input
                id="codigo"
                placeholder="ej: 22A14"
                value={codigoCurso}
                onChange={(e) => setCodigoCurso(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>Arquitectura del dispatcher</Label>
              <div className="grid grid-cols-2 gap-2">
                {(
                  [
                    { v: "rule", label: "Rule-driven", hint: "Cobertura 100%, reproducible" },
                    { v: "rag", label: "RAG semantico", hint: "Top-k por similitud" },
                  ] as const
                ).map((opt) => (
                  <button
                    type="button"
                    key={opt.v}
                    onClick={() => setDispatcher(opt.v)}
                    className={`rounded-lg border p-3 text-left transition-colors ${
                      dispatcher === opt.v ? "border-primary bg-primary/5" : "hover:bg-accent"
                    }`}
                  >
                    <div className="text-sm font-medium">{opt.label}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{opt.hint}</div>
                  </button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              Enriquecimientos LLM
            </CardTitle>
            <CardDescription>Cacheado: la segunda corrida del mismo PDA es instantanea</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ToggleRow
              label="Correcciones enriquecidas"
              hint="Texto prescriptivo para cada NO CUMPLE (+15s primera vez)"
              checked={enriquecer}
              onChange={setEnriquecer}
            />
            <ToggleRow
              label="Resumenes ejecutivo y didactico"
              hint="Dos parrafos: uno para la oficina, otro para el docente (+15s)"
              checked={generarResumen}
              onChange={setGenerarResumen}
            />
          </CardContent>
        </Card>

        <div className="flex items-center justify-end gap-3">
          <Button type="button" variant="ghost" onClick={() => router.back()}>
            Cancelar
          </Button>
          <Button type="submit" disabled={create.isPending || !file} className="gap-2">
            {create.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Iniciar analisis
          </Button>
        </div>
      </form>
    </div>
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
    <div className="flex items-start justify-between gap-4 py-1">
      <div>
        <div className="text-sm font-medium">{label}</div>
        <div className="text-xs text-muted-foreground mt-0.5">{hint}</div>
      </div>
      <Switch checked={checked} onCheckedChange={onChange} />
    </div>
  );
}
