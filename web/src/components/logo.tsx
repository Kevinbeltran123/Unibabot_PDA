import * as React from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";

interface Props {
  className?: string;
  title?: string;
}

export function Logo({ className, title }: Props) {
  return (
    <Image
      src="/unibague-escudo.jpg"
      alt={title || "Universidad de Ibagué"}
      width={1015}
      height={982}
      className={cn("object-contain", className)}
      priority
    />
  );
}
