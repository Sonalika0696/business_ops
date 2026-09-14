import { Badge } from "@/components/ui/Badge";
import type { ClaimStatus, ReturnStatus } from "@/api/mocks/fixtureTypes";

const returnStatusConfig: Record<ReturnStatus, { label: string; tone: "success" | "warning" | "danger" | "info" | "neutral" }> = {
  INITIATED: { label: "Initiated", tone: "neutral" },
  IN_TRANSIT: { label: "In transit", tone: "info" },
  RECEIVED: { label: "Received", tone: "info" },
  INSPECTED: { label: "Inspected", tone: "warning" },
  REFUNDED: { label: "Refunded", tone: "success" },
  REIMBURSED: { label: "Reimbursed", tone: "success" },
  DISPUTED: { label: "Disputed", tone: "danger" },
};

export function ReturnStatusBadge({ status }: { status: ReturnStatus }) {
  const c = returnStatusConfig[status];
  return <Badge tone={c.tone}>{c.label}</Badge>;
}

const claimStatusConfig: Record<ClaimStatus, { label: string; tone: "success" | "warning" | "danger" | "neutral" }> = {
  NOT_CLAIMED: { label: "Not claimed", tone: "neutral" },
  CLAIMED: { label: "Claimed", tone: "warning" },
  APPROVED: { label: "Approved", tone: "success" },
  REJECTED: { label: "Rejected", tone: "danger" },
};

export function ClaimStatusBadge({ status }: { status: ClaimStatus }) {
  const c = claimStatusConfig[status];
  return <Badge tone={c.tone}>{c.label}</Badge>;
}
