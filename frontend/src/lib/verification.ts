/**
 * Onboarding verification — fully offline (ARCHITECTURE.md §9: "onboarding
 * must work fully offline"; frontend/PLAN.md Phase 2 item 4: "static/offline
 * feedback is an acceptable dissertation substitute" for live verification).
 *
 * These aren't calls to gstinapi.in/Razorpay IFSC/postalpincode.in — they're
 * real, complete, publicly documented offline algorithms and reference data
 * (GST state codes, the GSTIN mod-36 check digit, IFSC/PAN format rules),
 * so there's nothing to fall back from: this degrades-to-offline case *is*
 * the primary path here, not a fallback. GSTIN checksum algorithm verified
 * against a real registered GSTIN (33AAACC1206D1ZN, Central Warehousing
 * Corporation) — https://dev.to/tarun_vaghasia_a387e1ac9b/how-gstin-checksum-validation-works-and-why-it-isnt-enough-3l8e
 */

const GSTIN_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";

// Official GST state/UT codes.
export const GST_STATE_CODES: Record<string, string> = {
  "01": "Jammu and Kashmir",
  "02": "Himachal Pradesh",
  "03": "Punjab",
  "04": "Chandigarh",
  "05": "Uttarakhand",
  "06": "Haryana",
  "07": "Delhi",
  "08": "Rajasthan",
  "09": "Uttar Pradesh",
  "10": "Bihar",
  "11": "Sikkim",
  "12": "Arunachal Pradesh",
  "13": "Nagaland",
  "14": "Manipur",
  "15": "Mizoram",
  "16": "Tripura",
  "17": "Meghalaya",
  "18": "Assam",
  "19": "West Bengal",
  "20": "Jharkhand",
  "21": "Odisha",
  "22": "Chhattisgarh",
  "23": "Madhya Pradesh",
  "24": "Gujarat",
  "25": "Daman and Diu",
  "26": "Dadra and Nagar Haveli",
  "27": "Maharashtra",
  "28": "Andhra Pradesh (old)",
  "29": "Karnataka",
  "30": "Goa",
  "31": "Lakshadweep",
  "32": "Kerala",
  "33": "Tamil Nadu",
  "34": "Puducherry",
  "35": "Andaman and Nicobar Islands",
  "36": "Telangana",
  "37": "Andhra Pradesh",
  "38": "Ladakh",
};

const PAN_HOLDER_TYPES: Record<string, string> = {
  P: "Individual",
  C: "Company",
  H: "Hindu Undivided Family",
  A: "Association of Persons",
  B: "Body of Individuals",
  G: "Government",
  J: "Artificial Juridical Person",
  L: "Local Authority",
  F: "Firm / LLP",
  T: "Trust",
};

// Curated list of common Indian bank IFSC prefixes — real, public data, not
// exhaustive. An unrecognized-but-well-formed code isn't flagged invalid,
// just shown without a bank-name autofill.
const IFSC_BANK_NAMES: Record<string, string> = {
  SBIN: "State Bank of India",
  HDFC: "HDFC Bank",
  ICIC: "ICICI Bank",
  UTIB: "Axis Bank",
  PUNB: "Punjab National Bank",
  KKBK: "Kotak Mahindra Bank",
  YESB: "Yes Bank",
  INDB: "IndusInd Bank",
  IDFB: "IDFC First Bank",
  BARB: "Bank of Baroda",
  CNRB: "Canara Bank",
  UBIN: "Union Bank of India",
  IOBA: "Indian Overseas Bank",
  CBIN: "Central Bank of India",
  MAHB: "Bank of Maharashtra",
  PSIB: "Punjab & Sind Bank",
  SIBL: "South Indian Bank",
  FDRL: "Federal Bank",
  RATN: "RBL Bank",
  BKID: "Bank of India",
  IBKL: "IDBI Bank",
  UCBA: "UCO Bank",
  KVBL: "Karur Vysya Bank",
  TMBL: "Tamilnad Mercantile Bank",
  DCBL: "DCB Bank",
  ESFB: "Equitas Small Finance Bank",
  AUBL: "AU Small Finance Bank",
  JAKA: "Jammu & Kashmir Bank",
  KARB: "Karnataka Bank",
  DBSS: "DBS Bank India",
  HSBC: "HSBC Bank",
  SCBL: "Standard Chartered Bank",
  CITI: "Citibank",
  DEUT: "Deutsche Bank",
  BOFA: "Bank of America",
  PYTM: "Paytm Payments Bank",
  AIRP: "Airtel Payments Bank",
  FINO: "Fino Payments Bank",
  APBL: "Andhra Pradesh Grameena Bank",
};

