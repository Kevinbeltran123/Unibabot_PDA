"use client";

import * as React from "react";
import { Check, Copy, Link2, Loader2, Share2, Trash2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useCreateShare, useRevokeShare, useShares } from "@/hooks/use-shares";
import { useConfirm } from "@/components/ui/confirm-dialog";
import { toast } from "@/hooks/use-toast";
import { cn, formatDate } from "@/lib/utils";
import type { ShareCreated, ShareSummary } from "@/lib/types";

/*
 * Dialog para gestionar share-links read-only del analisis con la vista
 * docente. Permite crear con TTL (7/14/30 dias o sin expiracion), copiar
 * el token plano UNA sola vez al crearlo, y revocar links activos.
 *
 * Decision de seguridad: el token plano solo se ve en la respuesta del
 * POST. Despues de cerrar el dialog o crear otro link, el plano se va y
 * solo queda el hash en DB.
 */

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  analysisId: string;
}

const TTL_OPTIONS: { label: string; value: number | null }[] = [
  { label: "7 dias", value: 7 },
  { label: "14 dias", value: 14 },
  { label: "30 dias", value: 30 },
  { label: "Sin expiracion", value: null },
];

export function ShareDialog({ open, onOpenChange, analysisId }: Props) {
  const [ttl, setTtl] = React.useState<number | null>(30);
  const [justCreated, setJustCreated] = React.useState<ShareCreated | null>(null);

  const { data: shares, isLoading } = useShares(analysisId, open);
  const createMut = useCreateShare(analysisId);
  const revokeMut = useRevokeShare(analysisId);
  const confirm = useConfirm();

  React.useEffect(() => {
    if (!open) {
      setJustCreated(null);
      setTtl(30);
    }
  }, [open]);

  async function handleCreate() {
    try {
      const created = await createMut.mutateAsync(ttl);
      setJustCreated(created);
    } catch {
      toast({
        title: "No se pudo crear el link",
        description: "Intenta de nuevo en unos segundos.",
        variant: "destructive",
      });
    }
  }

  async function handleRevoke(share: ShareSummary) {
    const ok = await confirm({
      title: "Revocar este link?",
      description:
        "El docente perdera acceso inmediato. No se puede deshacer.",
      confirmText: "Revocar",
      variant: "destructive",
    });
    if (!ok) return;
    try {
      await revokeMut.mutateAsync(share.id);
      toast({
        title: "Link revocado",
        description: "El docente ya no puede abrir este enlace.",
        variant: "success",
      });
    } catch {
      toast({
        title: "No se pudo revocar",
        description: "Intenta de nuevo en unos segundos.",
        variant: "destructive",
      });
    }
  }

  const activos = (shares || []).filter((s) => s.revoked_at === null);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Compartir con docente</DialogTitle>
          <DialogDescription>
            Genera un link read-only que el docente puede abrir sin tener cuenta.
            Solo verá los hallazgos por corregir y el resumen para él.
          </DialogDescription>
        </DialogHeader>

        {justCreated ? (
          <JustCreatedPanel
            share={justCreated}
            onCreateAnother={() => setJustCreated(null)}
          />
        ) : (
          <>
            <CreateForm
              ttl={ttl}
              setTtl={setTtl}
              onCreate={handleCreate}
              creating={createMut.isPending}
            />

            <div className="border-t border-border pt-5 mt-2">
              <div className="text-[0.65rem] uppercase tracking-institutional text-muted-foreground mb-3">
                Links activos
              </div>
              {isLoading ? (
                <div className="flex justify-center py-4">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              ) : activos.length === 0 ? (
                <p className="text-xs text-muted-foreground italic">
                  No hay links activos para este análisis.
                </p>
              ) : (
                <div className="space-y-2">
                  {activos.map((s) => (
                    <ShareRow
                      key={s.id}
                      share={s}
                      onRevoke={() => handleRevoke(s)}
                      revoking={revokeMut.isPending}
                    />
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

function CreateForm({
  ttl,
  setTtl,
  onCreate,
  creating,
}: {
  ttl: number | null;
  setTtl: (v: number | null) => void;
  onCreate: () => void;
  creating: boolean;
}) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Vigencia del link</Label>
        <div className="flex flex-wrap gap-2">
          {TTL_OPTIONS.map((opt) => {
            const selected = opt.value === ttl;
            return (
              <button
                key={String(opt.value)}
                type="button"
                onClick={() => setTtl(opt.value)}
                className={cn(
                  "px-3 py-1.5 rounded-md border text-xs transition-colors",
                  selected
                    ? "border-foreground bg-foreground text-background"
                    : "border-border bg-card hover:border-border-strong text-foreground",
                )}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
        {ttl === null && (
          <p className="text-[0.7rem] text-warning leading-relaxed">
            Sin expiración: el link va a funcionar hasta que lo revoques manualmente.
            No recomendado para distribución pública.
          </p>
        )}
      </div>

      <Button
        type="button"
        onClick={onCreate}
        disabled={creating}
        className="w-full gap-1.5"
      >
        {creating ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Share2 className="h-3.5 w-3.5" />
        )}
        Crear link
      </Button>
    </div>
  );
}

function JustCreatedPanel({
  share,
  onCreateAnother,
}: {
  share: ShareCreated;
  onCreateAnother: () => void;
}) {
  const [copied, setCopied] = React.useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(share.url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast({
        title: "No se pudo copiar",
        description: "Selecciona el link manualmente y cópialo.",
        variant: "destructive",
      });
    }
  }

  return (
    <div className="space-y-4">
      <div className="border border-warning/40 bg-warning/5 rounded-md p-3 text-xs text-foreground/85 leading-relaxed">
        Este link solo se muestra una vez. Cópialo ahora y envíalo al docente.
        Al cerrar este diálogo no podrás volver a verlo.
      </div>

      <div className="space-y-2">
        <Label>Link para el docente</Label>
        <div className="flex gap-2">
          <input
            readOnly
            value={share.url}
            className="flex-1 min-w-0 font-mono text-[0.7rem] px-3 py-2 rounded-md border border-border bg-paper-warm/40 text-foreground"
            onFocus={(e) => e.target.select()}
          />
          <Button
            type="button"
            variant="default"
            size="sm"
            onClick={handleCopy}
            className="gap-1.5 shrink-0"
          >
            {copied ? (
              <Check className="h-3.5 w-3.5" />
            ) : (
              <Copy className="h-3.5 w-3.5" />
            )}
            {copied ? "Copiado" : "Copiar"}
          </Button>
        </div>
        {share.expires_at && (
          <p className="text-[0.7rem] text-muted-foreground">
            Expira el <span className="tabular text-foreground">{formatDate(share.expires_at)}</span>.
          </p>
        )}
      </div>

      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={onCreateAnother}
        className="w-full"
      >
        Crear otro link
      </Button>
    </div>
  );
}

function ShareRow({
  share,
  onRevoke,
  revoking,
}: {
  share: ShareSummary;
  onRevoke: () => void;
  revoking: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-3 px-3 py-2 rounded-md border border-border bg-paper-warm/30">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 text-xs text-foreground">
          <Link2 className="h-3 w-3 text-muted-foreground shrink-0" />
          <span className="truncate">
            Creado {formatDate(share.created_at)}
          </span>
        </div>
        <div className="text-[0.7rem] text-muted-foreground tabular mt-0.5">
          {share.expires_at ? `Expira ${formatDate(share.expires_at)}` : "Sin expiración"}
          {share.access_count > 0 && (
            <>
              <span className="mx-1.5">·</span>
              {share.access_count} {share.access_count === 1 ? "vista" : "vistas"}
            </>
          )}
        </div>
      </div>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        onClick={onRevoke}
        disabled={revoking}
        aria-label="Revocar link"
        className="h-7 w-7 text-muted-foreground hover:text-destructive shrink-0"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}
