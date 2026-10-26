import { Link } from "react-router-dom";
import { cn } from "@/lib/cn";

export function BrandMark({ inverted = false, to = "/", size = "md" }: { inverted?: boolean; to?: string; size?: "sm" | "md" | "lg" }) {
  const px = size === "lg" ? "h-14 w-14" : size === "sm" ? "h-8 w-8" : "h-10 w-10";
  const type = size === "lg" ? "text-2xl" : size === "sm" ? "text-sm" : "text-lg";
  return (
    <Link to={to} className="inline-flex items-center gap-3">
      <img src={`${import.meta.env.BASE_URL}logo.png`} alt="ApproveFlow" className={cn(px, "rounded-xl object-contain")} />
      <span className={cn("font-extrabold tracking-tight", type, inverted ? "text-white" : "text-ink")}>ApproveFlow</span>
    </Link>
  );
}
