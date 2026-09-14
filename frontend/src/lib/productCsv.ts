import { gstRateOptions } from "@/lib/labels";
import { rupeesInputToPaise } from "@/lib/money";
import type { ProductCreate } from "@/api/types";

/**
 * CSV bulk product import (frontend/PLAN.md Phase 2 item 4). Parsing and
 * per-row shape validation happen here — the same checks ProductFormDialog
 * already applies to a single row, not new business logic — but the
 * canonical source of truth for whether a row is actually acceptable is
 * still the real `POST /api/products` call per row (uniqueness, DB
 * constraints); this only catches malformed rows before they're sent.
 */

export const PRODUCT_CSV_COLUMNS = [
  "internal_sku",
  "product_name",
  "mrp",
  "cost_price",
  "gst_rate",
  "hsn_code",
  "category_primary",
  "category_sub",
  "weight_grams",
] as const;

export function buildProductCsvTemplate(): string {
  const header = PRODUCT_CSV_COLUMNS.join(",");
  const example = "SKU-101,Cotton Kurta - Blue,899.00,410.00,5,6109,Apparel,Kurtas,250";
  return `${header}\n${example}\n`;
}

function parseCsvLine(line: string): string[] {
  // Minimal quoted-field CSV split — handles commas inside "quoted" values,
  // which is as far as a template this simple needs to go.
  const cells: string[] = [];
  let current = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === "," && !inQuotes) {
      cells.push(current);
      current = "";
    } else {
      current += char;
    }
  }
  cells.push(current);
  return cells.map((c) => c.trim());
}

export interface ParsedProductRow {
  rowNumber: number;
  raw: Record<string, string>;
  data: ProductCreate | null;
  errors: string[];
}

export function parseProductCsv(text: string): ParsedProductRow[] {
  const lines = text.split(/\r\n|\n|\r/).filter((line) => line.trim().length > 0);
  if (lines.length === 0) return [];

  const header = parseCsvLine(lines[0]).map((h) => h.toLowerCase());
  const rows: ParsedProductRow[] = [];

  for (let i = 1; i < lines.length; i++) {
    const cells = parseCsvLine(lines[i]);
    const raw: Record<string, string> = {};
    header.forEach((col, idx) => {
      raw[col] = cells[idx] ?? "";
    });

    const errors: string[] = [];
    const internal_sku = raw.internal_sku?.trim();
    const product_name = raw.product_name?.trim();
    if (!internal_sku) errors.push("internal_sku is required");
    if (!product_name) errors.push("product_name is required");

    const mrpRaw = raw.mrp?.trim();
    const costRaw = raw.cost_price?.trim();
    if (!mrpRaw || Number.isNaN(Number.parseFloat(mrpRaw))) errors.push("mrp must be a number");
    if (!costRaw || Number.isNaN(Number.parseFloat(costRaw))) errors.push("cost_price must be a number");

    const gstRateRaw = raw.gst_rate?.trim();
    const gstRate = Number.parseInt(gstRateRaw ?? "", 10);
    if (!gstRateRaw || !gstRateOptions.includes(gstRate as (typeof gstRateOptions)[number])) {
      errors.push(`gst_rate must be one of ${gstRateOptions.join(", ")}`);
    }

    const weightRaw = raw.weight_grams?.trim();
    if (weightRaw && Number.isNaN(Number.parseInt(weightRaw, 10))) errors.push("weight_grams must be a whole number");

    rows.push({
      rowNumber: i + 1,
      raw,
      errors,
      data:
        errors.length === 0
          ? {
              internal_sku,
              product_name,
              mrp_paise: rupeesInputToPaise(mrpRaw!),
              cost_price_paise: rupeesInputToPaise(costRaw!),
              gst_rate: gstRate,
              hsn_code: raw.hsn_code?.trim() || null,
              category_primary: raw.category_primary?.trim() || null,
              category_sub: raw.category_sub?.trim() || null,
              weight_grams: weightRaw ? Number.parseInt(weightRaw, 10) : null,
            }
          : null,
    });
  }

  return rows;
}
