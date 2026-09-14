import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import { queryKeys } from "./queryClient";
import type { SellerRead, SellerUpdate } from "./types";

export function getSeller(): Promise<SellerRead> {
  return apiFetch<SellerRead>("/api/sellers/me");
}

export function useSeller() {
  return useQuery({ queryKey: queryKeys.seller, queryFn: getSeller });
}

export function useUpdateSeller() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: SellerUpdate) => apiFetch<SellerRead>("/api/sellers/me", { method: "PATCH", body: payload }),
    onSuccess: (seller) => {
      client.setQueryData(queryKeys.seller, seller);
    },
  });
}
