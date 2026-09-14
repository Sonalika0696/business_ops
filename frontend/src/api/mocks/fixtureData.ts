/**
 * Deterministic fixture generator for Phase 2 mock screens — see
 * fixtureTypes.ts for why these exist. A seeded PRNG keeps the numbers
 * stable across re-renders/pagination within one browser session instead
 * of reshuffling on every fetch, without needing a real store.
 */

import type {
  AnomalyLineItem,
  MarketplaceReconciliationRow,
  OrderDetail,
  ReconciliationSummary,
  ReturnQueueItem,
  TaxSummary,
} from "./fixtureTypes";
import type { AmountCanonical, MarketplaceCode } from "@/api/types";

function mulberry32(seed: number) {
  return function random() {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const rand = mulberry32(20260914);
const pick = <T,>(arr: readonly T[]): T => arr[Math.floor(rand() * arr.length)];
const int = (min: number, max: number) => Math.floor(min + rand() * (max - min + 1));

const MARKETPLACES: MarketplaceCode[] = ["AMAZON_IN", "FLIPKART", "MEESHO"];
const FEE_TYPES: { description: string; canonical: AmountCanonical }[] = [
  { description: "Referral fee", canonical: "REFERRAL_FEE" },
  { description: "Closing fee", canonical: "CLOSING_FEE" },
  { description: "Shipping fee", canonical: "SHIPPING_FEE" },
  { description: "FBA pick & pack fee", canonical: "FBA_FEE" },
  { description: "Collection fee", canonical: "COLLECTION_FEE" },
];
const PRODUCT_NAMES = [
  "Cotton Kurta - Blue",
  "Wireless Earbuds Pro",
  "Steel Water Bottle 1L",
  "Yoga Mat 6mm",
  "Men's Running Shoes",
  "Ceramic Coffee Mug Set",
  "Bluetooth Speaker Mini",
  "Kids Storybook Set",
  "Non-stick Frying Pan",
  "Leather Wallet - Brown",
];

function daysAgoISO(days: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - days);
  return d.toISOString().slice(0, 10);
}

let anomalyReviewOverrides = new Map<string, { review_status: AnomalyLineItem["review_status"]; review_note: string | null }>();

export function resetAnomalyOverrides() {
  anomalyReviewOverrides = new Map();
}

export function setAnomalyReview(id: string, status: AnomalyLineItem["review_status"], note: string | null) {
  anomalyReviewOverrides.set(id, { review_status: status, review_note: note });
}

const ANOMALIES: AnomalyLineItem[] = Array.from({ length: 14 }, (_, i) => {
  const marketplace = pick(MARKETPLACES);
  const feeType = pick(FEE_TYPES);
  const expected = int(4000, 45000);
  const driftPct = pick([-0.42, -0.28, -0.19, 0.15, 0.22, 0.35, -0.5]);
  const actual = Math.round(expected * (1 + driftPct));
  return {
    id: `anomaly-${i + 1}`,
    settlement_report_id: `mock-report-${(i % 3) + 1}`,
    order_id: `mock-order-${100 + i}`,
    marketplace_order_id: `${marketplace.slice(0, 3)}-ORD-${9000 + i}`,
    marketplace_code: marketplace,
    amount_description: feeType.description,
    amount_canonical: feeType.canonical,
    amount_value_paise: -actual,
    expected_amount_paise: -expected,
    deviation_paise: -actual - -expected,
    match_status: "MATCHED_EXACT",
    posted_date: daysAgoISO(int(1, 28)),
    review_status: "PENDING",
    review_note: null,
  };
});

export function getAnomalyQueue(): AnomalyLineItem[] {
  return ANOMALIES.map((item) => {
    const override = anomalyReviewOverrides.get(item.id);
    return override ? { ...item, ...override } : item;
  });
}

export function getReconciliationSummary(): ReconciliationSummary {
  const byMarketplace: MarketplaceReconciliationRow[] = MARKETPLACES.map((code) => {
    const expected = int(180000, 420000) * 100;
    const actual = Math.round(expected * (1 + pick([-0.06, -0.03, -0.015, 0, 0.01])));
    return {
      marketplace_code: code,
      expected_payout_paise: expected,
      actual_payout_paise: actual,
      bank_credited_paise: null,
    };
  });

  const expected_payout_paise = byMarketplace.reduce((sum, r) => sum + r.expected_payout_paise, 0);
  const actual_payout_paise = byMarketplace.reduce((sum, r) => sum + r.actual_payout_paise, 0);
  const pending = getAnomalyQueue().filter((a) => a.review_status === "PENDING").length;

  return {
    period_start: daysAgoISO(30),
    period_end: daysAgoISO(1),
    expected_payout_paise,
    actual_payout_paise,
    bank_credited_paise: null,
    discrepancy_paise: actual_payout_paise - expected_payout_paise,
    anomaly_count: ANOMALIES.length,
    pending_review_count: pending,
    by_marketplace: byMarketplace,
  };
}

const ORDER_DETAILS = new Map<string, OrderDetail>();
function buildOrderDetail(orderId: string): OrderDetail {
  const anomaly = ANOMALIES.find((a) => a.order_id === orderId);
  const marketplace = anomaly?.marketplace_code ?? pick(MARKETPLACES);
  const gross = int(8000, 60000) * 100;
  const gst = Math.round(gross * 0.12);
  const tcs = Math.round(gross * 0.005);
  const tds = Math.round(gross * 0.001);
  const lineCount = int(1, 3);

  const lineItems = Array.from({ length: lineCount }, () => {
    const qty = int(1, 3);
    const unitPrice = Math.round(gross / lineCount / qty);
    return {
      product_name: pick(PRODUCT_NAMES),
      internal_sku: `SKU-${int(1, 15).toString().padStart(3, "0")}`,
      quantity: qty,
      unit_price_before_gst_paise: unitPrice,
      line_total_paise: unitPrice * qty,
    };
  });

  const settlementLines = anomaly
    ? [
        {
          amount_description: anomaly.amount_description,
          amount_canonical: anomaly.amount_canonical,
          amount_value_paise: anomaly.amount_value_paise,
          expected_amount_paise: anomaly.expected_amount_paise,
          deviation_paise: anomaly.deviation_paise,
        },
      ]
    : [
        {
          amount_description: "Referral fee",
          amount_canonical: "REFERRAL_FEE" as AmountCanonical,
          amount_value_paise: -Math.round(gross * 0.08),
          expected_amount_paise: -Math.round(gross * 0.08),
          deviation_paise: 0,
        },
      ];

  const feesTotal = settlementLines.reduce((sum, l) => sum + l.amount_value_paise, 0);

  return {
    id: orderId,
    marketplace_order_id: anomaly?.marketplace_order_id ?? `ORD-${orderId}`,
    marketplace_code: marketplace,
    order_date: daysAgoISO(int(2, 35)),
    order_status: pick(["DELIVERED", "SHIPPED", "DELIVERED", "DELIVERED", "RETURNED"]),
    payment_type: pick(["PREPAID", "PREPAID", "COD"]),
    total_gross_amount_paise: gross,
    total_gst_amount_paise: gst,
    total_tcs_deducted_paise: tcs,
    total_tds_deducted_paise: tds,
    line_items: lineItems,
    settlement_lines: settlementLines,
    net_earned_paise: gross + feesTotal - tcs - tds,
  };
}

export function getOrderDetail(orderId: string): OrderDetail {
  if (!ORDER_DETAILS.has(orderId)) {
    ORDER_DETAILS.set(orderId, buildOrderDetail(orderId));
  }
  return ORDER_DETAILS.get(orderId)!;
}

let returnClaimOverrides = new Map<string, ReturnQueueItem["claim_status"]>();

export function setReturnClaimStatus(id: string, status: ReturnQueueItem["claim_status"]) {
  returnClaimOverrides.set(id, status);
}

const RETURNS: ReturnQueueItem[] = Array.from({ length: 9 }, (_, i) => {
  const marketplace = pick(MARKETPLACES);
  const expected = int(3000, 28000);
  const credited = pick([0, 0, expected, Math.round(expected * 0.6)]);
  return {
    id: `return-${i + 1}`,
    order_id: `mock-order-${200 + i}`,
    marketplace_order_id: `${marketplace.slice(0, 3)}-ORD-${8000 + i}`,
    marketplace_code: marketplace,
    return_reason: pick(["DAMAGED", "WRONG_ITEM", "NOT_AS_DESCRIBED", "CHANGE_OF_MIND", "DEFECTIVE", "RTO_UNDELIVERED"]),
    return_type: pick(["CUSTOMER_RETURN", "CUSTOMER_RETURN", "RTO"]),
    return_status: pick(["RECEIVED", "INSPECTED", "REFUNDED", "IN_TRANSIT", "DISPUTED"]),
    initiated_date: daysAgoISO(int(5, 40)),
    received_date: rand() > 0.3 ? daysAgoISO(int(1, 30)) : null,
    refund_amount_expected_paise: expected,
    refund_amount_credited_paise: credited,
    claim_status: "NOT_CLAIMED",
    claim_window_expires: daysAgoISO(-int(3, 20)),
  };
});

export function getReturnsQueue(): ReturnQueueItem[] {
  return RETURNS.map((item) => {
    const override = returnClaimOverrides.get(item.id);
    return override ? { ...item, claim_status: override } : item;
  });
}

export function getTaxSummary(): TaxSummary {
  const byMarketplace = MARKETPLACES.map((code) => {
    const gross = int(180000, 420000) * 100;
    return {
      marketplace_code: code,
      gross_sales_paise: gross,
      tcs_paise: Math.round(gross * 0.005),
      tds_paise: Math.round(gross * 0.001),
    };
  });
  return {
    period_start: daysAgoISO(30),
    period_end: daysAgoISO(1),
    total_tcs_paise: byMarketplace.reduce((s, r) => s + r.tcs_paise, 0),
    total_tds_paise: byMarketplace.reduce((s, r) => s + r.tds_paise, 0),
    net_of_tax_paise: byMarketplace.reduce((s, r) => s + r.gross_sales_paise - r.tcs_paise - r.tds_paise, 0),
    by_marketplace: byMarketplace,
  };
}
