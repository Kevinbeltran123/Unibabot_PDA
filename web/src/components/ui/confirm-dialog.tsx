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

/*
 * Sustituto institucional de `window.confirm()`. Provee un Dialog visual
 * en el lenguaje del producto y devuelve una Promise<boolean> (true si
 * el usuario confirma, false si cancela o cierra el modal).
 *
 * Uso:
 *
 *   const confirm = useConfirm();
 *
 *   const ok = await confirm({
 *     title: "¿Eliminar este análisis?",
 *     description: "El reporte se borrará y no podrás recuperarlo.",
 *     confirmText: "Eliminar",
 *     variant: "destructive",
 *   });
 *   if (!ok) return;
 *
 * Requiere que <ConfirmProvider> envuelva la app (ya está en el layout).
 */

interface ConfirmOptions {
  title: string;
  description?: React.ReactNode;
  confirmText?: string;
  cancelText?: string;
  variant?: "default" | "destructive";
}

interface ConfirmCtxValue {
  confirm: (options: ConfirmOptions) => Promise<boolean>;
}

const ConfirmCtx = React.createContext<ConfirmCtxValue | null>(null);

interface PendingConfirm extends ConfirmOptions {
  resolve: (value: boolean) => void;
}

export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const [pending, setPending] = React.useState<PendingConfirm | null>(null);

  const confirm = React.useCallback((options: ConfirmOptions): Promise<boolean> => {
    return new Promise<boolean>((resolve) => {
      setPending({ ...options, resolve });
    });
  }, []);

  function handleClose(value: boolean) {
    if (!pending) return;
    pending.resolve(value);
    setPending(null);
  }

  return (
    <ConfirmCtx.Provider value={{ confirm }}>
      {children}
      <Dialog open={!!pending} onOpenChange={(open) => !open && handleClose(false)}>
        {pending && (
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>{pending.title}</DialogTitle>
              {pending.description && (
                <DialogDescription>{pending.description}</DialogDescription>
              )}
            </DialogHeader>
            <DialogFooter>
              <Button variant="ghost" onClick={() => handleClose(false)} autoFocus>
                {pending.cancelText ?? "Cancelar"}
              </Button>
              <Button
                variant={pending.variant === "destructive" ? "destructive" : "default"}
                onClick={() => handleClose(true)}
              >
                {pending.confirmText ?? "Confirmar"}
              </Button>
            </DialogFooter>
          </DialogContent>
        )}
      </Dialog>
    </ConfirmCtx.Provider>
  );
}

export function useConfirm() {
  const ctx = React.useContext(ConfirmCtx);
  if (!ctx) {
    throw new Error("useConfirm debe usarse dentro de <ConfirmProvider>");
  }
  return ctx.confirm;
}
