/**
 * Mock-first Phase 2 hooks (see fixtureTypes.ts). Shaped exactly like a
 * real TanStack Query hook (`{data, isLoading, isError, error, refetch}`
 * / `useMutation`) on purpose — when the reconciliation engine and
 * FeeSchedule work land (TRACKING.md Phase 2 row), swapping these for
 * `apiFetch` calls against the real endpoints is a body-swap, not a
 * rewrite of any page.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getAnomalyQueue,
  getReconciliationSummary,
  setAnomalyReview,
} from "./fixtureData";
import type { AnomalyLineItem, ReconciliationSummary } from "./fixtureTypes";

const MOCK_DELAY_MS = 350;
const delay = <T,>(value: T) => new Promise<T>((resolve) => setTimeout(() => resolve(value), MOCK_DELAY_MS));

const mockKeys = {
  summary: ["mock", "reconciliation-summary"] as const,
  anomalies: ["mock", "anomaly-queue"] as const,
};

export function useReconciliationSummary() {
  return useQuery({
    queryKey: mockKeys.summary,
    queryFn: () => delay(getReconciliationSummary()),
  });
}

export function useAnomalyQueue() {
  return useQuery({
    queryKey: mockKeys.anomalies,
    queryFn: () => delay(getAnomalyQueue()),
  });
}

export function useReviewAnomaly() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      status,
      note,
    }: {
      id: string;
      status: AnomalyLineItem["review_status"];
      note?: string | null;
    }) => {
      setAnomalyReview(id, status, note ?? null);
      return delay({ id, status });
    },
    onSuccess: () => {
      client.invalidateQueries({ queryKey: mockKeys.anomalies });
      client.invalidateQueries({ queryKey: mockKeys.summary });
    },
  });
}

export type { ReconciliationSummary };
