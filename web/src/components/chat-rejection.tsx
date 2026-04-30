import * as React from "react";
import { FileX, RefreshCw, Lightbulb } from "lucide-react";
import { Button } from "@/components/ui/button";

/*
 * Contenido del AssistantMessage cuando el backend rechaza el upload con
 * 422. Muestra el mensaje natural del clasificador + un hint accionable
 * dependiente del codigo de rechazo + boton para reintentar adjuntando
 * otro archivo.
 */

const HINTS_BY_CODE: Record<string, string> = {
  NOT_A_PDA:
    "Verifica que el documento sea un Plan de Desarrollo Académico de la Universidad de Ibagué con sus secciones canónicas (información general, RAE, evaluación, cronograma).",
  INSUFFICIENT_STRUCTURE:
    "Si crees que es un PDA legítimo, abre el documento y confirma que tenga al menos las secciones de Información general, RAE y Evaluación.",
  EMPTY_OR_SCANNED:
    "Si el documento es escaneado, primero pásalo por OCR (Acrobat, Preview en Mac, o herramientas como ocr.space) para que tenga texto seleccionable.",
  PDF_PARSE_ERROR:
    "Intenta abrir el PDF localmente y re-exportarlo, o quitar la protección con contraseña antes de subirlo.",
  OLD_TEMPLATE:
    "Pide la versión actual del template a tu coordinador o consulta la página oficial del programa académico.",
};

const FALLBACK_HINT =
  "Intenta de nuevo con un archivo distinto. Si crees que es un error, contacta al equipo de soporte.";

export interface RejectionMessageProps {
  filename: string;
  message: string;
  code?: string;
  onRetry?: () => void;
}

export function RejectionMessage({
  filename,
  message,
  code,
  onRetry,
}: RejectionMessageProps) {
  const hint = (code && HINTS_BY_CODE[code]) || FALLBACK_HINT;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <FileX className="h-3.5 w-3.5" />
        <span className="truncate max-w-[400px]">{filename}</span>
      </div>

      <p className="text-base leading-relaxed text-foreground/90 max-w-prose">
        {message}
      </p>

      <div className="flex items-start gap-2 rounded-md border border-border/60 bg-paper-warm/40 px-3 py-2.5 max-w-prose">
        <Lightbulb className="h-3.5 w-3.5 mt-0.5 text-muted-foreground shrink-0" />
        <p className="text-xs leading-relaxed text-muted-foreground">{hint}</p>
      </div>

      {onRetry && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onRetry}
          className="gap-1.5"
        >
          <RefreshCw className="h-3 w-3" />
          Adjuntar otro archivo
        </Button>
      )}
    </div>
  );
}
