import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import { queryKeys } from "./queryClient";
import type { ProductCreate, ProductListResponse, ProductRead, ProductUpdate } from "./types";

const PAGE_SIZE = 20;

export function useProducts(page: number) {
  return useQuery({
    queryKey: queryKeys.products(page),
    queryFn: () =>
      apiFetch<ProductListResponse>("/api/products", { query: { page, page_size: PAGE_SIZE } }),
    placeholderData: (prev) => prev,
  });
}

export function useCreateProduct() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProductCreate) => apiFetch<ProductRead>("/api/products", { method: "POST", body: payload }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["products"] }),
  });
}

export function useUpdateProduct(productId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProductUpdate) =>
      apiFetch<ProductRead>(`/api/products/${productId}`, { method: "PATCH", body: payload }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["products"] }),
  });
}

export function useDeleteProduct() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (productId: string) => apiFetch<void>(`/api/products/${productId}`, { method: "DELETE" }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["products"] }),
  });
}

export { PAGE_SIZE as PRODUCTS_PAGE_SIZE };
