import { useState } from "react";
import { Store, Plus, Trash2 } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { AsyncState } from "@/components/ui/AsyncState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ConfirmDialog } from "@/components/ui/Dialog";
import { useToast } from "@/components/ui/Toast";
import { useDeleteMarketplaceAccount, useMarketplaceAccounts, useMarketplaces } from "@/api/marketplaceAccounts";
import { fulfillmentTypeLabels, marketplaceCodeLabels } from "@/lib/labels";
import { formatDateIST } from "@/lib/date";
import { ApiError } from "@/api/client";
import { MarketplaceAccountFormDialog } from "./MarketplaceAccountFormDialog";
import type { SellerMarketplaceAccountRead } from "@/api/types";

export function MarketplaceAccountsPage() {
  const [formOpen, setFormOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<SellerMarketplaceAccountRead | null>(null);

  const accountsQuery = useMarketplaceAccounts();
  const marketplacesQuery = useMarketplaces();
  const deleteAccount = useDeleteMarketplaceAccount();
  const { push } = useToast();

  const items = accountsQuery.data?.items ?? [];
  const marketplaceById = new Map((marketplacesQuery.data?.items ?? []).map((m) => [m.id, m]));

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteAccount.mutateAsync(deleteTarget.id);
      push("Marketplace account removed.");
      setDeleteTarget(null);
    } catch (err) {
      push(err instanceof ApiError ? err.message : "Couldn't remove this account.", "danger");
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-heading text-2xl font-semibold text-foreground">Marketplace accounts</h1>
          <p className="mt-1 text-base text-muted-foreground">
            Connect the marketplace seller accounts you upload settlement files for.
          </p>
        </div>
        <Button onClick={() => setFormOpen(true)} icon={<Plus className="size-4" aria-hidden />}>
          Add account
        </Button>
      </div>

      <Card>
        <AsyncState
          isLoading={accountsQuery.isLoading}
          isError={accountsQuery.isError}
          error={accountsQuery.error}
          onRetry={() => accountsQuery.refetch()}
          isEmpty={items.length === 0}
          emptyState={
            <EmptyState
              icon={<Store className="size-6" aria-hidden />}
              title="No marketplace accounts yet"
              description="Add Amazon, Flipkart or Meesho to start uploading settlement files."
              action={<Button onClick={() => setFormOpen(true)}>Add your first account</Button>}
            />
          }
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-border text-sm text-muted-foreground">
                  <th className="py-2.5 pl-5 pr-3 font-medium">Marketplace</th>
                  <th className="px-3 py-2.5 font-medium">Merchant ID</th>
                  <th className="px-3 py-2.5 font-medium">Fulfillment</th>
                  <th className="px-3 py-2.5 font-medium">Activated</th>
                  <th className="py-2.5 pl-3 pr-5 font-medium">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {items.map((account) => {
                  const marketplace = marketplaceById.get(account.marketplace_id);
                  return (
                    <tr key={account.id} className="border-b border-border last:border-0 hover:bg-muted/50">
                      <td className="py-3 pl-5 pr-3">
                        <Badge tone="info">
                          {(marketplace && marketplaceCodeLabels[marketplace.code]) ?? marketplace?.display_name ?? "—"}
                        </Badge>
                      </td>
                      <td className="px-3 py-3 font-mono text-sm text-foreground">{account.merchant_id_on_platform}</td>
                      <td className="px-3 py-3 text-base text-muted-foreground">
                        {fulfillmentTypeLabels[account.fulfillment_type]}
                      </td>
                      <td className="px-3 py-3 text-base text-muted-foreground">{formatDateIST(account.activated_on)}</td>
                      <td className="py-3 pl-3 pr-5">
                        <div className="flex justify-end">
                          <button
                            type="button"
                            onClick={() => setDeleteTarget(account)}
                            aria-label={`Remove ${account.merchant_id_on_platform}`}
                            className="cursor-pointer rounded p-2 text-muted-foreground hover:bg-danger-soft hover:text-danger"
                          >
                            <Trash2 className="size-4" aria-hidden />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </AsyncState>
      </Card>

      <MarketplaceAccountFormDialog open={formOpen} onClose={() => setFormOpen(false)} />

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Remove this marketplace account?"
        description="Past settlement uploads for this account stay in your history, but you won't be able to upload new ones for it."
        confirmLabel="Remove"
        danger
        loading={deleteAccount.isPending}
      />
    </div>
  );
}
