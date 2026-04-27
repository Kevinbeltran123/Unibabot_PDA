import type { AnalysisDetail, AnalysisSummary, TokenResponse } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "unibabot_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(
  path: string,
  init: RequestInit & { auth?: boolean; raw?: boolean } = {},
): Promise<T> {
  const { auth = true, raw = false, headers, ...rest } = init;
  const finalHeaders: Record<string, string> = {
    Accept: "application/json",
    ...(headers as Record<string, string>),
  };
  if (!raw && !(rest.body instanceof FormData)) {
    finalHeaders["Content-Type"] = "application/json";
  }
  if (auth) {
    const token = getToken();
    if (token) finalHeaders["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API}${path}`, { ...rest, headers: finalHeaders });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  health: () => request<{ status: string }>("/api/health", { auth: false }),

  register: (email: string, password: string) =>
    request<TokenResponse>("/api/auth/register", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    request<TokenResponse>("/api/auth/login", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<{ id: string; email: string; created_at: string }>("/api/auth/me"),

  listAnalyses: () => request<AnalysisSummary[]>("/api/analyses"),

  getAnalysis: (id: string) => request<AnalysisDetail>(`/api/analyses/${id}`),

  createAnalysis: (form: FormData) =>
    request<{ id: string; status: string }>("/api/analyses", {
      method: "POST",
      body: form,
    }),

  deleteAnalysis: (id: string) =>
    request<void>(`/api/analyses/${id}`, { method: "DELETE" }),

  downloadUrl: (id: string) => `${API}/api/analyses/${id}/download`,

  eventsUrl: (id: string) => `${API}/api/analyses/${id}/events`,
};

export { ApiError };
