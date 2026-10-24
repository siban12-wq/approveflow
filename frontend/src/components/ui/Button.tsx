import { cn } from "@/lib/cn";
import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "danger" | "outline";
  size?: "sm" | "md";
};

export function Button({ variant = "primary", size = "md", className, ...props }: Props) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-2xl font-medium transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-50",
        size === "sm" ? "px-3 py-1.5 text-sm" : "px-4 py-2.5 text-sm",
        variant === "primary" && "bg-ink text-white shadow-card hover:shadow-lift",
        variant === "ghost" && "bg-white text-ink hover:bg-canvas",
        variant === "outline" && "border border-line bg-white text-ink hover:border-indigo/40",
        variant === "danger" && "bg-rose-600 text-white",
        className,
      )}
      {...props}
    />
  );
}
