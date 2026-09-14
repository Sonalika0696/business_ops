import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "./client";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
        return failureCount < 2;
      },
    },
    mutations: {
      retry: false,
    },
  },
});

export const queryKeys = {
  seller: ["seller"] as const,
  products: (page: number) => ["products", page] as const,
  marketplaces: ["marketplaces"] as const,
  marketplaceAccounts: ["marketplace-accounts"] as const,
  settlements: (page: number) => ["settlements", page] as const,
  settlement: (id: string) => ["settlement", id] as const,
  lineItems: (id: string, matchStatus?: string) => ["settlement", id, "line-items", matchStatus ?? "all"] as const,
  rejectedRows: (id: string) => ["settlement", id, "rejected-rows"] as const,
};
