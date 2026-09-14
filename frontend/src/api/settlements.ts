import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import { queryKeys } from "./queryClient";
import type {
  MatchStatus,
  RejectedRowsResponse,
  SettlementLineItemListResponse,
  SettlementReportListResponse,
  SettlementReportRead,
  SettlementUploadResponse,
} from "./types";

const PAGE_SIZE = 20;

/** Terminal states — once reached, no further progress frames will arrive. */
export function isTerminalStatus(status: SettlementReportRead["status"]): boolean {
  return status === "RECONCILED" || status === "FAILED";
}

export function useSettlements(page: number) {
  return useQuery({
    queryKey: queryKeys.settlements(page),
    queryFn: () =>
      apiFetch<SettlementReportListResponse>("/api/settlements", { query: { page, page_size: PAGE_SIZE } }),
    placeholderData: (prev) => prev,
  });
}

export function useSettlement(reportId: string | undefined, opts: { livePoll?: boolean } = {}) {
  return useQuery({
    queryKey: queryKeys.settlement(reportId ?? ""),
    queryFn: () => apiFetch<SettlementReportRead>(`/api/settlements/${reportId}`),
    enabled: Boolean(reportId),
    // Safety-net poll alongside the WS push: the dev environment's Redis is
    // known-unavailable (see backend/DEV_SETUP.md), which makes the WS
    // pub/sub progress push silently stop after the first frame. Polling
    // while non-terminal means the processing screen still resolves to a
    // real final state instead of hanging forever if that happens.
    refetchInterval: (query) => {
      if (!opts.livePoll) return false;
      const status = query.state.data?.status;
      if (!status || isTerminalStatus(status)) return false;
      return 3000;
    },
  });
}

export function useUploadSettlement() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ file, sellerMarketplaceAccountId }: { file: File; sellerMarketplaceAccountId: string }) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("seller_marketplace_account_id", sellerMarketplaceAccountId);
      return apiFetch<SettlementUploadResponse>("/api/settlements/upload", { method: "POST", formData });
    },
    onSuccess: () => client.invalidateQueries({ queryKey: ["settlements"] }),
  });
}

export function useLineItems(reportId: string | undefined, matchStatus?: MatchStatus) {
  return useQuery({
    queryKey: queryKeys.lineItems(reportId ?? "", matchStatus),
    queryFn: () =>
      apiFetch<SettlementLineItemListResponse>(`/api/settlements/${reportId}/line-items`, {
        query: { match_status: matchStatus },
      }),
    enabled: Boolean(reportId),
  });
}

export function useRejectedRows(reportId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.rejectedRows(reportId ?? ""),
    queryFn: () => apiFetch<RejectedRowsResponse>(`/api/settlements/${reportId}/rejected-rows`),
    enabled: Boolean(reportId),
  });
}
