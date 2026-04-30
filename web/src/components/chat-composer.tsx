"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { ArrowUp, FileText, Loader2, Paperclip, Settings2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AnalysisOptions,
  AttachOptionsDialog,
  DEFAULT_OPTIONS,
} from "./attach-options-dialog";
import { useCreateAnalysis } from "@/hooks/use-analyses";
import { toast } from "@/hooks/use-toast";
import { ApiError } from "@/lib/api-client";
import { cn } from "@/lib/utils";

/*
 * Composer institucional. Es el area de input principal del chat: una caja
 * con borde fino que SE EXPANDE en estado drag-over. El boton primario es
 * adjuntar PDF (visualmente prominente). Una vez adjunto, aparece un chip
 * con nombre + opciones aplicadas y se habilita el send.
 *
 * Funcionalmente: al hacer send, llama useCreateAnalysis y navega a la
 * pantalla de processing del id retornado. Si el backend rechaza el PDF
 * con 422 (no es PDA, escaneado, corrupto, etc.) llama a `onRejection`
 * para que el dashboard renderice la respuesta como AssistantMessage en
 * lugar de mostrarla como toast efimero.
 */

export interface ChatComposerProps {
  onRejection?: (params: {
    filename: string;
    message: string;
    code?: string;
  }) => void;
  onSubmitStart?: (filename: string) => void;
}

export function ChatComposer({ onRejection, onSubmitStart }: ChatComposerProps = {}) {
  const router = useRouter();
  const create = useCreateAnalysis();
  const [file, setFile] = React.useState<File | null>(null);
  const [opts, setOpts] = React.useState<AnalysisOptions>(DEFAULT_OPTIONS);
  const [optsOpen, setOptsOpen] = React.useState(false);
  const [note, setNote] = React.useState("");

  const onDrop = React.useCallback((accepted: File[]) => {
    if (accepted[0]) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive, isDragReject, open: openPicker } =
    useDropzone({
      onDrop,
      multiple: false,
      noClick: true,
      noKeyboard: true,
      accept: { "application/pdf": [".pdf"] },
      maxSize: 20 * 1024 * 1024,
    });

  const optionsApplied =
    opts.codigoCurso.trim() !== "" ||
    opts.dispatcher !== DEFAULT_OPTIONS.dispatcher ||
    opts.enriquecer ||
    opts.generarResumen;

  async function onSend() {
    if (!file) {
      toast({
        title: "Falta el PDA",
        description: "Adjunta el PDF antes de iniciar el análisis.",
        variant: "destructive",
      });
      return;
    }
    const submittedName = file.name;
    onSubmitStart?.(submittedName);

    const form = new FormData();
    form.append("file", file);
    form.append("modelo", "qwen2.5:14b");
    form.append("dispatcher", opts.dispatcher);
    form.append("top_k", "5");
    form.append("enriquecer", String(opts.enriquecer));
    form.append("generar_resumen", String(opts.generarResumen));
    if (opts.codigoCurso.trim()) form.append("codigo_curso", opts.codigoCurso.trim());

    try {
      const r = await create.mutateAsync(form);
      router.push(`/dashboard/analyses/${r.id}/processing`);
    } catch (err) {
      // Rechazo del clasificador (no es PDA, escaneado, corrupto): renderizar
      // como respuesta del asistente en el chat. Otros errores siguen como toast.
      if (err instanceof ApiError && err.status === 422 && onRejection) {
        onRejection({
          filename: submittedName,
          message: err.message,
          code: err.code,
        });
        setFile(null);
        return;
      }
      const msg = err instanceof ApiError ? err.message : "Error inesperado";
      toast({
        title: "No se pudo iniciar el análisis",
        description: msg.length < 120 ? msg : "Intenta de nuevo en unos segundos.",
        variant: "destructive",
      });
    }
  }

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={cn(
          "relative rounded-md border bg-card transition-colors",
          isDragActive && "border-foreground bg-paper-warm",
          isDragReject && "border-destructive",
          !isDragActive && !isDragReject && "border-border hover:border-border-strong",
        )}
      >
        <input {...getInputProps()} aria-label="Adjuntar PDF" />

        {/* File chip cuando hay archivo */}
        {file && (
          <div className="px-3 pt-3">
            <div className="inline-flex items-center gap-2 rounded-md border border-border bg-paper-warm px-2.5 py-1.5">
              <FileText className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-xs text-foreground max-w-[260px] truncate">
                {file.name}
              </span>
              <span className="text-[0.65rem] text-muted-foreground tabular">
                {(file.size / 1024 / 1024).toFixed(1)} MB
              </span>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setFile(null);
                }}
                aria-label="Quitar archivo"
                className="ml-1 text-muted-foreground hover:text-foreground transition-colors"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          </div>
        )}

        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder={
            file
              ? "Añade un comentario opcional para tu archivo..."
              : "Arrastra un PDF aquí o usa el clip para adjuntarlo"
          }
          rows={file ? 2 : 3}
          className={cn(
            "w-full resize-none bg-transparent px-4 py-3.5 text-sm",
            "text-foreground placeholder:text-muted-foreground/70",
            "focus:outline-none",
          )}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              onSend();
            }
          }}
        />

        {/* Action row */}
        <div className="flex items-center justify-between gap-2 px-2 pb-2 pt-0.5">
          <div className="flex items-center gap-1">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={openPicker}
              className="gap-1.5 text-muted-foreground hover:text-foreground"
              aria-label="Adjuntar PDF"
            >
              <Paperclip className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Adjuntar PDF</span>
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setOptsOpen(true)}
              className="gap-1.5 text-muted-foreground hover:text-foreground"
            >
              <Settings2 className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Opciones</span>
              {optionsApplied && (
                <Badge variant="warning" className="ml-1 h-4 px-1 py-0 text-[0.55rem]">
                  Activas
                </Badge>
              )}
            </Button>
          </div>

          <Button
            type="button"
            onClick={onSend}
            disabled={!file || create.isPending}
            size="sm"
            className="gap-1.5"
          >
            {create.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <ArrowUp className="h-3.5 w-3.5" strokeWidth={2.5} />
            )}
            Iniciar
          </Button>
        </div>
      </div>

      <AttachOptionsDialog
        open={optsOpen}
        onOpenChange={setOptsOpen}
        initial={opts}
        onApply={setOpts}
      />
    </div>
  );
}
