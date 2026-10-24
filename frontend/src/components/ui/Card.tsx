import { cn } from "@/lib/cn";
import { motion } from "framer-motion";
import type { ReactNode } from "react";

export function Card({ className, children }: { className?: string; children?: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -3 }}
      className={cn("rounded-card border border-line bg-white p-5 shadow-card", className)}
    >
      {children}
    </motion.div>
  );
}
