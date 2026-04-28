"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import {
  BookOpen,
  Briefcase,
  Download,
  FileText,
  Loader2,
  Trash2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AssistantMessage, UserMessage } from "@/components/chat-message";
import { FindingRow } from "@/components/finding-row";
import { FindingsTable } from "@/components/findings-table";
import { useAnalysis, useDeleteAnalysis } from "@/hooks/use-analyses";
import { useAuth } from "@/hooks/use-auth";
import { toast } from "@/hooks/use-toast";
import { useConfirm } from "@/components/ui/confirm-dialog";
import { api } from "@/lib/api-client";
import { cn, formatDate, formatDuration } from "@/lib/utils";
import type { Hallazgo, ResultadoSeccion } from "@/lib/types";

/*
 * Pagina de detalle como turno de conversacion:
 *  1) UserMessage: el "envio" del PDA con sus parametros
 *  2) AssistantMessage: el reporte completo embebido (header con stats,
 *     resumenes opcionales y tabs estructural / por seccion / tabla)
 */

export default function AnalysisDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;
  const { user } = useAuth();
  const { data, isLoading } = useAnalysis(id, { refetchInterval: false });
  const del = useDeleteAnalysis();
  const confirm = useConfirm();

  React.useEffect(() => {
    if (!data) return;
    if (data.status !== "done") {
      router.replace(`/dashboard/analyses/${id}/processing`);
    }
  }, [data, id, router]);

  if (isLoading || !data || !data.report) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
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

  async function onDelete() {
    const ok = await confirm({
      title: "¿Eliminar este análisis?",
      description: (
        <>
          Vas a eliminar el reporte de{" "}
          <span className="font-medium text-foreground">{data!.filename}</span>.
          Esta acción no se puede deshacer.
        </>
      ),
      confirmText: "Eliminar",
      cancelText: "Mantener",
      variant: "destructive",
    });
    if (!ok) return;
    try {
      await del.mutateAsync(id);
      toast({
        title: "Análisis eliminado",
        description: "El reporte y sus archivos asociados se borraron del servidor.",
        variant: "success",
      });
      router.push("/dashboard");
    } catch {
      toast({
        title: "No se pudo eliminar",
        description: "Ocurrió un error al borrar el análisis. Intenta de nuevo.",
        variant: "destructive",
      });
    }
  }

  return (
    <div className="mx-auto w-full max-w-[820px] px-6 py-8">
      <ConversationHeader
        filename={data.filename}
        completedAt={data.completed_at}
        duration={data.duration_s}
        onDelete={onDelete}
      />

      <UserMessage email={user?.email}>
        <UserPDARequest filename={data.filename} />
      </UserMessage>

      <AssistantMessage>
        <div className="space-y-8">
          {/* Resumen one-liner */}
          <p className="text-base text-foreground/85 leading-relaxed max-w-prose">
            Terminé de revisar <span className="font-medium text-foreground">{data.filename}</span>.
            Encontré <span className="font-medium tabular text-foreground">{allHallazgos.length}</span> hallazgos
            en <span className="font-medium tabular text-foreground">{report.total_secciones}</span> secciones evaluadas.
            {noCumple === 0 ? (
              <> Todos cumplen.</>
            ) : (
              <>
                {" "}
                <span className="text-destructive font-medium tabular">{noCumple}</span> de
                ellos requieren corrección.
              </>
            )}
          </p>

          {/* Stats grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-border border border-border">
            <Stat label="Total hallazgos" value={allHallazgos.length} />
            <Stat label="Cumple" value={cumple} tone="success" />
            <Stat label="No cumple" value={noCumple} tone="destructive" />
            <Stat label="Secciones" value={report.total_secciones} />
          </div>

          {/* Resumenes opcionales */}
          {report.resumenes && (
            <div className="grid gap-3 md:grid-cols-2">
              <SummaryPanel
                icon={<Briefcase className="h-3.5 w-3.5" />}
                label="Para la oficina"
                body={report.resumenes.oficina}
              />
              <SummaryPanel
                icon={<BookOpen className="h-3.5 w-3.5" />}
                label="Para el docente"
                body={report.resumenes.docente}
              />
            </div>
          )}

          {/* Tabs con desglose */}
          <Tabs defaultValue="por-seccion">
            <div className="flex items-end justify-between gap-3">
              <TabsList>
                <TabsTrigger value="estructural">Estructural</TabsTrigger>
                <TabsTrigger value="por-seccion">Por sección</TabsTrigger>
                <TabsTrigger value="tabla">Tabla</TabsTrigger>
              </TabsList>
              <a href={api.downloadUrl(id)} download className="pb-2">
                <Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground hover:text-foreground">
                  <Download className="h-3.5 w-3.5" />
                  Descargar JSON
                </Button>
              </a>
            </div>

            <TabsContent value="estructural">
              {estructurales && estructurales.hallazgos.length > 0 ? (
                <FindingGroup hallazgos={estructurales.hallazgos} />
              ) : (
                <EmptyHint text="No hay hallazgos estructurales." />
              )}
            </TabsContent>

            <TabsContent value="por-seccion" className="space-y-8">
              {declaraciones && declaraciones.hallazgos.length > 0 && (
                <SectionGroup title="Declaraciones canónicas" subtitle="Verificadas por extractor + matcher" resultado={declaraciones} />
              )}
              {ausentes && ausentes.hallazgos.length > 0 && (
                <SectionGroup title="Secciones ausentes" subtitle="No encontradas en el PDA" resultado={ausentes} />
              )}
              {porSeccion.length === 0 && declaraciones === undefined && (
                <EmptyHint text="No hay secciones evaluadas vía LLM en este reporte." />
              )}
              {porSeccion.map((r) => (
                <SectionGroup key={r.seccion} title={prettifySectionName(r.seccion)} resultado={r} />
              ))}
            </TabsContent>

            <TabsContent value="tabla">
              <FindingsTable resultados={report.resultados} />
            </TabsContent>
          </Tabs>
        </div>
      </AssistantMessage>
    </div>
  );
}

