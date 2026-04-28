"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Loader2, Menu, PanelLeft } from "lucide-react";
import { ChatSidebar } from "@/components/chat-sidebar";
import { BrandMark } from "@/components/brand-mark";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

/*
 * Layout chat con sidebar colapsable animado.
 *
 * Técnica: el contenedor desktop es un grid de 2 columnas con la primera
 * animando entre [280px] y [0px] vía `transition: grid-template-columns`.
 * El sidebar interno mantiene su ancho fijo de 280px y se desliza con
 * `translateX(-100%)` cuando colapsa, dando un slide suave.
 *
 * En mobile el sidebar es un drawer overlay con animación slide-in/out.
 */

const SIDEBAR_KEY = "unibabot.sidebar.collapsed";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [mobileSidebar, setMobileSidebar] = React.useState(false);
  const [collapsed, setCollapsed] = React.useState(false);
  const [hydrated, setHydrated] = React.useState(false);

  React.useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  React.useEffect(() => {
    try {
      const stored = window.localStorage.getItem(SIDEBAR_KEY);
      if (stored === "1") setCollapsed(true);
    } catch {
      /* ignore */
    }
    setHydrated(true);
  }, []);

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        window.localStorage.setItem(SIDEBAR_KEY, next ? "1" : "0");
      } catch {
        /* ignore */
      }
      return next;
    });
  }

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Antes de hidratar usamos el estado expandido por defecto para evitar flash.
  const isCollapsed = hydrated && collapsed;
  const easing = "cubic-bezier(0.32, 0.72, 0, 1)";

  return (
    <div className="h-screen overflow-hidden bg-background">
      {/* Desktop layout: grid con primera columna animada */}
      <div
        className="hidden md:grid h-screen"
        style={{
          gridTemplateColumns: isCollapsed ? "0px 1fr" : "280px 1fr",
          transition: `grid-template-columns 320ms ${easing}`,
        }}
      >
        {/* Slot del sidebar */}
        <div className="overflow-hidden">
          <div
            className="w-[280px] h-full"
            style={{
              transform: isCollapsed ? "translateX(-100%)" : "translateX(0)",
              transition: `transform 320ms ${easing}`,
            }}
          >
            <ChatSidebar onCollapse={toggleCollapsed} />
          </div>
        </div>

        {/* Main */}
        <div className="flex flex-col min-w-0 relative">
          <main className="flex-1 overflow-y-auto">{children}</main>
        </div>
      </div>

      {/* Botón flotante para reabrir el sidebar en desktop */}
      <div
        className={cn(
          "hidden md:block fixed top-3 left-3 z-30",
          "transition-all duration-300",
          isCollapsed
            ? "opacity-100 translate-x-0 pointer-events-auto delay-200"
            : "opacity-0 -translate-x-2 pointer-events-none",
        )}
        style={{ transitionTimingFunction: easing }}
      >
        <Button
          variant="ghost"
          size="icon"
          aria-label="Mostrar panel lateral"
          onClick={toggleCollapsed}
          className="h-8 w-8 text-muted-foreground hover:text-foreground bg-background/80 backdrop-blur-sm border border-border/60"
        >
          <PanelLeft className="h-4 w-4" strokeWidth={1.75} />
        </Button>
      </div>

      {/* Mobile layout */}
      <div className="md:hidden flex flex-col h-screen">
        <div className="flex items-center justify-between px-3 py-3 border-b border-border">
          <Button
            variant="ghost"
            size="icon"
            aria-label="Abrir menú"
            onClick={() => setMobileSidebar(true)}
            className="h-8 w-8"
          >
            <Menu className="h-4 w-4" />
          </Button>
          <BrandMark variant="text" className="text-base" />
          <span className="w-8" />
        </div>
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>

      {/* Mobile drawer */}
      <div
        className={cn(
          "md:hidden fixed inset-0 z-50",
          mobileSidebar ? "pointer-events-auto" : "pointer-events-none",
        )}
      >
        {/* Overlay */}
        <div
          className={cn(
            "absolute inset-0 bg-foreground/30 transition-opacity duration-300",
            mobileSidebar ? "opacity-100" : "opacity-0",
          )}
          onClick={() => setMobileSidebar(false)}
        />
        {/* Panel */}
        <div
          className="absolute inset-y-0 left-0 w-[280px]"
          style={{
            transform: mobileSidebar ? "translateX(0)" : "translateX(-100%)",
            transition: `transform 320ms ${easing}`,
          }}
        >
          <ChatSidebar onCollapse={() => setMobileSidebar(false)} />
        </div>
      </div>
    </div>
  );
}
