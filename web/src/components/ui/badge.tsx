import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/*
 * Badge institucional: tipografia uppercase pequena con tracking amplio.
 * Sin halos ni glows. Borde 1px y fill traslucido del color de su rol.
 * Variants: success (musgo), destructive (crimson), warning (gold), default
 * (navy ink), secondary (gris papel), outline (transparente).
 */
const badgeVariants = cva(
  [
    "inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5",
    "text-[0.625rem] font-medium uppercase tracking-institutional leading-none",
    "transition-colors",
  ].join(" "),
  {
    variants: {
      variant: {
        default:
          "border-foreground/20 bg-foreground/[0.04] text-foreground",
        secondary:
          "border-border-strong bg-paper-warm text-muted-foreground",
        destructive:
          "border-destructive/30 bg-destructive/[0.08] text-destructive",
        success:
          "border-success/30 bg-success/[0.08] text-success",
        warning:
          "border-gold/40 bg-gold/[0.08] text-gold",
        outline:
          "border-border-strong bg-transparent text-muted-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
