import { PackageOpen, ScrollText } from "lucide-react";
import { Card, CardBody } from "@/components/ui/Card";
import { AsyncState } from "@/components/ui/AsyncState";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatCard } from "@/components/ui/StatCard";
import { MockDataBanner } from "@/components/ui/MockDataBanner";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { useFileClaim, useReturnsQueue } from "@/api/mocks/returns";
import { ReturnStatusBadge, ClaimStatusBadge } from "@/components/reconciliation/ReturnStatusBadges";
import { marketplaceCodeLabels, returnReasonLabels } from "@/lib/labels";
import { formatPaise } from "@/lib/money";
import { formatDateIST } from "@/lib/date";
import { ApiError } from "@/api/client";

export function ReturnsQueuePage() {
  const returnsQuery = useReturnsQueue();
  const fileClaim = useFileClaim();
  const { push } = useToast();
  const items = returnsQuery.data ?? [];

  const uncredited = items.filter((r) => r.refund_amount_credited_paise < r.refund_amount_expected_paise);
  const uncreditedTotal = uncredited.reduce(
    (sum, r) => sum + (r.refund_amount_expected_paise - r.refund_amount_credited_paise),
    0,
  );
  const claimable = uncredited.filter((r) => r.claim_status === "NOT_CLAIMED").length;

  const handleFileClaim = async (id: string) => {
    try {
      await fileClaim.mutateAsync({ id });
      push("Claim filed.");
    } catch (err) {
      push(err instanceof ApiError ? err.message : "Couldn't file that claim.", "danger");
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="font-heading text-2xl font-semibold text-foreground">Un-credited refunds</h1>
        <p className="mt-1 text-base text-muted-foreground">
          Returns where the marketplace hasn't credited what it owes you back yet.
        </p>
      </div>

      <MockDataBanner>
        This is the thin Returns slice the reconciliation story needs (frontend/PLAN.md Phase 2, item 5) — figures are
        fixture data until the Returns service lands. Full open-returns dashboard, RTO tracker and claim workspace are
        Phase 5 product work, not part of this slice.
      </MockDataBanner>

      <AsyncState
        isLoading={returnsQuery.isLoading}
        isError={returnsQuery.isError}
        error={returnsQuery.error}
        onRetry={() => returnsQuery.refetch()}
      >
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <StatCard index={0} label="Un-credited amount" value={formatPaise(uncreditedTotal)} tone="danger" />
          <StatCard index={1} label="Returns affected" value={uncredited.length} />
          <StatCard index={2} label="Not yet claimed" value={claimable} tone={claimable > 0 ? "danger" : "success"} />
        </div>

        <Card>
          <CardBody className="p-0">
            <AsyncState
              isLoading={false}
              isError={false}
              isEmpty={items.length === 0}
              emptyState={
                <EmptyState
                  icon={<PackageOpen className="size-6" aria-hidden />}
                  title="No returns on file"
                  description="Un-credited refunds will show up here once returns start coming in."
                />
              }
            >
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-border text-sm text-muted-foreground">
                      <th className="py-2.5 pl-5 pr-3 font-medium">Order</th>
                      <th className="px-3 py-2.5 font-medium">Marketplace</th>
                      <th className="px-3 py-2.5 font-medium">Reason</th>
                      <th className="px-3 py-2.5 font-medium">Status</th>
                      <th className="px-3 py-2.5 text-right font-medium">Expected</th>
                      <th className="px-3 py-2.5 text-right font-medium">Credited</th>
                      <th className="px-3 py-2.5 font-medium">Claim</th>
                      <th className="py-2.5 pl-3 pr-5 font-medium">
                        <span className="sr-only">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item) => {
                      const gap = item.refund_amount_expected_paise - item.refund_amount_credited_paise;
                      return (
                        <tr key={item.id} className="border-b border-border last:border-0 hover:bg-muted/50">
                          <td className="py-3 pl-5 pr-3 font-medium text-foreground">{item.marketplace_order_id}</td>
                          <td className="px-3 py-3">
                            <Badge tone="info">{marketplaceCodeLabels[item.marketplace_code]}</Badge>
                          </td>
                          <td className="px-3 py-3 text-base text-muted-foreground">
                            {returnReasonLabels[item.return_reason]}
                          </td>
                          <td className="px-3 py-3">
                            <ReturnStatusBadge status={item.return_status} />
                          </td>
                          <td className="px-3 py-3 text-right text-base tabular-nums text-muted-foreground">
                            {formatPaise(item.refund_amount_expected_paise)}
                          </td>
                          <td
                            className={`px-3 py-3 text-right text-base tabular-nums font-medium ${
                              gap > 0 ? "text-danger" : "text-success"
                            }`}
                          >
                            {formatPaise(item.refund_amount_credited_paise)}
                          </td>
                          <td className="px-3 py-3">
                            <ClaimStatusBadge status={item.claim_status} />
                          </td>
                          <td className="py-3 pl-3 pr-5 text-right">
                            {gap > 0 && item.claim_status === "NOT_CLAIMED" && (
                              <Button
                                variant="secondary"
                                size="sm"
                                icon={<ScrollText className="size-3.5" aria-hidden />}
                                loading={fileClaim.isPending}
                                onClick={() => handleFileClaim(item.id)}
                              >
                                File claim
                              </Button>
                            )}
                            {item.claim_window_expires && item.claim_status === "NOT_CLAIMED" && (
                              <p className="mt-1 text-xs text-muted-foreground">
                                Window closes {formatDateIST(item.claim_window_expires)}
                              </p>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </AsyncState>
          </CardBody>
        </Card>
      </AsyncState>
    </div>
  );
}
