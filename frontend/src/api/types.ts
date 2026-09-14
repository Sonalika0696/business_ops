/**
 * Hand-mirrored from the live OpenAPI schema (http://localhost:8000/openapi.json).
 * That schema is the source of truth, not DESIGN.md prose — re-check it if a
 * field here ever looks stale (see TRACKING.md contract freeze log).
 */

export type MsmeClassification = "MICRO" | "SMALL" | "MEDIUM" | "NONE";
export type MarketplaceCode = "AMAZON_IN" | "FLIPKART" | "MEESHO";
export type FulfillmentType =
  | "SELF_SHIP"
  | "FBA"
  | "FLIPKART_ADVANTAGE"
  | "MEESHO_SUPPLIER";
export type SettlementStatus =
  | "UPLOADED"
  | "PARSING"
  | "PARSED"
  | "RECONCILING"
  | "RECONCILED"
  | "FAILED";
export type MatchStatus =
  | "UNMATCHED"
  | "MATCHED_EXACT"
  | "MATCHED_FUZZY"
  | "ADJUSTMENT";
export type AmountCanonical =
  | "REFERRAL_FEE"
  | "CLOSING_FEE"
  | "SHIPPING_FEE"
  | "COLLECTION_FEE"
  | "FBA_FEE"
  | "STORAGE_FEE"
  | "ADVERTISING_FEE"
  | "PROMOTION_REBATE"
  | "TCS"
  | "TDS"
  | "REFUND"
  | "REIMBURSEMENT"
  | "ADJUSTMENT"
  | "GST_ON_FEE";

export interface ErrorEnvelope {
  error: {
    code: string;
    message: string;
    field_errors: Record<string, string> | null;
  };
}

export interface RegisterRequest {
  email: string;
  password: string;
  legal_name: string;
}
export interface RegisterResponse {
  seller_id: string;
}
export interface LoginRequest {
  email: string;
  password: string;
}
export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface SellerRead {
  id: string;
  legal_name: string;
  trade_name: string | null;
  email: string;
  gstin: string | null;
  pan: string | null;
  udyam_registration_number: string | null;
  msme_classification: MsmeClassification;
  primary_state: string | null;
  primary_pincode: string | null;
  principal_place_of_business: string | null;
  bank_account_number: string | null;
  bank_ifsc: string | null;
  bank_name: string | null;
  created_at: string;
  updated_at: string;
}
export type SellerUpdate = Partial<
  Omit<SellerRead, "id" | "email" | "created_at" | "updated_at">
>;

export interface ProductRead {
  id: string;
  seller_id: string;
  internal_sku: string;
  product_name: string;
  hsn_code: string | null;
  category_primary: string | null;
  category_sub: string | null;
  weight_grams: number | null;
  dimensions_cm_length: string | null;
  dimensions_cm_width: string | null;
  dimensions_cm_height: string | null;
  mrp_paise: number;
  cost_price_paise: number;
  gst_rate: number;
  created_at: string;
  deleted_at: string | null;
}
export interface ProductCreate {
  internal_sku: string;
  product_name: string;
  hsn_code?: string | null;
  category_primary?: string | null;
  category_sub?: string | null;
  weight_grams?: number | null;
  dimensions_cm_length?: number | null;
  dimensions_cm_width?: number | null;
  dimensions_cm_height?: number | null;
  mrp_paise: number;
  cost_price_paise: number;
  gst_rate: number;
}
export type ProductUpdate = Partial<ProductCreate>;
export interface ProductListResponse {
  items: ProductRead[];
  total: number;
}

export interface MarketplaceRead {
  id: string;
  code: MarketplaceCode;
  display_name: string;
  settlement_frequency_days: number;
  payout_split_count: number;
  active: boolean;
}
export interface MarketplaceListResponse {
  items: MarketplaceRead[];
}

export interface SellerMarketplaceAccountRead {
  id: string;
  seller_id: string;
  marketplace_id: string;
  merchant_id_on_platform: string;
  warehouse_pincode: string | null;
  fulfillment_type: FulfillmentType;
  activated_on: string;
  deleted_at: string | null;
}
export interface SellerMarketplaceAccountCreate {
  marketplace_code: MarketplaceCode;
  merchant_id_on_platform: string;
  warehouse_pincode?: string | null;
  fulfillment_type: FulfillmentType;
}
export interface SellerMarketplaceAccountUpdate {
  warehouse_pincode?: string | null;
  fulfillment_type?: FulfillmentType | null;
}
export interface SellerMarketplaceAccountListResponse {
  items: SellerMarketplaceAccountRead[];
  total: number;
}

export interface SettlementReportRead {
  id: string;
  seller_marketplace_account_id: string;
  period_start: string;
  period_end: string;
  total_gross_sales_paise: number | null;
  total_fees_paise: number | null;
  total_taxes_deducted_paise: number | null;
  total_returns_refunds_paise: number | null;
  total_reimbursements_paise: number | null;
  net_payout_expected_paise: number | null;
  net_payout_bank_credited_paise: number | null;
  discrepancy_amount_paise: number | null;
  file_uploaded_at: string;
  source_file_hash: string;
  original_filename: string;
  status: SettlementStatus;
  row_count: number | null;
  rejected_row_count: number;
  error_message: string | null;
}
export interface SettlementReportListResponse {
  items: SettlementReportRead[];
  total: number;
}
export interface SettlementUploadResponse {
  settlement_report_id: string;
  status: SettlementStatus;
  duplicate?: boolean;
}

export interface SettlementLineItemRead {
  id: string;
  settlement_report_id: string;
  order_id: string | null;
  amount_description: string;
  amount_canonical: AmountCanonical;
  amount_value_paise: number;
  posted_date: string;
  currency: string;
  raw_line_data: Record<string, unknown>;
  match_status: MatchStatus;
  expected_amount_paise: number | null;
  deviation_paise: number | null;
  is_anomaly: boolean;
  created_at: string;
}
export interface SettlementLineItemListResponse {
  items: SettlementLineItemRead[];
  total: number;
}

export interface RejectedRowDetail {
  row_number: number;
  raw_row: Record<string, unknown>;
  reason: string;
}
export interface RejectedRowsResponse {
  items: RejectedRowDetail[];
}

export interface ProgressFrame {
  status: SettlementStatus;
  row_count: number | null;
  rejected_row_count: number;
}
