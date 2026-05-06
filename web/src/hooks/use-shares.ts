"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

export function useShares(analysisId: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ["shares", analysisId],
    queryFn: () => api.listShares(analysisId),
    enabled,
  });
}

export function useCreateShare(analysisId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (expiresInDays: number | null) =>
      api.createShare(analysisId, expiresInDays),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["shares", analysisId] }),
  });
}

export function useRevokeShare(analysisId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (shareId: string) => api.revokeShare(shareId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["shares", analysisId] }),
  });
}
