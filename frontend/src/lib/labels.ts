import type { AmountCanonical, FulfillmentType, MarketplaceCode, MsmeClassification } from "@/api/types";

export const amountCanonicalLabels: Record<AmountCanonical, string> = {
  REFERRAL_FEE: "Referral fee",
  CLOSING_FEE: "Closing fee",
  SHIPPING_FEE: "Shipping fee",
  COLLECTION_FEE: "Collection fee",
  FBA_FEE: "FBA fee",
  STORAGE_FEE: "Storage fee",
  ADVERTISING_FEE: "Advertising fee",
  PROMOTION_REBATE: "Promotion rebate",
  TCS: "TCS",
  TDS: "TDS",
  REFUND: "Refund",
  REIMBURSEMENT: "Reimbursement",
  ADJUSTMENT: "Adjustment",
  GST_ON_FEE: "GST on fee",
};

export const marketplaceCodeLabels: Record<MarketplaceCode, string> = {
  AMAZON_IN: "Amazon.in",
  FLIPKART: "Flipkart",
  MEESHO: "Meesho",
};

export const fulfillmentTypeLabels: Record<FulfillmentType, string> = {
  SELF_SHIP: "Self-ship",
  FBA: "Fulfilled by marketplace (FBA)",
  FLIPKART_ADVANTAGE: "Flipkart Advantage",
  MEESHO_SUPPLIER: "Meesho supplier",
};

export const msmeClassificationLabels: Record<MsmeClassification, string> = {
  MICRO: "Micro",
  SMALL: "Small",
  MEDIUM: "Medium",
  NONE: "Not registered",
};

export const gstRateOptions = [0, 5, 12, 18, 28] as const;

export const returnReasonLabels: Record<string, string> = {
  DAMAGED: "Damaged",
  WRONG_ITEM: "Wrong item",
  NOT_AS_DESCRIBED: "Not as described",
  CHANGE_OF_MIND: "Change of mind",
  DEFECTIVE: "Defective",
  RTO_UNDELIVERED: "RTO — undelivered",
};
