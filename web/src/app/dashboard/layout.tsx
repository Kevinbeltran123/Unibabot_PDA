"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { LayoutDashboard, Loader2, LogOut, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  React.useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur-md">
        <div className="container flex h-14 items-center justify-between gap-4">
          <Link href="/dashboard" className="flex items-center gap-2 font-semibold">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground text-xs font-bold">
              UB
            </span>
            <span className="hidden sm:inline">UnibaBot PDA</span>
          </Link>
          <nav className="flex items-center gap-1">
            <Link href="/dashboard">
              <Button
                variant={pathname === "/dashboard" ? "secondary" : "ghost"}
                size="sm"
                className="gap-2"
              >
                <LayoutDashboard className="h-4 w-4" />
                <span className="hidden sm:inline">Mis analisis</span>
              </Button>
            </Link>
            <Link href="/dashboard/new">
              <Button
                variant={pathname === "/dashboard/new" ? "default" : "outline"}
                size="sm"
                className="gap-2"
              >
                <Plus className="h-4 w-4" />
                <span className="hidden sm:inline">Nuevo</span>
              </Button>
            </Link>
            <div className="mx-2 h-6 w-px bg-border" />
            <ThemeToggle />
            <Button variant="ghost" size="icon" onClick={logout} aria-label="Cerrar sesion">
              <LogOut className="h-4 w-4" />
            </Button>
          </nav>
        </div>
        <div className={cn("container -mt-px text-xs text-muted-foreground pb-2", "hidden md:block")}>
          {user.email}
        </div>
      </header>
      <main className="container flex-1 py-8">{children}</main>
      <footer className="border-t py-4 text-center text-xs text-muted-foreground">
        UnibaBot PDA · Universidad de Ibague · 2026
      </footer>
    </div>
  );
}
