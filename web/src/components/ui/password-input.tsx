"use client";

import * as React from "react";
import { Eye, EyeOff } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

/*
 * Campo de contraseña con toggle de visibilidad. Muestra un placeholder
 * con puntos suspensivos para que el campo sea visualmente identificable
 * antes de tipear. El icono de ojo a la derecha alterna entre type=password
 * y type=text. La pulsación no envía el formulario (type="button").
 */

export type PasswordInputProps = Omit<
  React.InputHTMLAttributes<HTMLInputElement>,
  "type"
>;

export const PasswordInput = React.forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ className, placeholder = "••••••••", ...props }, ref) => {
    const [visible, setVisible] = React.useState(false);

    return (
      <div className="relative">
        <Input
          ref={ref}
          type={visible ? "text" : "password"}
          placeholder={placeholder}
          className={cn("pr-8", className)}
          {...props}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
          aria-pressed={visible}
          tabIndex={-1}
          className={cn(
            "absolute right-0 top-1/2 -translate-y-1/2 p-1.5 rounded-sm",
            "text-muted-foreground hover:text-foreground transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          )}
        >
          {visible ? (
            <EyeOff className="h-3.5 w-3.5" strokeWidth={1.75} />
          ) : (
            <Eye className="h-3.5 w-3.5" strokeWidth={1.75} />
          )}
        </button>
      </div>
    );
  },
);
PasswordInput.displayName = "PasswordInput";
