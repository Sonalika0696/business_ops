import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { History, UploadCloud } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { AsyncState } from "@/components/ui/AsyncState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Pagination } from "@/components/ui/Pagination";
import { Button } from "@/components/ui/Button";
import { SettlementStatusBadge } from "@/components/settlements/StatusBadge";
import { useMarketplaceAccounts, useMarketplaces } from "@/api/marketplaceAccounts";
import { useSettlements } from "@/api/settlements";
import { formatDateTimeIST } from "@/lib/date";
import { formatNumber } from "@/lib/number";

const PAGE_SIZE = 20;

export function SettlementsHistoryPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const settlementsQuery = useSettlements(page);
  const accountsQuery = useMarketplaceAccounts();
  const marketplacesQuery = useMarketplaces();

  const accountLabelById = new Map(
    (accountsQuery.data?.items ?? []).map((account) => {
      const marketplace = (marketplacesQuery.data?.items ?? []).find((m) => m.id === account.marketplace_id);
      return [account.id, `${marketplace?.display_name ?? "Marketplace"} — ${account.merchant_id_on_platform}`];
    }),
  );

  const items = settlementsQuery.data?.items ?? [];
  const total = settlementsQuery.data?.total ?? 0;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-heading text-2xl font-semibold text-foreground">Settlement history</h1>
          <p className="mt-1 text-base text-muted-foreground">Every settlement file you've uploaded and its status.</p>
        </div>
        <Button onClick={() => navigate("/upload")} icon={<UploadCloud className="size-4" aria-hidden />}>
          Upload settlement
        </Button>
      </div>

      <Card>
        <AsyncState
          isLoading={settlementsQuery.isLoading}
          isError={settlementsQuery.isError}
          error={settlementsQuery.error}
          onRetry={() => settlementsQuery.refetch()}
          isEmpty={items.length === 0}
          emptyState={
            <EmptyState
              icon={<History className="size-6" aria-hidden />}
              title="No settlements uploaded yet"
              description="Once you upload a settlement file, it'll show up here with its processing status."
              action={<Button onClick={() => navigate("/upload")}>Upload your first settlement</Button>}
            />
          }
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-border text-sm text-muted-foreground">
                  <th className="py-2.5 pl-5 pr-3 font-medium">File</th>
                  <th className="px-3 py-2.5 font-medium">Marketplace account</th>
                  <th className="px-3 py-2.5 font-medium">Uploaded</th>
                  <th className="px-3 py-2.5 font-medium">Rows</th>
                  <th className="py-2.5 pl-3 pr-5 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {items.map((report) => (
                  <tr
                    key={report.id}
                    className="cursor-pointer border-b border-border last:border-0 hover:bg-muted/50"
                    onClick={() => navigate(`/settlements/${report.id}`)}
                  >
                    <td className="py-3 pl-5 pr-3">
                      <Link
                        to={`/settlements/${report.id}`}
                        onClick={(e) => e.stopPropagation()}
                        className="text-base font-medium text-primary hover:underline"
                      >
                        {report.original_filename}
                      </Link>
                    </td>
                    <td className="px-3 py-3 text-base text-muted-foreground">
                      {accountLabelById.get(report.seller_marketplace_account_id) ?? "—"}
                    </td>
                    <td className="px-3 py-3 text-base text-muted-foreground">
                      {formatDateTimeIST(report.file_uploaded_at)}
                    </td>
                    <td className="px-3 py-3 text-base tabular-nums text-muted-foreground">
                      {report.row_count !== null ? formatNumber(report.row_count) : "—"}
                      {report.rejected_row_count > 0 && (
                        <span className="ml-1.5 text-danger">({formatNumber(report.rejected_row_count)} rejected)</span>
                      )}
                    </td>
                    <td className="py-3 pl-3 pr-5">
                      <SettlementStatusBadge status={report.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {total > 0 && <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />}
        </AsyncState>
      </Card>
    </div>
  );
}
