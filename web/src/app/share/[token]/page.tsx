"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AlertTriangle, Clock, FileText, Loader2 } from "lucide-react";
import { BrandMark } from "@/components/brand-mark";
import { ApiError, api } from "@/lib/api-client";
import { cn, formatDate } from "@/lib/utils";
import type { SharedHallazgo, SharedSeccion, SharePublic } from "@/lib/types";

/*
 * Vista publica read-only del reporte para el docente.
 *
 * Sin auth, sin sidebar. Layout propio para que sea visualmente claro
 * que el usuario NO esta logueado en una cuenta. Renderiza solo:
 *  - resumen para docente (si fue generado con --resumen)
 *  - hallazgos NO CUMPLE agrupados por seccion, con su correccion
 *
 * Estados: 410 (expirado/revocado) y 404 (no existe) con UX explicita.
 */

export default function SharedReportPage() {
  const params = useParams<{ token: string }>();
  const token = params?.token;

  const [data, setData] = React.useState<SharePublic | null>(null);
  const [error, setError] = React.useState<{ status: number; message: string } | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLoading(true);
    api
      .getShared(token)
      .then((resp) => {
        if (!cancelled) setData(resp);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError) {
          setError({ status: err.status, message: err.message });
        } else {
          setError({ status: 0, message: "Error inesperado" });
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return <ErrorState status={error.status} message={error.message} />;
  }

  if (!data) {
    return <ErrorState status={0} message="No se pudo cargar el reporte" />;
  }

  return <ReportView data={data} />;
}

function ReportView({ data }: { data: SharePublic }) {
  const { report } = data;
  return (
    <div className="min-h-screen bg-background">
      <PublicHeader />
      <main className="mx-auto w-full max-w-[820px] px-6 py-8">
        <Attribution
          sharedBy={data.shared_by}
          completedAt={data.analysis_completed_at}
          expiresAt={data.expires_at}
        />

        <h1 className="mt-6 text-2xl font-medium tracking-tight text-foreground">
          {report.archivo}
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Revision automatica de PDA. Vista enfocada en lo que requiere correccion (
          <span className="tabular text-foreground">{report.total_no_cumple}</span>{" "}
          {report.total_no_cumple === 1 ? "hallazgo" : "hallazgos"}).
        </p>

        {report.resumen_docente && (
          <section className="mt-8 border border-border rounded-md p-5 bg-paper-warm/40">
            <div className="text-[0.65rem] uppercase tracking-institutional text-muted-foreground mb-2">
              Resumen para el docente
            </div>
            <p className="text-sm leading-relaxed text-foreground/90 whitespace-pre-wrap">
              {report.resumen_docente}
            </p>
          </section>
        )}

        {report.secciones.length === 0 ? (
          <section className="mt-8 border border-border rounded-md p-6 text-center text-sm text-muted-foreground">
            No hay hallazgos por corregir. Todo en orden.
          </section>
        ) : (
          <section className="mt-8 space-y-8">
            {report.secciones.map((s) => (
              <SectionGroup key={s.seccion} resultado={s} />
            ))}
          </section>
        )}

        <PublicFooter />
      </main>
    </div>
  );
}

function PublicHeader() {
  return (
    <header className="border-b border-border bg-background">
      <div className="mx-auto w-full max-w-[820px] px-6 py-4 flex items-center gap-3">
        <BrandMark variant="default" />
        <span className="ml-auto text-[0.65rem] uppercase tracking-institutional text-muted-foreground">
          Vista compartida
        </span>
      </div>
    </header>
  );
}

function PublicFooter() {
  return (
    <footer className="mt-16 pt-6 border-t border-border text-[0.7rem] text-muted-foreground leading-relaxed">
      Esta vista fue compartida con el docente para facilitar las correcciones.
      No se requiere cuenta para abrirla. Si tienes preguntas sobre el contenido,
      contacta a la oficina que lo envio.
    </footer>
  );
}

function Attribution({
  sharedBy,
  completedAt,
  expiresAt,
}: {
  sharedBy: string;
  completedAt: string | null;
  expiresAt: string | null;
}) {
  const expiringSoon = React.useMemo(() => {
    if (!expiresAt) return false;
    const ms = new Date(expiresAt).getTime() - Date.now();
    const days = ms / (1000 * 60 * 60 * 24);
    return days > 0 && days < 3;
  }, [expiresAt]);

  return (
    <div className="space-y-2 text-xs text-muted-foreground">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span>Compartido por</span>
        <span className="font-medium text-foreground">{sharedBy}</span>
        {completedAt && (
          <>
            <span>el</span>
            <span className="tabular text-foreground">{formatDate(completedAt)}</span>
          </>
        )}
      </div>
      {expiresAt && (
        <div
          className={cn(
            "inline-flex items-center gap-1.5",
            expiringSoon && "text-warning",
          )}
        >
          <Clock className="h-3 w-3" />
          <span>
            {expiringSoon ? "Expira en menos de 3 dias: " : "Expira el "}
            <span className="tabular">{formatDate(expiresAt)}</span>
          </span>
        </div>
      )}
    </div>
  );
}

function SectionGroup({ resultado }: { resultado: SharedSeccion }) {
  return (
    <section>
      <header className="border-b border-border pb-2 mb-3 flex items-end justify-between gap-2">
        <h2 className="text-sm font-medium text-foreground">
          {prettifySectionName(resultado.seccion)}
        </h2>
        <span className="text-[0.7rem] tabular text-destructive">
          {resultado.hallazgos.length} no cumple
        </span>
      </header>
      <div className="border border-border rounded-md overflow-hidden">
        {resultado.hallazgos.map((h, i) => (
          <FindingCard key={`${h.regla_id}-${i}`} h={h} />
        ))}
      </div>
    </section>
  );
}

function FindingCard({ h }: { h: SharedHallazgo }) {
  const correccion = h.correccion_enriquecida || h.correccion;
  return (
    <article className="relative border-b border-border last:border-b-0 px-4 py-4">
      <span aria-hidden className="absolute left-0 top-0 bottom-0 w-[2px] bg-destructive" />
      <div className="flex items-start gap-3">
        <span className="shrink-0 mt-0.5 font-mono text-[0.7rem] text-muted-foreground min-w-[5rem]">
          {h.regla_id}
        </span>
        <div className="flex-1 min-w-0 space-y-3">
          <p className="text-sm leading-snug text-foreground">{h.regla}</p>

          {h.evidencia && (
            <div className="text-xs">
              <div className="text-[0.65rem] uppercase tracking-institutional text-muted-foreground mb-1">
                Evidencia detectada
              </div>
              <div className="bg-paper-warm/60 border-l-2 border-border pl-3 py-1.5 text-foreground/85 whitespace-pre-wrap">
                {h.evidencia}
              </div>
            </div>
          )}

          {correccion && (
            <div className="text-xs">
              <div className="text-[0.65rem] uppercase tracking-institutional text-muted-foreground mb-1">
                Sugerencia de correccion
              </div>
              <div className="text-foreground/95 leading-relaxed whitespace-pre-wrap">
                {correccion}
              </div>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

function ErrorState({ status, message }: { status: number; message: string }) {
  const title =
    status === 404
      ? "Link no encontrado"
      : status === 410
        ? "Link expirado o revocado"
        : status === 429
          ? "Demasiados intentos"
          : "No se pudo cargar el reporte";

  const explanation =
    status === 404
      ? "El link que abriste no existe. Verifica que sea el ultimo enviado por la oficina."
      : status === 410
        ? "Este link ya no esta activo. Puede que la oficina lo haya revocado o que haya pasado su fecha de expiracion. Pidele uno nuevo."
        : status === 429
          ? "Estas haciendo demasiadas peticiones. Espera un momento e intenta de nuevo."
          : message || "Hubo un error al cargar el reporte.";

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-6">
      <div className="max-w-md w-full border border-border rounded-md p-6 bg-card">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
          <div className="space-y-2">
            <h1 className="text-base font-medium text-foreground">{title}</h1>
            <p className="text-sm text-muted-foreground leading-relaxed">{explanation}</p>
            <Link
              href="/"
              className="inline-flex items-center gap-1 text-xs text-foreground hover:underline mt-3"
            >
              <FileText className="h-3 w-3" />
              Ir al inicio
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function prettifySectionName(s: string): string {
  if (s === "__estructural_global__") return "Hallazgos estructurales";
  if (s === "__declaraciones_global__") return "Declaraciones canonicas";
  if (s === "__seccion_ausente_global__") return "Secciones ausentes";
  return s.charAt(0).toUpperCase() + s.slice(1);
}
