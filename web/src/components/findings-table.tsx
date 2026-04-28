"use client";

import * as React from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import type { ResultadoSeccion } from "@/lib/types";
import { cn } from "@/lib/utils";

type Filtro = "all" | "CUMPLE" | "NO CUMPLE";

const FILTROS: { value: Filtro; label: string }[] = [
  { value: "all", label: "Todos" },
  { value: "CUMPLE", label: "Cumple" },
  { value: "NO CUMPLE", label: "No cumple" },
];

/*
 * Tabla compacta editorial. Sin halos. Header en uppercase mini. Indicador
 * lateral en la columna ID. Filtros como ribbon de botones de texto.
 */
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
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-0 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Buscar regla, ID o sección"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-6"
          />
        </div>
        <div className="flex items-center gap-3 text-xs">
          {FILTROS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFiltro(f.value)}
              className={cn(
                "py-1 transition-colors",
                filtro === f.value
                  ? "text-foreground underline-gold"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="border-t border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[0.625rem] uppercase tracking-institutional text-muted-foreground">
              <th className="font-medium py-2 pr-4 w-[6.5rem]">Estado</th>
              <th className="font-medium py-2 pr-4 w-[6rem]">ID</th>
              <th className="font-medium py-2 pr-4">Regla</th>
              <th className="font-medium py-2 hidden md:table-cell w-[10rem]">Sección</th>
            </tr>
          </thead>
          <tbody>
            {filas.length === 0 && (
              <tr>
                <td colSpan={4} className="py-12 text-center text-sm text-muted-foreground border-t border-border">
                  No hay hallazgos para este filtro.
                </td>
              </tr>
            )}
            {filas.map((f, i) => {
              const ok = f.estado === "CUMPLE";
              return (
                <tr
                  key={`${f.regla_id}-${i}`}
                  className="border-t border-border hover:bg-paper-warm/60 transition-colors"
                >
                  <td className="py-2.5 pr-4">
                    <span
                      className={cn(
                        "text-[0.625rem] font-medium uppercase tracking-institutional",
                        ok ? "text-success" : "text-destructive",
                      )}
                    >
                      {ok ? "Cumple" : "No cumple"}
                    </span>
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-[0.7rem] text-muted-foreground">
                    {f.regla_id}
                  </td>
                  <td className="py-2.5 pr-4 max-w-md truncate text-foreground" title={f.regla}>
                    {f.regla}
                  </td>
                  <td className="py-2.5 hidden md:table-cell text-xs text-muted-foreground truncate">
                    {f.seccion.replace(/^__|__$|_global_/g, "").replace(/_/g, " ")}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-[0.7rem] text-muted-foreground">
        {filas.length} de {resultados.reduce((acc, r) => acc + r.hallazgos.length, 0)} hallazgos visibles
      </p>
    </div>
  );
}
