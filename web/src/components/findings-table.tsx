"use client";

import * as React from "react";
import { Filter, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import type { ResultadoSeccion } from "@/lib/types";
import { cn } from "@/lib/utils";

type Filtro = "all" | "CUMPLE" | "NO CUMPLE";

export function FindingsTable({ resultados }: { resultados: ResultadoSeccion[] }) {
  const [filtro, setFiltro] = React.useState<Filtro>("all");
  const [query, setQuery] = React.useState("");

  const filas = React.useMemo(() => {
    const all: { seccion: string; regla_id: string; estado: string; regla: string }[] = [];
    for (const r of resultados) {
      for (const h of r.hallazgos) {
        all.push({ seccion: r.seccion, regla_id: h.regla_id, estado: h.estado, regla: h.regla });
      }
    }
    return all
      .filter((f) => filtro === "all" || f.estado === filtro)
      .filter((f) => {
        if (!query) return true;
        const q = query.toLowerCase();
        return (
          f.regla_id.toLowerCase().includes(q) ||
          f.regla.toLowerCase().includes(q) ||
          f.seccion.toLowerCase().includes(q)
        );
      });
  }, [resultados, filtro, query]);

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Buscar por regla, ID o seccion..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          <Filter className="h-3.5 w-3.5 text-muted-foreground" />
          {(["all", "CUMPLE", "NO CUMPLE"] as Filtro[]).map((f) => (
            <button
              key={f}
              onClick={() => setFiltro(f)}
              className={cn(
                "px-3 py-1.5 rounded-md font-medium transition-colors",
                filtro === f
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/70",
              )}
            >
              {f === "all" ? "Todos" : f}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="text-left font-medium px-4 py-2.5">ID</th>
              <th className="text-left font-medium px-4 py-2.5">Estado</th>
              <th className="text-left font-medium px-4 py-2.5">Seccion</th>
              <th className="text-left font-medium px-4 py-2.5">Regla</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filas.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                  No hay hallazgos para este filtro.
                </td>
              </tr>
            )}
            {filas.map((f, i) => (
              <tr key={`${f.regla_id}-${i}`} className="hover:bg-muted/30 transition-colors">
                <td className="px-4 py-2 font-mono text-xs text-muted-foreground">{f.regla_id}</td>
                <td className="px-4 py-2">
                  <Badge variant={f.estado === "CUMPLE" ? "success" : "destructive"}>{f.estado}</Badge>
                </td>
                <td className="px-4 py-2 text-muted-foreground">{f.seccion}</td>
                <td className="px-4 py-2 max-w-md truncate" title={f.regla}>
                  {f.regla}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
