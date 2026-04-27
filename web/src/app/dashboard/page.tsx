"use client";

import Link from "next/link";
import { CheckCircle2, Clock, FileText, Loader2, Plus, Trash2, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAnalyses, useDeleteAnalysis } from "@/hooks/use-analyses";
import { toast } from "@/hooks/use-toast";
import { formatDuration, relativeTime } from "@/lib/utils";
import type { AnalysisStatus } from "@/lib/types";

const STATUS_LABEL: Record<AnalysisStatus, string> = {
  pending: "En cola",
  running: "Procesando",
  done: "Completado",
  failed: "Fallido",
};

function StatusBadge({ status }: { status: AnalysisStatus }) {
  const variant =
    status === "done" ? "success" : status === "failed" ? "destructive" : status === "running" ? "default" : "secondary";
  const Icon =
    status === "done" ? CheckCircle2 : status === "failed" ? XCircle : status === "running" ? Loader2 : Clock;
  return (
    <Badge variant={variant} className="gap-1">
      <Icon className={`h-3 w-3 ${status === "running" ? "animate-spin" : ""}`} />
      {STATUS_LABEL[status]}
    </Badge>
  );
}

export default function DashboardPage() {
  const { data, isLoading, error } = useAnalyses();
  const del = useDeleteAnalysis();

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6 text-destructive text-sm">No se pudo cargar la lista de analisis.</CardContent>
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 mb-4">
          <FileText className="h-8 w-8 text-primary" />
        </div>
        <h2 className="text-xl font-semibold mb-1">Aun no has analizado ningun PDA</h2>
        <p className="text-sm text-muted-foreground max-w-sm mb-6">
          Sube un Plan de Desarrollo Academico en PDF y obten en segundos un reporte de cumplimiento estructurado.
        </p>
        <Link href="/dashboard/new">
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            Analizar mi primer PDA
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Mis analisis</h1>
          <p className="text-sm text-muted-foreground">{data.length} reporte(s) generado(s)</p>
        </div>
        <Link href="/dashboard/new">
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            Nuevo
          </Button>
        </Link>
      </div>

      <div className="grid gap-3">
        {data.map((a) => (
          <Card key={a.id} className="transition-shadow hover:shadow-md">
            <CardContent className="p-5">
              <div className="flex items-start justify-between gap-4">
                <Link
                  href={a.status === "done" ? `/dashboard/analyses/${a.id}` : `/dashboard/analyses/${a.id}/processing`}
                  className="flex-1 min-w-0"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                    <span className="font-medium truncate">{a.filename}</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <StatusBadge status={a.status} />
                    {a.codigo_curso && <span className="font-mono">{a.codigo_curso}</span>}
                    <span>·</span>
                    <span>{relativeTime(a.created_at)}</span>
                    {a.duration_s != null && (
                      <>
                        <span>·</span>
                        <span>{formatDuration(a.duration_s)}</span>
                      </>
                    )}
                    {a.enriquecer && <Badge variant="outline">enriquecido</Badge>}
                    {a.generar_resumen && <Badge variant="outline">con resumenes</Badge>}
                  </div>
                  {a.error && <p className="mt-2 text-xs text-destructive truncate">{a.error}</p>}
                </Link>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Borrar"
                  onClick={async (e) => {
                    e.preventDefault();
                    if (!confirm(`Borrar analisis de ${a.filename}?`)) return;
                    try {
                      await del.mutateAsync(a.id);
                      toast({ title: "Analisis borrado" });
                    } catch {
                      toast({ title: "No se pudo borrar", variant: "destructive" });
                    }
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
