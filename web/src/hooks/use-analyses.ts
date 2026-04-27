"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

export function useAnalyses() {
  return useQuery({
    queryKey: ["analyses"],
    queryFn: () => api.listAnalyses(),
  });
}

export function useAnalysis(id: string, opts?: { refetchInterval?: number | false }) {
  return useQuery({
    queryKey: ["analyses", id],
    queryFn: () => api.getAnalysis(id),
    refetchInterval: opts?.refetchInterval,
  });
}

export function useCreateAnalysis() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (form: FormData) => api.createAnalysis(form),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["analyses"] }),
  });
}

export function useDeleteAnalysis() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteAnalysis(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["analyses"] }),
  });
}
