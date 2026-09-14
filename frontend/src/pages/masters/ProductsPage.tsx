import { useState } from "react";
import { PackageSearch, Plus, Pencil, Trash2, UploadCloud } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { AsyncState } from "@/components/ui/AsyncState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Pagination } from "@/components/ui/Pagination";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/Dialog";
import { useToast } from "@/components/ui/Toast";
import { useDeleteProduct, useProducts, PRODUCTS_PAGE_SIZE } from "@/api/products";
import { formatPaise } from "@/lib/money";
import { ApiError } from "@/api/client";
import { ProductFormDialog } from "./ProductFormDialog";
import { ProductBulkImportDialog } from "./ProductBulkImportDialog";
import type { ProductRead } from "@/api/types";

export function ProductsPage() {
  const [page, setPage] = useState(1);
  const [formState, setFormState] = useState<{ open: boolean; product: ProductRead | null }>({
    open: false,
    product: null,
  });
  const [bulkImportOpen, setBulkImportOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ProductRead | null>(null);

  const productsQuery = useProducts(page);
  const deleteProduct = useDeleteProduct();
  const { push } = useToast();

  const items = productsQuery.data?.items ?? [];
  const total = productsQuery.data?.total ?? 0;

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteProduct.mutateAsync(deleteTarget.id);
      push(`"${deleteTarget.product_name}" removed.`);
      setDeleteTarget(null);
    } catch (err) {
      push(err instanceof ApiError ? err.message : "Couldn't remove this product.", "danger");
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-heading text-2xl font-semibold text-foreground">Products</h1>
          <p className="mt-1 text-base text-muted-foreground">Your SKU catalog, used to reconcile settlement lines.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => setBulkImportOpen(true)} icon={<UploadCloud className="size-4" aria-hidden />}>
            Bulk import
          </Button>
          <Button onClick={() => setFormState({ open: true, product: null })} icon={<Plus className="size-4" aria-hidden />}>
            Add product
          </Button>
        </div>
      </div>

      <Card>
        <AsyncState
          isLoading={productsQuery.isLoading}
          isError={productsQuery.isError}
          error={productsQuery.error}
          onRetry={() => productsQuery.refetch()}
          isEmpty={items.length === 0}
          emptyState={
            <EmptyState
              icon={<PackageSearch className="size-6" aria-hidden />}
              title="No products yet"
              description="Add your SKUs so settlement lines can be matched against real products."
              action={<Button onClick={() => setFormState({ open: true, product: null })}>Add your first product</Button>}
            />
          }
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-border text-sm text-muted-foreground">
                  <th className="py-2.5 pl-5 pr-3 font-medium">SKU</th>
                  <th className="px-3 py-2.5 font-medium">Product</th>
                  <th className="px-3 py-2.5 font-medium">Category</th>
                  <th className="px-3 py-2.5 text-right font-medium">MRP</th>
                  <th className="px-3 py-2.5 text-right font-medium">Cost</th>
                  <th className="px-3 py-2.5 font-medium">GST</th>
                  <th className="py-2.5 pl-3 pr-5 font-medium">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {items.map((product) => (
                  <tr key={product.id} className="border-b border-border last:border-0 hover:bg-muted/50">
                    <td className="py-3 pl-5 pr-3 font-mono text-sm text-foreground">{product.internal_sku}</td>
                    <td className="px-3 py-3 text-base text-foreground">{product.product_name}</td>
                    <td className="px-3 py-3 text-base text-muted-foreground">
                      {product.category_primary ?? "—"}
                    </td>
                    <td className="px-3 py-3 text-right text-base tabular-nums text-foreground">
                      {formatPaise(product.mrp_paise)}
                    </td>
                    <td className="px-3 py-3 text-right text-base tabular-nums text-muted-foreground">
                      {formatPaise(product.cost_price_paise)}
                    </td>
                    <td className="px-3 py-3 text-base text-muted-foreground">{product.gst_rate}%</td>
                    <td className="py-3 pl-3 pr-5">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => setFormState({ open: true, product })}
                          aria-label={`Edit ${product.product_name}`}
                          className="cursor-pointer rounded p-2 text-muted-foreground hover:bg-muted hover:text-foreground"
                        >
                          <Pencil className="size-4" aria-hidden />
                        </button>
                        <button
                          type="button"
                          onClick={() => setDeleteTarget(product)}
                          aria-label={`Remove ${product.product_name}`}
                          className="cursor-pointer rounded p-2 text-muted-foreground hover:bg-danger-soft hover:text-danger"
                        >
                          <Trash2 className="size-4" aria-hidden />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {total > 0 && <Pagination page={page} pageSize={PRODUCTS_PAGE_SIZE} total={total} onPageChange={setPage} />}
        </AsyncState>
      </Card>

      <ProductFormDialog
        open={formState.open}
        product={formState.product}
        onClose={() => setFormState({ open: false, product: null })}
      />

      <ProductBulkImportDialog open={bulkImportOpen} onClose={() => setBulkImportOpen(false)} />

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Remove this product?"
        description={`"${deleteTarget?.product_name}" will no longer be available for new reconciliation matches. This can be reversed by an administrator.`}
        confirmLabel="Remove"
        danger
        loading={deleteProduct.isPending}
      />
    </div>
  );
}
