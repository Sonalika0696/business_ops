/**
 * Phase 2 fixture shapes.
 *
 * None of these have a real backend endpoint yet — TRACKING.md's Phase 2
 * row lists FeeSchedule engine / reconciliation engine / returns / TCS-TDS
 * accumulation / integration gateway as still 🔲. Per
 * CROSS-SYSTEM-DEPENDENCIES.md §2-3 this is the mock-first slice: fields
 * are named to match the real entities in backend/DESIGN.md §2 (Order,
 * Return, SettlementLineItem) so swapping a mock hook for a real one in
 * `src/api/reconciliation.ts` etc. later is a data-source change only, not
 * a UI change. Check TRACKING.md's Phase 2 Notes before treating any of
 * this as real.
 */

import type { AmountCanonical, MarketplaceCode, MatchStatus } from "@/api/types";

export type AnomalyReviewStatus = "PENDING" | "ACCEPTED" | "DISPUTED";

export interface AnomalyLineItem {
  id: string;
  settlement_report_id: string;
  order_id: string | null;
  marketplace_order_id: string | null;
  marketplace_code: MarketplaceCode;
  amount_description: string;
  amount_canonical: AmountCanonical;
  amount_value_paise: number;
  expected_amount_paise: number;
  deviation_paise: number;
  match_status: MatchStatus;
  posted_date: string;
  review_status: AnomalyReviewStatus;
  review_note: string | null;
}

export interface MarketplaceReconciliationRow {
  marketplace_code: MarketplaceCode;
  expected_payout_paise: number;
  actual_payout_paise: number;
  bank_credited_paise: number | null;
}

export interface ReconciliationSummary {
  period_start: string;
  period_end: string;
  expected_payout_paise: number;
  actual_payout_paise: number;
  bank_credited_paise: number | null;
  discrepancy_paise: number;
  anomaly_count: number;
  pending_review_count: number;
  by_marketplace: MarketplaceReconciliationRow[];
}

export interface OrderLineItemDetail {
  product_name: string;
  internal_sku: string;
  quantity: number;
  unit_price_before_gst_paise: number;
  line_total_paise: number;
}

export interface OrderSettlementLine {
  amount_description: string;
  amount_canonical: AmountCanonical;
  amount_value_paise: number;
  expected_amount_paise: number | null;
  deviation_paise: number | null;
}

export interface OrderDetail {
  id: string;
  marketplace_order_id: string;
  marketplace_code: MarketplaceCode;
  order_date: string;
  order_status: "PLACED" | "SHIPPED" | "DELIVERED" | "CANCELLED" | "RETURNED" | "RTO";
  payment_type: "PREPAID" | "COD";
  total_gross_amount_paise: number;
  total_gst_amount_paise: number;
  total_tcs_deducted_paise: number;
  total_tds_deducted_paise: number;
  line_items: OrderLineItemDetail[];
  settlement_lines: OrderSettlementLine[];
  net_earned_paise: number;
}

export type ReturnStatus = "INITIATED" | "IN_TRANSIT" | "RECEIVED" | "INSPECTED" | "REFUNDED" | "REIMBURSED" | "DISPUTED";
export type ClaimStatus = "NOT_CLAIMED" | "CLAIMED" | "APPROVED" | "REJECTED";

export interface ReturnQueueItem {
  id: string;
  order_id: string;
  marketplace_order_id: string;
  marketplace_code: MarketplaceCode;
  return_reason: "DAMAGED" | "WRONG_ITEM" | "NOT_AS_DESCRIBED" | "CHANGE_OF_MIND" | "DEFECTIVE" | "RTO_UNDELIVERED";
  return_type: "CUSTOMER_RETURN" | "RTO";
  return_status: ReturnStatus;
  initiated_date: string;
  received_date: string | null;
  refund_amount_expected_paise: number;
  refund_amount_credited_paise: number;
  claim_status: ClaimStatus;
  claim_window_expires: string | null;
}

export interface MarketplaceTaxRow {
  marketplace_code: MarketplaceCode;
  gross_sales_paise: number;
  tcs_paise: number;
  tds_paise: number;
}

export interface TaxSummary {
  period_start: string;
  period_end: string;
  total_tcs_paise: number;
  total_tds_paise: number;
  net_of_tax_paise: number;
  by_marketplace: MarketplaceTaxRow[];
}
