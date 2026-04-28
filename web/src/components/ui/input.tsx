import * as React from "react";
import { cn } from "@/lib/utils";

const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, type, ...props }, ref) => (
  <input
    type={type}
    className={cn(
      "flex h-9 w-full bg-transparent px-3 py-2 text-sm text-foreground",
      "border-0 border-b border-border-strong rounded-none",
      "transition-[border-color] duration-150",
      "placeholder:text-muted-foreground/70 placeholder:font-normal",
      "focus:outline-none focus:border-foreground",
      "disabled:cursor-not-allowed disabled:opacity-50",
      "file:border-0 file:bg-transparent file:text-sm file:font-medium",
      className,
    )}
    ref={ref}
    {...props}
  />
));
Input.displayName = "Input";

export { Input };
