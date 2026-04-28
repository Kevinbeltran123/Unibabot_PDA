"use client";

import * as React from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PasswordInput } from "@/components/ui/password-input";
import { AuthShell } from "@/components/auth-shell";
import { useAuth } from "@/hooks/use-auth";
import { toast } from "@/hooks/use-toast";
import { ApiError } from "@/lib/api-client";

export default function RegisterPage() {
  const { register } = useAuth();
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await register(email, password);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Error inesperado";
      toast({
        title: "No se pudo crear la cuenta",
        description:
          msg === "Email ya registrado"
            ? "Ese correo ya tiene una cuenta. Intenta iniciar sesión."
            : msg,
        variant: "destructive",
      });
      setSubmitting(false);
    }
  }

  return (
    <AuthShell>
      <div className="mb-7">
        <h1 className="text-[1.75rem] font-medium leading-tight tracking-tight text-foreground">
          Crea tu cuenta
        </h1>
        <p className="mt-1.5 text-sm text-muted-foreground">
          Regístrate para empezar a verificar PDAs en segundos.
        </p>
      </div>

      <form onSubmit={onSubmit} className="space-y-5">
        <div className="space-y-1.5">
          <Label htmlFor="email">Correo institucional</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="tu@correo.com"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Contraseña</Label>
          <PasswordInput
            id="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <p className="text-[0.7rem] text-muted-foreground">Mínimo 8 caracteres.</p>
        </div>
        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
          Crear cuenta
        </Button>
      </form>

      <div className="mt-7 text-sm text-muted-foreground">
        ¿Ya tienes cuenta?{" "}
        <Link
          href="/login"
          className="text-foreground underline underline-offset-[3px] decoration-foreground/30 hover:decoration-foreground"
        >
          Inicia sesión
        </Link>
      </div>
    </AuthShell>
  );
}
