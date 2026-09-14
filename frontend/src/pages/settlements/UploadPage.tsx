import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { UploadCloud, Store, TriangleAlert, FileText, X, CircleCheck, CircleX, Loader2, Info } from "lucide-react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { AsyncState } from "@/components/ui/AsyncState";
import { EmptyState } from "@/components/ui/EmptyState";
import { MultiFileDropzone } from "@/components/settlements/MultiFileDropzone";
import { useMarketplaceAccounts, useMarketplaces } from "@/api/marketplaceAccounts";
import { useUploadSettlement } from "@/api/settlements";
import { ApiError } from "@/api/client";
import { useToast } from "@/components/ui/Toast";
import { peekSettlementFile, type FilePeek } from "@/lib/filePreview";
import { cn } from "@/lib/cn";

type FileStatus = "queued" | "uploading" | "done" | "duplicate" | "error";

interface PendingFile {
  id: string;
  file: File;
  peek: FilePeek | null;
  status: FileStatus;
  reportId?: string;
  errorMessage?: string;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function UploadPage() {
  const navigate = useNavigate();
  const { push } = useToast();
  const accountsQuery = useMarketplaceAccounts();
  const marketplacesQuery = useMarketplaces();
  const upload = useUploadSettlement();

  const [accountId, setAccountId] = useState<string>("");
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([]);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const accounts = accountsQuery.data?.items ?? [];
  const marketplaceById = new Map((marketplacesQuery.data?.items ?? []).map((m) => [m.id, m]));

  const addFiles = async (files: File[]) => {
    const newEntries: PendingFile[] = files.map((file) => ({
      id: `${file.name}-${file.size}-${file.lastModified}`,
      file,
      peek: null,
      status: "queued",
    }));
    setPendingFiles((prev) => [...prev, ...newEntries.filter((e) => !prev.some((p) => p.id === e.id))]);

    for (const entry of newEntries) {
      try {
        const peek = await peekSettlementFile(entry.file);
        setPendingFiles((prev) => prev.map((p) => (p.id === entry.id ? { ...p, peek } : p)));
      } catch {
        // Preview is best-effort only; upload can still proceed without it.
      }
    }
  };

  const removeFile = (id: string) => setPendingFiles((prev) => prev.filter((p) => p.id !== id));

  const handleSubmit = async () => {
    setFormError(null);
    if (!accountId) {
      setFormError("Choose which marketplace account these files belong to.");
      return;
    }
    if (pendingFiles.length === 0) {
      setFormError("Select at least one settlement file to upload.");
      return;
    }

    setIsSubmitting(true);
    let lastReportId: string | null = null;
    // React state updates from setPendingFiles are async/batched, so the
    // `pendingFiles` closure below would still read pre-loop values right
    // after this loop finishes — track outcomes locally instead.
    let failureCount = 0;
    const totalCount = pendingFiles.length;

    for (const entry of pendingFiles) {
      if (entry.status === "done" || entry.status === "duplicate") continue;
      setPendingFiles((prev) => prev.map((p) => (p.id === entry.id ? { ...p, status: "uploading" } : p)));
      try {
        const result = await upload.mutateAsync({ file: entry.file, sellerMarketplaceAccountId: accountId });
        lastReportId = result.settlement_report_id;
        setPendingFiles((prev) =>
          prev.map((p) =>
            p.id === entry.id
              ? { ...p, status: result.duplicate ? "duplicate" : "done", reportId: result.settlement_report_id }
              : p,
          ),
        );
      } catch (err) {
        failureCount += 1;
        setPendingFiles((prev) =>
          prev.map((p) =>
            p.id === entry.id
              ? { ...p, status: "error", errorMessage: err instanceof ApiError ? err.message : "Upload failed." }
              : p,
          ),
        );
      }
    }

    setIsSubmitting(false);

    if (failureCount === 0 && totalCount === 1 && lastReportId) {
      navigate(`/settlements/${lastReportId}`);
      return;
    }
    if (failureCount === 0) {
      push(`${totalCount} file${totalCount === 1 ? "" : "s"} processed — see status below.`);
    } else {
      push(`${failureCount} file${failureCount === 1 ? "" : "s"} failed to upload — see details below.`, "danger");
    }
  };

  const statusIcon: Record<FileStatus, React.ReactNode> = {
    queued: <FileText className="size-4 text-muted-foreground" aria-hidden />,
    uploading: <Loader2 className="size-4 animate-spin text-primary" aria-hidden />,
    done: <CircleCheck className="size-4 text-success" aria-hidden />,
    duplicate: <Info className="size-4 text-info" aria-hidden />,
    error: <CircleX className="size-4 text-danger" aria-hidden />,
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="font-heading text-2xl font-semibold text-foreground">Upload settlement</h1>
        <p className="mt-1 text-base text-muted-foreground">
          Upload one or more marketplace settlement exports for this period to parse and reconcile against your
          orders.
        </p>
      </div>

      <Card className="max-w-3xl">
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
                action={<Button onClick={() => navigate("/marketplace-accounts")}>Add a marketplace account</Button>}
              />
            }
          >
            <div className="flex flex-col gap-5">
              {formError && (
                <div
                  className="flex items-start gap-2 rounded border border-danger/20 bg-danger-soft px-3.5 py-2.5 text-sm text-danger"
                  role="alert"
                >
                  <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
                  {formError}
                </div>
              )}

              <Select label="Marketplace account" required value={accountId} onChange={(e) => setAccountId(e.target.value)}>
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
                <p className="mb-1.5 text-sm font-medium text-foreground">Settlement files</p>
                <MultiFileDropzone onFilesAdded={addFiles} />
              </div>

              {pendingFiles.length > 0 && (
                <div className="flex flex-col gap-2">
                  <p className="text-sm font-medium text-foreground">
                    {pendingFiles.length} file{pendingFiles.length === 1 ? "" : "s"} ready to review
                  </p>
                  <ul className="flex flex-col gap-2">
                    {pendingFiles.map((entry) => (
                      <li
                        key={entry.id}
                        className={cn(
                          "flex items-start gap-3 rounded-md border px-4 py-3",
                          entry.status === "error" ? "border-danger/30 bg-danger-soft/40" : "border-border bg-surface",
                        )}
                      >
                        <div className="mt-0.5 shrink-0">{statusIcon[entry.status]}</div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-base font-medium text-foreground">{entry.file.name}</p>
                          <p className="text-sm text-muted-foreground">
                            {formatBytes(entry.file.size)}
                            {entry.peek && (
                              <>
                                {" · "}
                                ~{entry.peek.approxDataRowCount} rows detected · columns:{" "}
                                {entry.peek.headerColumns.slice(0, 4).join(", ")}
                                {entry.peek.headerColumns.length > 4 ? "…" : ""}
                              </>
                            )}
                          </p>
                          {entry.status === "duplicate" && (
                            <p className="mt-0.5 text-sm text-info">Already uploaded — showing the existing report.</p>
                          )}
                          {entry.status === "error" && entry.errorMessage && (
                            <p className="mt-0.5 text-sm text-danger">{entry.errorMessage}</p>
                          )}
                          {(entry.status === "done" || entry.status === "duplicate") && entry.reportId && (
                            <Link
                              to={`/settlements/${entry.reportId}`}
                              className="mt-0.5 inline-block text-sm font-medium text-primary hover:underline"
                            >
                              View report
                            </Link>
                          )}
                        </div>
                        {entry.status === "queued" && (
                          <button
                            type="button"
                            onClick={() => removeFile(entry.id)}
                            aria-label={`Remove ${entry.file.name}`}
                            className="shrink-0 cursor-pointer rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                          >
                            <X className="size-4" aria-hidden />
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                  <p className="text-sm text-muted-foreground">
                    Row counts above are a quick local peek at each file, not a validated preview — remove anything
                    that doesn't look right before uploading. The backend doesn't yet offer a dry-run step that
                    validates a file without creating a report (flagged in CROSS-SYSTEM-DEPENDENCIES.md); once it
                    does, this preview will show real parse results before you commit.
                  </p>
                </div>
              )}

              <Button
                onClick={handleSubmit}
                loading={isSubmitting}
                icon={<UploadCloud className="size-4" aria-hidden />}
                size="lg"
              >
                {pendingFiles.length > 1 ? `Upload ${pendingFiles.length} files` : "Upload and process"}
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
