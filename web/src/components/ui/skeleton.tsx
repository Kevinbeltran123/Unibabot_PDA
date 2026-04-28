import { cn } from "@/lib/utils";

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-sm bg-paper-warm relative overflow-hidden",
        "before:absolute before:inset-0 before:-translate-x-full",
        "before:bg-gradient-to-r before:from-transparent before:via-paper-tint before:to-transparent",
        "before:animate-[shimmer_1.4s_infinite]",
        className,
      )}
      style={{ animationName: "shimmer" }}
      {...props}
    />
  );
}
