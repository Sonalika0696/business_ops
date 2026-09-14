import { Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";
import type { SettlementStatus } from "@/api/types";

const steps: { status: SettlementStatus; label: string }[] = [
  { status: "UPLOADED", label: "Uploaded" },
  { status: "PARSING", label: "Parsing rows" },
  { status: "PARSED", label: "Parsed" },
  { status: "RECONCILING", label: "Reconciling" },
  { status: "RECONCILED", label: "Reconciled" },
];

const order = steps.map((s) => s.status);

export function ProcessingSteps({ status }: { status: SettlementStatus }) {
  const currentIndex = order.indexOf(status);

  return (
    <ol className="flex flex-col gap-0">
      {steps.map((step, index) => {
        const isDone = currentIndex > index;
        const isCurrent = currentIndex === index;
        const isPending = currentIndex < index;

        return (
          <li key={step.status} className="flex gap-3">
            <div className="flex flex-col items-center">
              <span
                className={cn(
                  "flex size-7 shrink-0 items-center justify-center rounded-full text-sm font-semibold",
                  isDone && "bg-success text-success-foreground",
                  isCurrent && "bg-primary text-primary-foreground",
                  isPending && "bg-muted text-muted-foreground",
                )}
              >
                {isDone ? (
                  <Check className="size-4" aria-hidden />
                ) : isCurrent ? (
                  <Loader2 className="size-4 animate-spin" aria-hidden />
                ) : (
                  index + 1
                )}
              </span>
              {index < steps.length - 1 && (
                <span className={cn("h-8 w-0.5", isDone ? "bg-success" : "bg-border")} aria-hidden />
              )}
            </div>
            <p
              className={cn(
                "pb-8 pt-1 text-base font-medium",
                isCurrent ? "text-foreground" : isDone ? "text-foreground" : "text-muted-foreground",
              )}
            >
              {step.label}
            </p>
          </li>
        );
      })}
    </ol>
  );
}
