import { useState } from "react";
import { Link } from "react-router-dom";
import { Check, X } from "lucide-react";
import { amountCanonicalLabels, marketplaceCodeLabels } from "@/lib/labels";
import { formatSignedPaise } from "@/lib/money";
import { formatDateIST } from "@/lib/date";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Textarea } from "@/components/ui/Textarea";
import { useReviewAnomaly } from "@/api/mocks/reconciliation";
import { useToast } from "@/components/ui/Toast";
import { AnomalyReviewBadge } from "./AnomalyReviewBadge";
import type { AnomalyLineItem } from "@/api/mocks/fixtureTypes";

export function AnomalyQueueTable({ items }: { items: AnomalyLineItem[] }) {
  const reviewAnomaly = useReviewAnomaly();
  const { push } = useToast();
  const [disputeTarget, setDisputeTarget] = useState<AnomalyLineItem | null>(null);
  const [note, setNote] = useState("");

  const handleAccept = async (item: AnomalyLineItem) => {
    try {
      await reviewAnomaly.mutateAsync({ id: item.id, status: "ACCEPTED" });
      push("Marked as accepted.");
    } catch {
      push("Couldn't save that — try again.", "danger");
    }
  };

  const submitDispute = async () => {
    if (!disputeTarget) return;
    try {
      await reviewAnomaly.mutateAsync({ id: disputeTarget.id, status: "DISPUTED", note: note.trim() || null });
      push("Marked as disputed.");
      setDisputeTarget(null);
      setNote("");
    } catch {
      push("Couldn't save that — try again.", "danger");
    }
  };

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-border text-sm text-muted-foreground">
              <th className="py-2.5 pl-5 pr-3 font-medium">Order</th>
              <th className="px-3 py-2.5 font-medium">Marketplace</th>
              <th className="px-3 py-2.5 font-medium">Fee type</th>
              <th className="px-3 py-2.5 text-right font-medium">Expected</th>
              <th className="px-3 py-2.5 text-right font-medium">Actual</th>
              <th className="px-3 py-2.5 text-right font-medium">Deviation</th>
              <th className="px-3 py-2.5 font-medium">Status</th>
              <th className="py-2.5 pl-3 pr-5 font-medium">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b border-border last:border-0 hover:bg-muted/50">
                <td className="py-3 pl-5 pr-3">
                  {item.order_id ? (
                    <Link to={`/orders/${item.order_id}`} className="font-medium text-primary hover:underline">
                      {item.marketplace_order_id}
                    </Link>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </td>
                <td className="px-3 py-3">
                  <Badge tone="info">{marketplaceCodeLabels[item.marketplace_code]}</Badge>
                </td>
                <td className="px-3 py-3 text-base text-muted-foreground">
                  {amountCanonicalLabels[item.amount_canonical]}
                </td>
                <td className="px-3 py-3 text-right text-base tabular-nums text-muted-foreground">
                  {formatSignedPaise(item.expected_amount_paise)}
                </td>
                <td className="px-3 py-3 text-right text-base tabular-nums font-medium text-foreground">
                  {formatSignedPaise(item.amount_value_paise)}
                </td>
                <td className="px-3 py-3 text-right text-base tabular-nums font-medium text-danger">
                  {formatSignedPaise(item.deviation_paise)}
                </td>
                <td className="px-3 py-3">
                  <AnomalyReviewBadge status={item.review_status} />
                </td>
                <td className="py-3 pl-3 pr-5">
                  {item.review_status === "PENDING" ? (
                    <div className="flex items-center justify-end gap-1.5">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleAccept(item)}
                        loading={reviewAnomaly.isPending}
                        icon={<Check className="size-3.5" aria-hidden />}
                      >
                        Accept
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setDisputeTarget(item)}
                        icon={<X className="size-3.5" aria-hidden />}
                      >
                        Dispute
                      </Button>
                    </div>
                  ) : (
                    <span className="block text-right text-sm text-muted-foreground">{formatDateIST(item.posted_date)}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Dialog
        open={Boolean(disputeTarget)}
        onClose={() => setDisputeTarget(null)}
        title="Dispute this fee"
        footer={
          <>
            <Button variant="secondary" onClick={() => setDisputeTarget(null)} disabled={reviewAnomaly.isPending}>
              Cancel
            </Button>
            <Button variant="danger" onClick={submitDispute} loading={reviewAnomaly.isPending}>
              Submit dispute
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          {disputeTarget && (
            <p className="text-base text-muted-foreground">
              {disputeTarget.marketplace_order_id} — {amountCanonicalLabels[disputeTarget.amount_canonical]} charged{" "}
              {formatSignedPaise(disputeTarget.amount_value_paise)}, expected{" "}
              {formatSignedPaise(disputeTarget.expected_amount_paise)}.
            </p>
          )}
          <Textarea
            label="Note for this dispute"
            helperText="Optional — helps when you follow up with the marketplace"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>
      </Dialog>
    </>
  );
}
