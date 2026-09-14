import { Inbox, ShieldCheck } from "lucide-react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { AsyncState } from "@/components/ui/AsyncState";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatCard } from "@/components/ui/StatCard";
import { MockDataBanner } from "@/components/ui/MockDataBanner";
import { ExpectedActualChart } from "@/components/reconciliation/ExpectedActualChart";
import { AnomalyQueueTable } from "@/components/reconciliation/AnomalyQueueTable";
import { useAnomalyQueue, useReconciliationSummary } from "@/api/mocks/reconciliation";
import { formatPaise } from "@/lib/money";
import { formatDateIST } from "@/lib/date";

export function ReconciliationDashboardPage() {
  const summaryQuery = useReconciliationSummary();
  const anomaliesQuery = useAnomalyQueue();
  const summary = summaryQuery.data;
  const anomalies = anomaliesQuery.data ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="font-heading text-2xl font-semibold text-foreground">Reconciliation dashboard</h1>
        <p className="mt-1 text-base text-muted-foreground">
          This period's expected payout versus what actually settled, and every fee that needs a decision.
        </p>
      </div>

      <MockDataBanner>
        Expected-payout figures here are illustrative — they'll be computed by the FeeSchedule and reconciliation
        engine once that lands (see <span className="font-medium">TRACKING.md</span>'s Phase 2 row). Discrepancies
        and anomalies shown are fixture data, not live matches.
      </MockDataBanner>

      <AsyncState
        isLoading={summaryQuery.isLoading}
        isError={summaryQuery.isError}
        error={summaryQuery.error}
        onRetry={() => summaryQuery.refetch()}
      >
        {summary && (
          <>
            <p className="text-sm text-muted-foreground">
              Period {formatDateIST(summary.period_start)} – {formatDateIST(summary.period_end)}
            </p>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatCard index={0} label="Expected payout" value={formatPaise(summary.expected_payout_paise)} />
              <StatCard
                index={1}
                label="Actual payout"
                value={formatPaise(summary.actual_payout_paise)}
                tone={summary.actual_payout_paise < summary.expected_payout_paise ? "danger" : "success"}
              />
              <StatCard
                index={2}
                label="Discrepancy"
                value={formatPaise(summary.discrepancy_paise)}
                tone={summary.discrepancy_paise < 0 ? "danger" : "success"}
                hint="Bank-credited payout not available until bank-statement upload lands"
              />
              <StatCard
                index={3}
                label="Pending review"
                value={summary.pending_review_count}
                tone={summary.pending_review_count > 0 ? "danger" : "success"}
              />
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Expected vs. actual by marketplace</CardTitle>
              </CardHeader>
              <CardBody>
                <ExpectedActualChart rows={summary.by_marketplace} />
              </CardBody>
            </Card>
          </>
        )}
      </AsyncState>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <ShieldCheck className="size-5 text-primary" aria-hidden />
            <CardTitle>Anomaly review queue</CardTitle>
          </div>
        </CardHeader>
        <CardBody className="p-0">
          <AsyncState
            isLoading={anomaliesQuery.isLoading}
            isError={anomaliesQuery.isError}
            error={anomaliesQuery.error}
            onRetry={() => anomaliesQuery.refetch()}
            isEmpty={anomalies.length === 0}
            emptyState={
              <EmptyState
                icon={<Inbox className="size-6" aria-hidden />}
                title="No anomalies to review"
                description="Every settled fee matched what was expected this period."
              />
            }
          >
            <AnomalyQueueTable items={anomalies} />
          </AsyncState>
        </CardBody>
      </Card>
    </div>
  );
}