// First-digit postal zone — India Post's own coarse grouping. This is a
// genuine offline-first substitute for a full pincode→locality database
// (thousands of rows), not a claim of street-level accuracy.
const PIN_ZONE_STATES: Record<string, string> = {
  "1": "Delhi / Haryana / Punjab / Himachal Pradesh / J&K / Chandigarh",
  "2": "Uttar Pradesh / Uttarakhand",
  "3": "Rajasthan / Gujarat / Daman & Diu / Dadra & Nagar Haveli",
  "4": "Maharashtra / Madhya Pradesh / Chhattisgarh / Goa",
  "5": "Andhra Pradesh / Telangana / Karnataka",
  "6": "Tamil Nadu / Kerala / Puducherry",
  "7": "West Bengal / Odisha / North-East India",
  "8": "Bihar / Jharkhand",
};

export interface VerificationResult {
  valid: boolean;
  reason?: string;
  detail?: string;
}

export function validatePAN(rawValue: string): VerificationResult & { holderType?: string } {
  const value = rawValue.trim().toUpperCase();
  if (!value) return { valid: false, reason: "Enter a PAN" };
  if (!/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(value)) {
    return { valid: false, reason: "PAN should be 5 letters, 4 digits, 1 letter (e.g. ABCDE1234F)" };
  }
  const holderType = PAN_HOLDER_TYPES[value[3]];
  return {
    valid: true,
    holderType,
    detail: holderType ? `${holderType} PAN` : undefined,
  };
}

export function validateGSTIN(rawValue: string): VerificationResult & {
  stateCode?: string;
  stateName?: string;
  embeddedPan?: string;
} {
  const value = rawValue.trim().toUpperCase();
  if (!value) return { valid: false, reason: "Enter a GSTIN" };
  if (value.length !== 15) return { valid: false, reason: "GSTIN must be exactly 15 characters" };
  if (!/^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/.test(value)) {
    return { valid: false, reason: "Doesn't match the GSTIN pattern (2-digit state + 10-char PAN + entity code + Z + checksum)" };
  }

  const stateCode = value.slice(0, 2);
  const stateName = GST_STATE_CODES[stateCode];
  if (!stateName) {
    return { valid: false, reason: `"${stateCode}" isn't a recognized GST state code` };
  }

  const embeddedPan = value.slice(2, 12);
  const panCheck = validatePAN(embeddedPan);
  if (!panCheck.valid) {
    return { valid: false, reason: "The PAN embedded in this GSTIN doesn't look valid" };
  }

  let total = 0;
  for (let i = 0; i < 14; i++) {
    const codePoint = GSTIN_CHARSET.indexOf(value[i]);
    const product = codePoint * (i % 2 ? 2 : 1);
    total += Math.floor(product / 36) + (product % 36);
  }
  const expectedCheckDigit = GSTIN_CHARSET[(36 - (total % 36)) % 36];

  if (value[14] !== expectedCheckDigit) {
    return { valid: false, reason: "Checksum digit doesn't match — check for a typo", stateCode, stateName, embeddedPan };
  }

  return {
    valid: true,
    stateCode,
    stateName,
    embeddedPan,
    detail: `${stateName} · ${panCheck.holderType ?? "PAN"} entity`,
  };
}

export function validateIFSC(rawValue: string): VerificationResult & { bankCode?: string; bankName?: string } {
  const value = rawValue.trim().toUpperCase();
  if (!value) return { valid: false, reason: "Enter an IFSC code" };
  if (!/^[A-Z]{4}0[A-Z0-9]{6}$/.test(value)) {
    return { valid: false, reason: "IFSC should be 11 characters: 4 letters, then 0, then 6 alphanumeric (e.g. HDFC0001234)" };
  }
  const bankCode = value.slice(0, 4);
  const bankName = IFSC_BANK_NAMES[bankCode];
  return {
    valid: true,
    bankCode,
    bankName,
    detail: bankName ? `Branch of ${bankName}` : "Format looks valid — bank not in our lookup table",
  };
}

export function lookupPincode(rawValue: string): VerificationResult & { stateGuess?: string } {
  const value = rawValue.trim();
  if (!value) return { valid: false, reason: "Enter a PIN code" };
  if (!/^[1-9][0-9]{5}$/.test(value)) {
    return { valid: false, reason: "PIN code should be 6 digits and not start with 0" };
  }
  const stateGuess = PIN_ZONE_STATES[value[0]];
  return {
    valid: true,
    stateGuess,
    detail: stateGuess ? `Likely ${stateGuess} (approximate, from PIN prefix)` : undefined,
  };
}

export function validateUdyam(rawValue: string): VerificationResult & { stateCode?: string } {
  const value = rawValue.trim().toUpperCase();
  if (!value) return { valid: false, reason: "Enter a Udyam registration number" };
  const match = /^UDYAM-([A-Z]{2})-[0-9]{2}-[0-9]{7}$/.exec(value);
  if (!match) {
    return { valid: false, reason: "Should look like UDYAM-XX-00-0000000" };
  }
  return { valid: true, stateCode: match[1], detail: `Registered in ${match[1]}` };
}
