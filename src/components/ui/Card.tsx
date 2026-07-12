import { cn } from "@/lib/utils";
import type { HTMLAttributes } from "react";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("glass rounded-3xl p-5", className)} {...props} />;
}

export function CardStrong({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("glass-strong rounded-3xl p-5", className)} {...props} />;
}
