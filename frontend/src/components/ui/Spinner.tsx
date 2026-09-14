import { Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";

export function Spinner({ className, label = "Loading" }: { className?: string; label?: string }) {
  return (
    <span role="status" className="inline-flex items-center">
      <Loader2 className={cn("animate-spin text-primary", className ?? "size-5")} aria-hidden />
      <span className="sr-only">{label}</span>
    </span>
  );
}
