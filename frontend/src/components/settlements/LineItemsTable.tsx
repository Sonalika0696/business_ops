import { cn } from "@/lib/cn";
import { amountCanonicalLabels } from "@/lib/labels";
import { formatSignedPaise } from "@/lib/money";
import { formatDateIST } from "@/lib/date";
import { MatchStatusBadge } from "./StatusBadge";
import type { SettlementLineItemRead } from "@/api/types";

export function LineItemsTable({ items }: { items: SettlementLineItemRead[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-border text-sm text-muted-foreground">
            <th className="py-2.5 pl-5 pr-3 font-medium">Description</th>
            <th className="px-3 py-2.5 font-medium">Type</th>
            <th className="px-3 py-2.5 text-right font-medium">Amount</th>
            <th className="px-3 py-2.5 font-medium">Posted</th>
            <th className="py-2.5 pl-3 pr-5 font-medium">Match status</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} className="border-b border-border last:border-0 hover:bg-muted/50">
              <td className="py-3 pl-5 pr-3 text-base text-foreground">{item.amount_description}</td>
              <td className="px-3 py-3 text-base text-muted-foreground">
                {amountCanonicalLabels[item.amount_canonical]}
              </td>
              <td
                className={cn(
                  "px-3 py-3 text-right text-base tabular-nums font-medium",
                  item.amount_value_paise > 0 ? "text-success" : item.amount_value_paise < 0 ? "text-danger" : "text-foreground",
                )}
              >
                {formatSignedPaise(item.amount_value_paise)}
              </td>
              <td className="px-3 py-3 text-base text-muted-foreground">{formatDateIST(item.posted_date)}</td>
              <td className="py-3 pl-3 pr-5">
                <MatchStatusBadge status={item.match_status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
