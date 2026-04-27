"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { api, clearToken, getToken, setToken } from "@/lib/api-client";
import type { UserPublic } from "@/lib/types";

interface AuthCtx {
  user: UserPublic | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const Ctx = React.createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<UserPublic | null>(null);
  const [loading, setLoading] = React.useState(true);
  const router = useRouter();

  const refresh = React.useCallback(async () => {
    const tk = getToken();
    if (!tk) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await api.me();
      setUser(me);
    } catch {
      clearToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  const login = React.useCallback(
    async (email: string, password: string) => {
      const r = await api.login(email, password);
      setToken(r.access_token);
      setUser(r.user);
      router.push("/dashboard");
    },
    [router],
  );

  const register = React.useCallback(
    async (email: string, password: string) => {
      const r = await api.register(email, password);
      setToken(r.access_token);
      setUser(r.user);
      router.push("/dashboard");
    },
    [router],
  );

  const logout = React.useCallback(() => {
    clearToken();
    setUser(null);
    router.push("/login");
  }, [router]);

  return (
    <Ctx.Provider value={{ user, loading, login, register, logout, refresh }}>{children}</Ctx.Provider>
  );
}

export function useAuth() {
  const ctx = React.useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