function ConversationHeader({
  filename,
  completedAt,
  duration,
  onDelete,
}: {
  filename: string;
  completedAt: string | null;
  duration: number | null;
  onDelete: () => void;
}) {
  return (
    <div className="pb-3 flex items-start justify-between gap-3">
      <div className="min-w-0">
        <div className="text-[0.7rem] uppercase tracking-institutional text-muted-foreground">
          Reporte de cumplimiento
        </div>
        <h2 className="mt-1.5 text-xl font-medium tracking-tight text-foreground leading-tight truncate">
          {filename}
        </h2>
        <div className="mt-1.5 text-xs text-muted-foreground tabular">
          {completedAt && formatDate(completedAt)}
          {duration != null && <span className="ml-2">&middot; {formatDuration(duration)}</span>}
        </div>
      </div>
      <Button
        variant="ghost"
        size="icon"
        aria-label="Borrar análisis"
        onClick={onDelete}
        className="h-8 w-8 text-muted-foreground hover:text-destructive"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}

function UserPDARequest({ filename }: { filename: string }) {
  return (
    <div className="inline-flex items-center gap-2">
      <FileText className="h-4 w-4 text-muted-foreground shrink-0" strokeWidth={1.75} />
      <span className="text-sm text-foreground truncate max-w-[320px]">{filename}</span>
    </div>
  );
}

function Stat({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: number;
  tone?: "default" | "success" | "destructive";
}) {
  const color =
    tone === "success" ? "text-success" : tone === "destructive" ? "text-destructive" : "text-foreground";
  return (
    <div className="bg-card p-4">
      <div className={cn("text-3xl font-medium tracking-tight leading-none tabular", color)}>{value}</div>
      <div className="mt-2 text-[0.65rem] uppercase tracking-institutional text-muted-foreground">
        {label}
      </div>
    </div>
  );
}

function SummaryPanel({
  icon,
  label,
  body,
}: {
  icon: React.ReactNode;
  label: string;
  body: string;
}) {
  return (
    <div className="border border-border rounded-md p-4 bg-paper-warm/40">
      <div className="flex items-center gap-1.5 text-[0.65rem] uppercase tracking-institutional text-muted-foreground mb-2">
        {icon}
        {label}
      </div>
      <p className="text-sm leading-relaxed text-foreground/90 whitespace-pre-wrap">{body}</p>
    </div>
  );
}

function FindingGroup({ hallazgos }: { hallazgos: Hallazgo[] }) {
  return (
    <div className="border border-border rounded-md overflow-hidden">
      {hallazgos.map((h, i) => (
        <FindingRow key={`${h.regla_id}-${i}`} h={h} />
      ))}
    </div>
  );
}

function SectionGroup({
  title,
  subtitle,
  resultado,
}: {
  title: string;
  subtitle?: string;
  resultado: ResultadoSeccion;
}) {
  const cumple = resultado.hallazgos.filter((h) => h.estado === "CUMPLE").length;
  const noCumple = resultado.hallazgos.filter((h) => h.estado === "NO CUMPLE").length;
  return (
    <section className="space-y-3">
      <header className="flex items-end justify-between gap-2 border-b border-border pb-2">
        <div className="min-w-0">
          <h3 className="text-sm font-medium text-foreground">{title}</h3>
          {subtitle && (
            <p className="text-[0.7rem] text-muted-foreground mt-0.5">{subtitle}</p>
          )}
        </div>
        <div className="flex items-center gap-3 text-[0.7rem] text-muted-foreground tabular shrink-0">
          <span className="text-success">{cumple} cumple</span>
          {noCumple > 0 && <span className="text-destructive">{noCumple} no cumple</span>}
        </div>
      </header>
      <div className="border border-border rounded-md overflow-hidden">
        {resultado.hallazgos.map((h, i) => (
          <FindingRow key={`${h.regla_id}-${i}`} h={h} />
        ))}
      </div>
    </section>
  );
}

function EmptyHint({ text }: { text: string }) {
  return (
    <div className="border border-border border-dashed rounded-md p-8 text-center text-sm text-muted-foreground">
      {text}
    </div>
  );
}

function prettifySectionName(name: string): string {
  return name
    .replace(/^_+|_+$/g, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
