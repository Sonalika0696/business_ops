import { CircleCheck, CircleX, Loader2, Clock, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import type { SettlementStatus, MatchStatus } from "@/api/types";

const statusConfig: Record<SettlementStatus, { label: string; tone: "success" | "warning" | "danger" | "info" | "neutral"; icon: React.ReactNode }> = {
  UPLOADED: { label: "Uploaded", tone: "neutral", icon: <Clock className="size-3.5" aria-hidden /> },
  PARSING: { label: "Parsing", tone: "info", icon: <Loader2 className="size-3.5 animate-spin" aria-hidden /> },
  PARSED: { label: "Parsed", tone: "info", icon: <RefreshCw className="size-3.5" aria-hidden /> },
  RECONCILING: { label: "Reconciling", tone: "info", icon: <Loader2 className="size-3.5 animate-spin" aria-hidden /> },
  RECONCILED: { label: "Reconciled", tone: "success", icon: <CircleCheck className="size-3.5" aria-hidden /> },
  FAILED: { label: "Failed", tone: "danger", icon: <CircleX className="size-3.5" aria-hidden /> },
};

export function SettlementStatusBadge({ status }: { status: SettlementStatus }) {
  const config = statusConfig[status];
  return (
    <Badge tone={config.tone} icon={config.icon}>
      {config.label}
    </Badge>
  );
}

const matchStatusConfig: Record<MatchStatus, { label: string; tone: "success" | "warning" | "danger" | "neutral" }> = {
  MATCHED_EXACT: { label: "Matched", tone: "success" },
  MATCHED_FUZZY: { label: "Matched (fuzzy)", tone: "success" },
  UNMATCHED: { label: "Unmatched", tone: "danger" },
  ADJUSTMENT: { label: "Adjustment", tone: "neutral" },
};

export function MatchStatusBadge({ status }: { status: MatchStatus }) {
  const config = matchStatusConfig[status];
  return <Badge tone={config.tone}>{config.label}</Badge>;
}
