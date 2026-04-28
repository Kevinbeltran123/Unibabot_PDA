"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Check,
  Clock,
  Loader2,
  LogOut,
  PanelLeftClose,
  PenLine,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ThemeToggle } from "@/components/theme-toggle";
import { BrandMark } from "@/components/brand-mark";
import { useAnalyses } from "@/hooks/use-analyses";
import { useAuth } from "@/hooks/use-auth";
import { cn, relativeTime } from "@/lib/utils";
import type { AnalysisStatus } from "@/lib/types";

/*
 * Sidebar tipo chat. Tres zonas verticales:
 *  1) Marca (top): wordmark + boton compacto "+ Nuevo"
 *  2) Lista de conversaciones (analisis previos)
 *  3) Footer: usuario + tema + logout
 *
 * Cada item de la lista muestra: indicador de estado (dot, icon),
 * nombre del archivo, codigo del curso y tiempo relativo.
 */

function StatusDot({ status }: { status: AnalysisStatus }) {
  if (status === "running") {
    return <Loader2 className="h-3 w-3 text-foreground animate-spin shrink-0" />;
  }
  if (status === "pending") {
    return <Clock className="h-3 w-3 text-muted-foreground shrink-0" />;
  }
  if (status === "failed") {
    return <XCircle className="h-3 w-3 text-destructive shrink-0" />;
  }
  return <Check className="h-3 w-3 text-success shrink-0" strokeWidth={2.5} />;
}

interface ChatSidebarProps {
  /** Callback opcional para cerrar/colapsar el sidebar (botón en el top) */
  onCollapse?: () => void;
}

export function ChatSidebar({ onCollapse }: ChatSidebarProps = {}) {
  const { data, isLoading } = useAnalyses();
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  return (
    <aside className="flex h-screen w-[280px] shrink-0 flex-col bg-paper-warm border-r border-border">
      {/* Top: brand + colapsar */}
      <div className="px-4 pt-5 pb-3 flex items-center justify-between gap-2">
        <Link href="/dashboard" aria-label="Inicio">
          <BrandMark />
        </Link>
        {onCollapse && (
          <Button
            variant="ghost"
            size="icon"
            aria-label="Ocultar panel lateral"
            onClick={onCollapse}
            className="h-7 w-7 text-muted-foreground hover:text-foreground -mr-1"
          >
            <PanelLeftClose className="h-3.5 w-3.5" strokeWidth={1.75} />
          </Button>
        )}
      </div>

      <div className="px-3 pb-2">
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2 bg-background"
          onClick={() => router.push("/dashboard")}
        >
          <PenLine className="h-3.5 w-3.5" />
          Nuevo análisis
        </Button>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-2 py-3">
        <div className="px-2 pb-1.5 text-[0.625rem] uppercase tracking-institutional text-muted-foreground">
          Historial
        </div>

        {isLoading ? (
          <div className="space-y-2 px-1.5">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-12" />
            ))}
          </div>
        ) : !data || data.length === 0 ? (
          <p className="px-3 pt-2 text-xs text-muted-foreground leading-relaxed">
            Aún no has analizado ningún PDA. Sube tu primer documento desde la ventana principal.
          </p>
        ) : (
          <ul className="space-y-0.5">
            {data.map((a) => {
              const href =
                a.status === "done"
                  ? `/dashboard/analyses/${a.id}`
                  : `/dashboard/analyses/${a.id}/processing`;
              const active = pathname?.startsWith(`/dashboard/analyses/${a.id}`);
              return (
                <li key={a.id}>
                  <Link
                    href={href}
                    className={cn(
                      "group flex items-start gap-2 rounded-md px-2.5 py-2 transition-colors",
                      active ? "bg-background" : "hover:bg-background/60",
                    )}
                  >
                    <span className="mt-1">
                      <StatusDot status={a.status} />
                    </span>
                    <span className="flex-1 min-w-0">
                      <span
                        className={cn(
                          "block text-[0.8rem] truncate",
                          active ? "text-foreground font-medium" : "text-foreground",
                        )}
                      >
                        {a.filename}
                      </span>
                      <span className="block text-[0.7rem] text-muted-foreground mt-0.5 truncate">
                        {a.codigo_curso ? (
                          <span className="font-mono mr-1.5">{a.codigo_curso}</span>
                        ) : null}
                        {relativeTime(a.created_at)}
                      </span>
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-border px-3 py-3">
        <div className="flex items-center gap-2">
          <div className="flex-1 min-w-0 px-1.5">
            <div className="text-[0.78rem] truncate text-foreground">{user?.email}</div>
          </div>
          <ThemeToggle />
          <Button
            variant="ghost"
            size="icon"
            aria-label="Cerrar sesión"
            onClick={logout}
            className="h-8 w-8 text-muted-foreground hover:text-foreground"
          >
            <LogOut className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </aside>
  );
}
