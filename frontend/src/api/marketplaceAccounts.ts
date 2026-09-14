import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import { queryKeys } from "./queryClient";
import type {
  MarketplaceListResponse,
  SellerMarketplaceAccountCreate,
  SellerMarketplaceAccountListResponse,
  SellerMarketplaceAccountRead,
  SellerMarketplaceAccountUpdate,
} from "./types";

export function useMarketplaces() {
  return useQuery({
    queryKey: queryKeys.marketplaces,
    queryFn: () => apiFetch<MarketplaceListResponse>("/api/marketplaces"),
    staleTime: Infinity,
  });
}

export function useMarketplaceAccounts() {
  return useQuery({
    queryKey: queryKeys.marketplaceAccounts,
    queryFn: () => apiFetch<SellerMarketplaceAccountListResponse>("/api/marketplace-accounts"),
  });
}

export function useCreateMarketplaceAccount() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: SellerMarketplaceAccountCreate) =>
      apiFetch<SellerMarketplaceAccountRead>("/api/marketplace-accounts", { method: "POST", body: payload }),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.marketplaceAccounts }),
  });
}

export function useUpdateMarketplaceAccount(accountId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: SellerMarketplaceAccountUpdate) =>
      apiFetch<SellerMarketplaceAccountRead>(`/api/marketplace-accounts/${accountId}`, {
        method: "PATCH",
        body: payload,
      }),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.marketplaceAccounts }),
  });
}

export function useDeleteMarketplaceAccount() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (accountId: string) =>
      apiFetch<void>(`/api/marketplace-accounts/${accountId}`, { method: "DELETE" }),
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.marketplaceAccounts }),
  });
}
