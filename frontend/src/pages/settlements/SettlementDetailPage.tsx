import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, FileWarning, Inbox, ListChecks } from "lucide-react";
import { Card, CardBody } from "@/components/ui/Card";
import { AsyncState } from "@/components/ui/AsyncState";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatCard } from "@/components/ui/StatCard";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { Tabs } from "@/components/ui/Tabs";
import { Spinner } from "@/components/ui/Spinner";
import { SettlementStatusBadge } from "@/components/settlements/StatusBadge";
import { ProcessingSteps } from "@/components/settlements/ProcessingSteps";
import { LineItemsTable } from "@/components/settlements/LineItemsTable";
import { RejectedRowsPanel } from "@/components/settlements/RejectedRowsPanel";
import { useLineItems, useRejectedRows, useSettlement, isTerminalStatus } from "@/api/settlements";
import { useSettlementProgress } from "@/hooks/useSettlementProgress";
import { formatPaise } from "@/lib/money";
import { formatDateTimeIST, formatDateIST } from "@/lib/date";
import { formatNumber } from "@/lib/number";

type TabKey = "discrepancies" | "all" | "rejected";

export function SettlementDetailPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const [tab, setTab] = useState<TabKey>("discrepancies");

  const reportQuery = useSettlement(reportId, { livePoll: true });
  const report = reportQuery.data;
  const terminal = report ? isTerminalStatus(report.status) : false;
  const rowsReady = report ? report.status !== "UPLOADED" && report.status !== "PARSING" : false;

  useSettlementProgress(reportId, Boolean(reportId) && !terminal);

  const discrepanciesQuery = useLineItems(rowsReady ? reportId : undefined, "UNMATCHED");
  const allItemsQuery = useLineItems(rowsReady && tab === "all" ? reportId : undefined);
  const rejectedRowsQuery = useRejectedRows(rowsReady && tab === "rejected" ? reportId : undefined);

  const tabs = useMemo(
    () => [
      { key: "discrepancies" as const, label: "Discrepancies", count: discrepanciesQuery.data?.total },
      { key: "all" as const, label: "All line items", count: report?.row_count ?? undefined },
      ...(report && report.rejected_row_count > 0
        ? [{ key: "rejected" as const, label: "Rejected rows", count: report.rejected_row_count }]
        : []),
    ],
    [discrepanciesQuery.data?.total, report],
  );

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link
          to="/settlements"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" aria-hidden />
          Settlement history
        </Link>
      </div>

      <AsyncState
        isLoading={reportQuery.isLoading}
        isError={reportQuery.isError}
        error={reportQuery.error}
        onRetry={() => reportQuery.refetch()}
      >
        {report && (
          <>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h1 className="break-words font-heading text-2xl font-semibold text-foreground">
                  {report.original_filename}
                </h1>
                <p className="mt-1 text-base text-muted-foreground">
                  Uploaded {formatDateTimeIST(report.file_uploaded_at)} · Period {formatDateIST(report.period_start)}
                  {" – "}
                  {formatDateIST(report.period_end)}
                </p>
              </div>
              <SettlementStatusBadge status={report.status} />
            </div>

            {!terminal && (
              <Card>
                <CardBody>
                  <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:gap-10">
                    <div className="flex-1">
                      <ProcessingSteps status={report.status} />
                    </div>
                    <div className="flex-1 space-y-3">
                      <ProgressBar indeterminate />
                      <p className="text-base text-muted-foreground">
                        {report.row_count !== null
                          ? `${formatNumber(report.row_count)} rows processed so far…`
                          : "Waiting for processing to begin…"}
                      </p>
                    </div>
                  </div>
                </CardBody>
              </Card>
            )}

            {report.status === "FAILED" && (
              <Card>
                <CardBody>
                  <EmptyState
                    icon={<FileWarning className="size-6" aria-hidden />}
                    title="Processing failed"
                    description={report.error_message ?? "An unexpected error stopped this upload from processing."}
                  />
                </CardBody>
              </Card>
            )}

            {terminal && report.status === "RECONCILED" && (
              <>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
                  <StatCard index={0} label="Gross sales" value={formatPaise(report.total_gross_sales_paise)} />
                  <StatCard index={1} label="Fees" value={formatPaise(report.total_fees_paise)} tone="danger" />
                  <StatCard
                    index={2}
                    label="Taxes deducted"
                    value={formatPaise(report.total_taxes_deducted_paise)}
                    tone="danger"
                  />
                  <StatCard index={3} label="Refunds" value={formatPaise(report.total_returns_refunds_paise)} />
                  <StatCard
                    index={4}
                    label="Reimbursements"
                    value={formatPaise(report.total_reimbursements_paise)}
                    tone="success"
                  />
                  <StatCard
                    index={5}
                    label="Net payout expected"
                    value={formatPaise(report.net_payout_expected_paise)}
                    tone="success"
                  />
                </div>

                <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                  <ListChecks className="size-4" aria-hidden />
                  <span>
                    <span className="font-medium text-foreground">{formatNumber(report.row_count)}</span> rows parsed
                  </span>
                  {report.rejected_row_count > 0 && (
                    <span className="text-danger">
                      · <span className="font-medium">{formatNumber(report.rejected_row_count)}</span> rejected
                    </span>
                  )}
                  <span>
                    · Bank-credited payout and final discrepancy are shown once bank-statement upload lands (Phase 2)
                  </span>
                </div>

                <Card>
                  <Tabs items={tabs} active={tab} onChange={(key) => setTab(key as TabKey)} />
                  <CardBody className="p-0">
                    {tab === "discrepancies" && (
                      <AsyncState
                        isLoading={discrepanciesQuery.isLoading}
                        isError={discrepanciesQuery.isError}
                        error={discrepanciesQuery.error}
                        onRetry={() => discrepanciesQuery.refetch()}
                        isEmpty={discrepanciesQuery.data?.items.length === 0}
                        emptyState={
                          <EmptyState
                            icon={<Inbox className="size-6" aria-hidden />}
                            title="No discrepancies"
                            description="Every settlement line for this report matched an order exactly."
                          />
                        }
                      >
                        <LineItemsTable items={discrepanciesQuery.data?.items ?? []} />
                      </AsyncState>
                    )}
                    {tab === "all" && (
                      <AsyncState
                        isLoading={allItemsQuery.isLoading}
                        isError={allItemsQuery.isError}
                        error={allItemsQuery.error}
                        onRetry={() => allItemsQuery.refetch()}
                        isEmpty={allItemsQuery.data?.items.length === 0}
                        emptyState={
                          <EmptyState icon={<Inbox className="size-6" aria-hidden />} title="No line items" />
                        }
                      >
                        <LineItemsTable items={allItemsQuery.data?.items ?? []} />
                      </AsyncState>
                    )}
                    {tab === "rejected" && (
                      <AsyncState
                        isLoading={rejectedRowsQuery.isLoading}
                        isError={rejectedRowsQuery.isError}
                        error={rejectedRowsQuery.error}
                        onRetry={() => rejectedRowsQuery.refetch()}
                        isEmpty={rejectedRowsQuery.data?.items.length === 0}
                        emptyState={<EmptyState icon={<Inbox className="size-6" aria-hidden />} title="No rejected rows" />}
                      >
                        <RejectedRowsPanel rows={rejectedRowsQuery.data?.items ?? []} />
                      </AsyncState>
                    )}
                  </CardBody>
                </Card>
              </>
            )}

            {reportQuery.isFetching && !terminal && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Spinner className="size-3.5" />
                Watching for updates…
              </div>
            )}
          </>
        )}
      </AsyncState>
    </div>
  );
}
