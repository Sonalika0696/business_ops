import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { UploadCloud, Store, TriangleAlert } from "lucide-react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { FileDropzone } from "@/components/ui/FileDropzone";
import { Button } from "@/components/ui/Button";
import { AsyncState } from "@/components/ui/AsyncState";
import { EmptyState } from "@/components/ui/EmptyState";
import { useMarketplaceAccounts, useMarketplaces } from "@/api/marketplaceAccounts";
import { useUploadSettlement } from "@/api/settlements";
import { ApiError } from "@/api/client";
import { useToast } from "@/components/ui/Toast";
import { Link } from "react-router-dom";

export function UploadPage() {
  const navigate = useNavigate();
  const { push } = useToast();
  const accountsQuery = useMarketplaceAccounts();
  const marketplacesQuery = useMarketplaces();
  const upload = useUploadSettlement();

  const [accountId, setAccountId] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const accounts = accountsQuery.data?.items ?? [];
  const marketplaceById = new Map((marketplacesQuery.data?.items ?? []).map((m) => [m.id, m]));

  const handleSubmit = async () => {
    setFormError(null);
    if (!accountId) {
      setFormError("Choose which marketplace account this file belongs to.");
      return;
    }
    if (!file) {
      setFormError("Select a settlement file to upload.");
      return;
    }
    try {
      const result = await upload.mutateAsync({ file, sellerMarketplaceAccountId: accountId });
      if (result.duplicate) {
        push("This file was already uploaded — showing the existing report.", "success");
      }
      navigate(`/settlements/${result.settlement_report_id}`);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Upload failed. Please try again.");
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="font-heading text-2xl font-semibold text-foreground">Upload settlement</h1>
        <p className="mt-1 text-base text-muted-foreground">
          Upload a marketplace settlement export to parse and reconcile it against your orders.
        </p>
      </div>

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>New upload</CardTitle>
        </CardHeader>
        <CardBody>
          <AsyncState
            isLoading={accountsQuery.isLoading}
            isError={accountsQuery.isError}
            error={accountsQuery.error}
            onRetry={() => accountsQuery.refetch()}
            isEmpty={accounts.length === 0}
            emptyState={
              <EmptyState
                icon={<Store className="size-6" aria-hidden />}
                title="No marketplace accounts yet"
                description="Connect a marketplace account before uploading a settlement file."
                action={
                  <Button onClick={() => navigate("/marketplace-accounts")}>Add a marketplace account</Button>
                }
              />
            }
          >
            <div className="flex flex-col gap-5">
              {formError && (
                <div className="flex items-start gap-2 rounded border border-danger/20 bg-danger-soft px-3.5 py-2.5 text-sm text-danger" role="alert">
                  <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
                  {formError}
                </div>
              )}

              <Select
                label="Marketplace account"
                required
                value={accountId}
                onChange={(e) => setAccountId(e.target.value)}
              >
                <option value="">Select an account…</option>
                {accounts.map((account) => {
                  const marketplace = marketplaceById.get(account.marketplace_id);
                  return (
                    <option key={account.id} value={account.id}>
                      {marketplace?.display_name ?? "Marketplace"} — {account.merchant_id_on_platform}
                    </option>
                  );
                })}
              </Select>

              <div>
                <p className="mb-1.5 text-sm font-medium text-foreground">Settlement file</p>
                <FileDropzone file={file} onFileSelected={setFile} onClear={() => setFile(null)} />
              </div>

              <Button
                onClick={handleSubmit}
                loading={upload.isPending}
                icon={<UploadCloud className="size-4" aria-hidden />}
                size="lg"
              >
                Upload and process
              </Button>

              <p className="text-sm text-muted-foreground">
                Prefer to check past uploads first?{" "}
                <Link to="/settlements" className="font-medium text-primary hover:underline">
                  View settlement history
                </Link>
              </p>
            </div>
          </AsyncState>
        </CardBody>
      </Card>
    </div>
  );
}
