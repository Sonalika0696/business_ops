import { CircleCheck, CircleX, CircleDashed } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import type { AnomalyReviewStatus } from "@/api/mocks/fixtureTypes";

const config: Record<AnomalyReviewStatus, { label: string; tone: "success" | "danger" | "warning"; icon: React.ReactNode }> = {
  PENDING: { label: "Pending review", tone: "warning", icon: <CircleDashed className="size-3.5" aria-hidden /> },
  ACCEPTED: { label: "Accepted", tone: "success", icon: <CircleCheck className="size-3.5" aria-hidden /> },
  DISPUTED: { label: "Disputed", tone: "danger", icon: <CircleX className="size-3.5" aria-hidden /> },
};

export function AnomalyReviewBadge({ status }: { status: AnomalyReviewStatus }) {
  const c = config[status];
  return (
    <Badge tone={c.tone} icon={c.icon}>
      {c.label}
    </Badge>
  );
}
