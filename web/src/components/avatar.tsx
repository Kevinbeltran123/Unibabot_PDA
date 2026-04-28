import * as React from "react";
import { cn } from "@/lib/utils";
import { BrandMark } from "./brand-mark";

/*
 * Avatares para el chat. El asistente reusa el monograma de marca con
 * punto dorado. El usuario es un cuadrado simple con sus iniciales en
 * tipografia sans, fondo paper-warm y borde fino.
 */

export function AssistantAvatar({ className }: { className?: string }) {
  return <BrandMark variant="mono" className={cn("shrink-0", className)} />;
}

export function UserAvatar({
  email,
  className,
}: {
  email?: string | null;
  className?: string;
}) {
  const initials = React.useMemo(() => {
    if (!email) return "?";
    const local = email.split("@")[0];
    const parts = local.split(/[._-]/);
    if (parts.length >= 2 && parts[0] && parts[1]) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return local.slice(0, 2).toUpperCase();
  }, [email]);

  return (
    <span
      aria-hidden
      className={cn(
        "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md",
        "bg-paper-warm border border-border text-[0.7rem] font-medium tracking-tight text-foreground",
        className,
      )}
    >
      {initials}
    </span>
  );
}
