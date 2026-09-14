import { useQuery } from "@tanstack/react-query";
import { getTaxSummary } from "./fixtureData";

const MOCK_DELAY_MS = 300;
const delay = <T,>(value: T) => new Promise<T>((resolve) => setTimeout(() => resolve(value), MOCK_DELAY_MS));

export function useTaxSummary() {
  return useQuery({ queryKey: ["mock", "tax-summary"], queryFn: () => delay(getTaxSummary()) });
}
