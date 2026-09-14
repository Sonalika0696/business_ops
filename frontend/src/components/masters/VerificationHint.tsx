import { CircleCheck, CircleX } from "lucide-react";
import { cn } from "@/lib/cn";
import type { VerificationResult } from "@/lib/verification";

/**
 * Inline offline verification feedback — real algorithms/reference data
 * (see lib/verification.ts), not a live external call, so there's no
 * loading/degraded-service state to render: format+checksum either compute
 * or they don't. Shown only once the user has typed something (empty
 * fields aren't "invalid", they're just optional).
 */
export function VerificationHint({ result, action }: { result: VerificationResult | null; action?: React.ReactNode }) {
  if (!result) return null;

  return (
    <div
      className={cn(
        "mt-1.5 flex items-start gap-1.5 text-sm",
        result.valid ? "text-success" : "text-muted-foreground",
      )}
      role={result.valid ? "status" : undefined}
    >
      {result.valid ? (
        <CircleCheck className="mt-0.5 size-3.5 shrink-0" aria-hidden />
      ) : (
        <CircleX className="mt-0.5 size-3.5 shrink-0 text-muted-foreground/70" aria-hidden />
      )}
      <span className="flex-1">{result.valid ? (result.detail ?? "Looks valid") : result.reason}</span>
      {result.valid && action}
    </div>
  );
}
