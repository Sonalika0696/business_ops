/**
 * Every money field the API returns is integer paise (DESIGN.md §1: "never
 * float"). This is the one place paise gets divided by 100 for display —
 * feature code should never do that math inline.
 */

const inrFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 2,
  minimumFractionDigits: 2,
});

const inrFormatterNoDecimals = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

export function formatPaise(paise: number | null | undefined, opts: { decimals?: boolean } = {}): string {
  if (paise === null || paise === undefined) return "—";
  const rupees = paise / 100;
  return opts.decimals === false ? inrFormatterNoDecimals.format(rupees) : inrFormatter.format(rupees);
}

/** Signed variant: prefixes a "+" for positive (credit) amounts, styles negatives naturally. */
export function formatSignedPaise(paise: number | null | undefined): string {
  if (paise === null || paise === undefined) return "—";
  const formatted = formatPaise(Math.abs(paise));
  return paise > 0 ? `+${formatted}` : paise < 0 ? `-${formatted}` : formatted;
}

export function paiseToRupeesInput(paise: number | null | undefined): string {
  if (paise === null || paise === undefined) return "";
  return (paise / 100).toString();
}

export function rupeesInputToPaise(value: string): number {
  const rupees = Number.parseFloat(value);
  if (Number.isNaN(rupees)) return 0;
  return Math.round(rupees * 100);
}
