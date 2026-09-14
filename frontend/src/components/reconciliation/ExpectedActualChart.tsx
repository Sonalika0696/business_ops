import { formatPaise } from "@/lib/money";
import { marketplaceCodeLabels } from "@/lib/labels";
import type { MarketplaceReconciliationRow } from "@/api/mocks/fixtureTypes";

/**
 * Deliberately plain: frontend/PLAN.md Phase 2 asks for "functional (not
 * beautiful) charts" — visual design system work is Phase 5. A hand-rolled
 * bar comparison avoids pulling in a charting library for one chart type,
 * and the table alternative right below it is the actual source of truth
 * for screen readers (dataviz a11y: charts alone aren't SR-friendly).
 */
export function ExpectedActualChart({ rows }: { rows: MarketplaceReconciliationRow[] }) {
  const max = Math.max(...rows.flatMap((r) => [r.expected_payout_paise, r.actual_payout_paise]), 1);

  return (
    <div>
      <div className="flex flex-col gap-5" role="img" aria-label="Expected versus actual payout by marketplace, detailed in the table below">
        {rows.map((row) => {
          const expectedPct = (row.expected_payout_paise / max) * 100;
          const actualPct = (row.actual_payout_paise / max) * 100;
          const isShortfall = row.actual_payout_paise < row.expected_payout_paise;

          return (
            <div key={row.marketplace_code}>
              <div className="mb-1.5 flex items-center justify-between">
                <p className="text-base font-medium text-foreground">{marketplaceCodeLabels[row.marketplace_code]}</p>
                <p className={isShortfall ? "text-sm font-medium text-danger" : "text-sm font-medium text-success"}>
                  {isShortfall ? "−" : "+"}
                  {formatPaise(Math.abs(row.actual_payout_paise - row.expected_payout_paise))}
                </p>
              </div>
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center gap-2.5">
                  <span className="w-16 shrink-0 text-xs text-muted-foreground">Expected</span>
                  <div className="h-3 flex-1 rounded-full bg-muted">
                    <div className="h-full rounded-full bg-primary-300" style={{ width: `${expectedPct}%` }} />
                  </div>
                  <span className="w-28 shrink-0 text-right text-sm tabular-nums text-muted-foreground">
                    {formatPaise(row.expected_payout_paise, { decimals: false })}
                  </span>
                </div>
                <div className="flex items-center gap-2.5">
                  <span className="w-16 shrink-0 text-xs text-muted-foreground">Actual</span>
                  <div className="h-3 flex-1 rounded-full bg-muted">
                    <div
                      className={isShortfall ? "h-full rounded-full bg-danger" : "h-full rounded-full bg-primary"}
                      style={{ width: `${actualPct}%` }}
                    />
                  </div>
                  <span className="w-28 shrink-0 text-right text-sm tabular-nums font-medium text-foreground">
                    {formatPaise(row.actual_payout_paise, { decimals: false })}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <table className="sr-only">
        <caption>Expected versus actual payout by marketplace</caption>
        <thead>
          <tr>
            <th>Marketplace</th>
            <th>Expected payout</th>
            <th>Actual payout</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.marketplace_code}>
              <td>{marketplaceCodeLabels[row.marketplace_code]}</td>
              <td>{formatPaise(row.expected_payout_paise)}</td>
              <td>{formatPaise(row.actual_payout_paise)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
