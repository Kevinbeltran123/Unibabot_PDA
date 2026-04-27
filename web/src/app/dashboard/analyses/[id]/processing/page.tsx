"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ProgressTimeline } from "@/components/progress-stream";
import { useAnalysis } from "@/hooks/use-analyses";
import { useProgressStream } from "@/hooks/use-progress-stream";

export default function ProcessingPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;

  const { data: analysis } = useAnalysis(id, { refetchInterval: 3000 });
  const { events, status } = useProgressStream(id);

  React.useEffect(() => {
    if (!analysis) return;
    if (analysis.status === "done") {
      router.replace(`/dashboard/analyses/${id}`);
    }
  }, [analysis, id, router]);

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => router.push("/dashboard")} aria-label="Volver">
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <h1 className="text-xl font-bold tracking-tight">Analizando</h1>
          {analysis?.filename && (
            <p className="text-sm text-muted-foreground flex items-center gap-1.5">
              <FileText className="h-3.5 w-3.5" />
              {analysis.filename}
            </p>
          )}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Progreso del analisis</CardTitle>
        </CardHeader>
        <CardContent>
          <ProgressTimeline events={events} status={status} />
        </CardContent>
      </Card>

      {analysis?.status === "failed" && (
        <Card className="border-destructive/40 bg-destructive/5">
          <CardContent className="p-5 space-y-3">
            <div className="text-sm font-medium text-destructive">El analisis fallo</div>
            <p className="text-sm">{analysis.error}</p>
            <Button variant="outline" size="sm" onClick={() => router.push("/dashboard/new")}>
              Intentar con otro PDF
            </Button>
          </CardContent>
        </Card>
      )}

      <p className="text-xs text-center text-muted-foreground">
        Este proceso suele tardar entre 1 y 3 minutos. Puedes cerrar esta pestana, el analisis seguira corriendo.
      </p>
    </div>
  );
}
