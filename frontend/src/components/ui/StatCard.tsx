import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/cn";

export function StatCard({
  label,
  value,
  tone = "neutral",
  hint,
  index = 0,
}: {
  label: string;
  value: ReactNode;
  tone?: "neutral" | "success" | "danger";
  hint?: string;
  index?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: index * 0.04, ease: [0.16, 1, 0.3, 1] }}
      whileHover={{ y: -2 }}
      className="rounded-md border border-border bg-surface p-4 shadow-card transition-shadow duration-150 hover:shadow-raised"
    >
      <p className="text-sm font-medium text-muted-foreground">{label}</p>
      <p
        className={cn(
          "mt-1.5 whitespace-nowrap text-2xl font-semibold tabular-nums font-heading",
          tone === "success" && "text-success",
          tone === "danger" && "text-danger",
          tone === "neutral" && "text-foreground",
        )}
      >
        {value}
      </p>
      {hint && <p className="mt-1 text-sm text-muted-foreground">{hint}</p>}
    </motion.div>
  );
}
