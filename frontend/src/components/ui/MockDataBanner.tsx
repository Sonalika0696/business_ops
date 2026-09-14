import { FlaskConical } from "lucide-react";

/**
 * ARCHITECTURE.md §11: "fail closed on money" — never let a fabricated
 * number look authoritative. Every Phase 2 screen still running on fixture
 * data (per TRACKING.md's Phase 2 row) carries this so the figures are
 * never mistaken for the real FeeSchedule/reconciliation engine output.
 * Drop this the moment TRACKING.md marks the backing capability live.
 */
export function MockDataBanner({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2.5 rounded-md border border-info/20 bg-info-soft px-4 py-3 text-sm text-foreground">
      <FlaskConical className="mt-0.5 size-4 shrink-0 text-info" aria-hidden />
      <p>{children}</p>
    </div>
  );
}
