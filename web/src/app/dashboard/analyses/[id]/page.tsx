"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, BookOpen, Briefcase, Download, FileText, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FindingCard } from "@/components/finding-card";
import { FindingsTable } from "@/components/findings-table";
import { useAnalysis } from "@/hooks/use-analyses";
import { api } from "@/lib/api-client";
import { formatDate, formatDuration } from "@/lib/utils";
import type { Hallazgo, ResultadoSeccion } from "@/lib/types";

export default function AnalysisDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;
  const { data, isLoading } = useAnalysis(id, { refetchInterval: false });

  React.useEffect(() => {
    if (!data) return;
    if (data.status !== "done") {
      router.replace(`/dashboard/analyses/${id}/processing`);
    }
  }, [data, id, router]);

  if (isLoading || !data || !data.report) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const report = data.report;
  const allHallazgos: Hallazgo[] = report.resultados.flatMap((r) => r.hallazgos || []);
  const cumple = allHallazgos.filter((h) => h.estado === "CUMPLE").length;
  const noCumple = allHallazgos.filter((h) => h.estado === "NO CUMPLE").length;

  const estructurales = report.resultados.find((r) => r.seccion === "__estructural_global__");
  const declaraciones = report.resultados.find((r) => r.seccion === "__declaraciones_global__");
  const ausentes = report.resultados.find((r) => r.seccion === "__seccion_ausente_global__");
  const porSeccion = report.resultados.filter((r) => !r.seccion.startsWith("__"));

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-3">
        <Button variant="ghost" size="icon" onClick={() => router.push("/dashboard")} aria-label="Volver">
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <FileText className="h-3.5 w-3.5" />
            <span className="truncate">{data.filename}</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Reporte de cumplimiento</h1>
          <div className="flex flex-wrap items-center gap-2 mt-1 text-xs text-muted-foreground">
            <span>{formatDate(data.created_at)}</span>
            <span>·</span>
            <span>{formatDuration(data.duration_s)}</span>
            <span>·</span>
            <span className="font-mono">{report.modelo}</span>
            {report.codigo_curso && <Badge variant="outline">{report.codigo_curso}</Badge>}
            <Badge variant="outline">{report.dispatcher}</Badge>
          </div>
        </div>
        <a href={api.downloadUrl(id)} download>
          <Button variant="outline" className="gap-2">
            <Download className="h-4 w-4" />
            JSON
          </Button>
        </a>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Total hallazgos" value={allHallazgos.length} />
        <StatCard label="Cumple" value={cumple} tone="success" />
        <StatCard label="No cumple" value={noCumple} tone="destructive" />
        <StatCard label="Secciones evaluadas" value={report.total_secciones} />
      </div>

      {report.resumenes && (
        <div className="grid gap-3 md:grid-cols-2">
          <Card className="border-primary/20">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Briefcase className="h-4 w-4 text-primary" />
                Resumen para la oficina
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm leading-relaxed whitespace-pre-wrap text-muted-foreground">
              {report.resumenes.oficina}
            </CardContent>
          </Card>
          <Card className="border-primary/20">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-primary" />
                Resumen para el docente
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm leading-relaxed whitespace-pre-wrap text-muted-foreground">
              {report.resumenes.docente}
            </CardContent>
          </Card>
        </div>
      )}

      <Tabs defaultValue="por-seccion">
        <TabsList>
          <TabsTrigger value="estructural">Estructural</TabsTrigger>
          <TabsTrigger value="por-seccion">Por seccion</TabsTrigger>
          <TabsTrigger value="tabla">Tabla</TabsTrigger>
        </TabsList>

        <TabsContent value="estructural" className="space-y-3">
          {estructurales?.hallazgos.length ? (
            estructurales.hallazgos.map((h, i) => <FindingCard key={`${h.regla_id}-${i}`} h={h} />)
          ) : (
            <EmptyState text="No hay hallazgos estructurales." />
          )}
        </TabsContent>

        <TabsContent value="por-seccion" className="space-y-6">
          {declaraciones && declaraciones.hallazgos.length > 0 && (
            <SectionGroup title="Declaraciones canonicas (extractor)" resultado={declaraciones} />
          )}
          {ausentes && ausentes.hallazgos.length > 0 && (
            <SectionGroup title="Secciones ausentes" resultado={ausentes} />
          )}
          {porSeccion.length === 0 && declaraciones === undefined && (
            <EmptyState text="No hay secciones evaluadas via LLM en este reporte." />
          )}
          {porSeccion.map((r) => (
            <SectionGroup key={r.seccion} title={r.seccion} resultado={r} />
          ))}
        </TabsContent>

        <TabsContent value="tabla">
          <FindingsTable resultados={report.resultados} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function StatCard({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: number;
  tone?: "default" | "success" | "destructive";
}) {
  const colors = {
    default: "text-foreground",
    success: "text-success",
    destructive: "text-destructive",
  };
  return (
    <Card>
      <CardContent className="p-4">
        <div className={`text-2xl font-bold ${colors[tone]}`}>{value}</div>
        <div className="text-xs text-muted-foreground mt-1">{label}</div>
      </CardContent>
    </Card>
  );
}

function SectionGroup({ title, resultado }: { title: string; resultado: ResultadoSeccion }) {
  const cumple = resultado.hallazgos.filter((h) => h.estado === "CUMPLE").length;
  const noCumple = resultado.hallazgos.filter((h) => h.estado === "NO CUMPLE").length;
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">{title}</h3>
        <div className="flex items-center gap-1.5 text-xs">
          <Badge variant="success">{cumple} cumple</Badge>
          <Badge variant="destructive">{noCumple} no cumple</Badge>
        </div>
      </div>
      <div className="space-y-2">
        {resultado.hallazgos.map((h, i) => (
          <FindingCard key={`${h.regla_id}-${i}`} h={h} />
        ))}
      </div>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <Card>
      <CardContent className="p-8 text-center text-sm text-muted-foreground">{text}</CardContent>
    </Card>
  );
}
