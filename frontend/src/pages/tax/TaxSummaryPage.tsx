import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { AsyncState } from "@/components/ui/AsyncState";
import { StatCard } from "@/components/ui/StatCard";
import { MockDataBanner } from "@/components/ui/MockDataBanner";
import { Badge } from "@/components/ui/Badge";
import { useTaxSummary } from "@/api/mocks/tax";
import { marketplaceCodeLabels } from "@/lib/labels";
import { formatPaise } from "@/lib/money";
import { formatDateIST } from "@/lib/date";

export function TaxSummaryPage() {
  const taxQuery = useTaxSummary();
  const summary = taxQuery.data;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="font-heading text-2xl font-semibold text-foreground">TCS &amp; TDS</h1>
        <p className="mt-1 text-base text-muted-foreground">
          Tax deducted at source by each marketplace — what it takes off your net payout.
        </p>
      </div>

      <MockDataBanner>
        Figures are fixture data until tax accumulation (frontend/PLAN.md Phase 2, item 6) lands. This view covers
        only what feeds margin/net-payout — GSTR-1 helper, compliance calendar and threshold warnings are Phase 5
        product work.
      </MockDataBanner>

      <AsyncState isLoading={taxQuery.isLoading} isError={taxQuery.isError} error={taxQuery.error} onRetry={() => taxQuery.refetch()}>
        {summary && (
          <>
            <p className="text-sm text-muted-foreground">
              Period {formatDateIST(summary.period_start)} – {formatDateIST(summary.period_end)}
            </p>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <StatCard index={0} label="TCS deducted" value={formatPaise(summary.total_tcs_paise)} tone="danger" />
              <StatCard index={1} label="TDS deducted" value={formatPaise(summary.total_tds_paise)} tone="danger" />
              <StatCard index={2} label="Net of tax" value={formatPaise(summary.net_of_tax_paise)} tone="success" />
            </div>

            <Card>
              <CardHeader>
                <CardTitle>By marketplace</CardTitle>
              </CardHeader>
              <CardBody className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="border-b border-border text-sm text-muted-foreground">
                        <th className="py-2.5 pl-5 pr-3 font-medium">Marketplace</th>
                        <th className="px-3 py-2.5 text-right font-medium">Gross sales</th>
                        <th className="px-3 py-2.5 text-right font-medium">TCS (0.5%)</th>
                        <th className="px-3 py-2.5 text-right font-medium">TDS (0.1%)</th>
                        <th className="py-2.5 pl-3 pr-5 text-right font-medium">Net of tax</th>
                      </tr>
                    </thead>
                    <tbody>
                      {summary.by_marketplace.map((row) => (
                        <tr key={row.marketplace_code} className="border-b border-border last:border-0">
                          <td className="py-3 pl-5 pr-3">
                            <Badge tone="info">{marketplaceCodeLabels[row.marketplace_code]}</Badge>
                          </td>
                          <td className="px-3 py-3 text-right text-base tabular-nums text-foreground">
                            {formatPaise(row.gross_sales_paise)}
                          </td>
                          <td className="px-3 py-3 text-right text-base tabular-nums text-danger">
                            -{formatPaise(row.tcs_paise)}
                          </td>
                          <td className="px-3 py-3 text-right text-base tabular-nums text-danger">
                            -{formatPaise(row.tds_paise)}
                          </td>
                          <td className="py-3 pl-3 pr-5 text-right text-base tabular-nums font-medium text-foreground">
                            {formatPaise(row.gross_sales_paise - row.tcs_paise - row.tds_paise)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardBody>
            </Card>
          </>
        )}
      </AsyncState>
    </div>
  );
}
