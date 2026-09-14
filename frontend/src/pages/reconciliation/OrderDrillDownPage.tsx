import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { AsyncState } from "@/components/ui/AsyncState";
import { StatCard } from "@/components/ui/StatCard";
import { Badge } from "@/components/ui/Badge";
import { MockDataBanner } from "@/components/ui/MockDataBanner";
import { useOrderDetail } from "@/api/mocks/orders";
import { amountCanonicalLabels, marketplaceCodeLabels } from "@/lib/labels";
import { formatPaise, formatSignedPaise } from "@/lib/money";
import { formatDateIST } from "@/lib/date";

const ORDER_STATUS_TONE: Record<string, "success" | "warning" | "danger" | "info" | "neutral"> = {
  DELIVERED: "success",
  SHIPPED: "info",
  PLACED: "neutral",
  CANCELLED: "danger",
  RETURNED: "warning",
  RTO: "danger",
};

export function OrderDrillDownPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const orderQuery = useOrderDetail(orderId);
  const order = orderQuery.data;

  return (
    <div className="flex flex-col gap-6">
      <Link
        to="/reconciliation"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" aria-hidden />
        Reconciliation dashboard
      </Link>

      <MockDataBanner>
        Order-level figures here are illustrative — there's no live order-ingestion API yet (orders come only from the
        synthetic generator per backend/DESIGN.md §2.6). This view is built against the shape that API will return.
      </MockDataBanner>

      <AsyncState isLoading={orderQuery.isLoading} isError={orderQuery.isError} error={orderQuery.error} onRetry={() => orderQuery.refetch()}>
        {order && (
          <>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h1 className="break-words font-heading text-2xl font-semibold text-foreground">
                  {order.marketplace_order_id}
                </h1>
                <p className="mt-1 text-base text-muted-foreground">
                  {marketplaceCodeLabels[order.marketplace_code]} · Ordered {formatDateIST(order.order_date)} ·{" "}
                  {order.payment_type === "PREPAID" ? "Prepaid" : "Cash on delivery"}
                </p>
              </div>
              <Badge tone={ORDER_STATUS_TONE[order.order_status] ?? "neutral"}>{order.order_status}</Badge>
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatCard index={0} label="Gross amount" value={formatPaise(order.total_gross_amount_paise)} />
              <StatCard index={1} label="GST" value={formatPaise(order.total_gst_amount_paise)} />
              <StatCard index={2} label="TCS + TDS" value={formatPaise(order.total_tcs_deducted_paise + order.total_tds_deducted_paise)} tone="danger" />
              <StatCard index={3} label="Net earned" value={formatPaise(order.net_earned_paise)} tone="success" />
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Items ordered</CardTitle>
              </CardHeader>
              <CardBody className="p-0">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-border text-sm text-muted-foreground">
                      <th className="py-2.5 pl-5 pr-3 font-medium">Product</th>
                      <th className="px-3 py-2.5 font-medium">SKU</th>
                      <th className="px-3 py-2.5 text-right font-medium">Qty</th>
                      <th className="px-3 py-2.5 text-right font-medium">Unit price</th>
                      <th className="py-2.5 pl-3 pr-5 text-right font-medium">Line total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {order.line_items.map((li, i) => (
                      <tr key={i} className="border-b border-border last:border-0">
                        <td className="py-3 pl-5 pr-3 text-base text-foreground">{li.product_name}</td>
                        <td className="px-3 py-3 font-mono text-sm text-muted-foreground">{li.internal_sku}</td>
                        <td className="px-3 py-3 text-right text-base tabular-nums text-muted-foreground">{li.quantity}</td>
                        <td className="px-3 py-3 text-right text-base tabular-nums text-muted-foreground">
                          {formatPaise(li.unit_price_before_gst_paise)}
                        </td>
                        <td className="py-3 pl-3 pr-5 text-right text-base tabular-nums font-medium text-foreground">
                          {formatPaise(li.line_total_paise)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardBody>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Settlement lines for this order</CardTitle>
              </CardHeader>
              <CardBody className="p-0">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-border text-sm text-muted-foreground">
                      <th className="py-2.5 pl-5 pr-3 font-medium">Description</th>
                      <th className="px-3 py-2.5 text-right font-medium">Expected</th>
                      <th className="px-3 py-2.5 text-right font-medium">Actual</th>
                      <th className="py-2.5 pl-3 pr-5 text-right font-medium">Deviation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {order.settlement_lines.map((line, i) => (
                      <tr key={i} className="border-b border-border last:border-0">
                        <td className="py-3 pl-5 pr-3 text-base text-foreground">
                          {amountCanonicalLabels[line.amount_canonical]}
                          <span className="ml-2 text-sm text-muted-foreground">{line.amount_description}</span>
                        </td>
                        <td className="px-3 py-3 text-right text-base tabular-nums text-muted-foreground">
                          {formatSignedPaise(line.expected_amount_paise)}
                        </td>
                        <td className="px-3 py-3 text-right text-base tabular-nums font-medium text-foreground">
                          {formatSignedPaise(line.amount_value_paise)}
                        </td>
                        <td
                          className={`py-3 pl-3 pr-5 text-right text-base tabular-nums font-medium ${
                            line.deviation_paise ? "text-danger" : "text-muted-foreground"
                          }`}
                        >
                          {line.deviation_paise ? formatSignedPaise(line.deviation_paise) : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardBody>
            </Card>
          </>
        )}
      </AsyncState>
    </div>
  );
}
