const numberFormatter = new Intl.NumberFormat("en-IN");

/** Indian digit grouping (1,00,000 not 100,000) for counts. */
export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return numberFormatter.format(value);
}
