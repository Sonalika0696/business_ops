import { useState } from "react";
import { Download, FileUp, CircleCheck, CircleX, Loader2, TriangleAlert } from "lucide-react";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { useCreateProduct } from "@/api/products";
import { useToast } from "@/components/ui/Toast";
import { ApiError } from "@/api/client";
import { cn } from "@/lib/cn";
import { buildProductCsvTemplate, parseProductCsv, type ParsedProductRow } from "@/lib/productCsv";

type RowOutcome = "pending" | "importing" | "created" | "failed" | "skipped";

interface ImportRow extends ParsedProductRow {
  outcome: RowOutcome;
  apiError?: string;
}

function downloadTemplate() {
  const blob = new Blob([buildProductCsvTemplate()], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "product-import-template.csv";
  link.click();
  URL.revokeObjectURL(url);
}

export function ProductBulkImportDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [rows, setRows] = useState<ImportRow[]>([]);
  const [isImporting, setIsImporting] = useState(false);
  const createProduct = useCreateProduct();
  const { push } = useToast();

  const handleFile = async (file: File) => {
    const text = await file.text();
    const parsed = parseProductCsv(text);
    setRows(parsed.map((row) => ({ ...row, outcome: row.errors.length > 0 ? "skipped" : "pending" })));
  };

  const handleClose = () => {
    if (isImporting) return;
    setRows([]);
    onClose();
  };

  const validCount = rows.filter((r) => r.outcome === "pending").length;
  const skippedCount = rows.filter((r) => r.outcome === "skipped").length;

  const handleImport = async () => {
    setIsImporting(true);
    let created = 0;
    let failed = 0;

    for (const row of rows) {
      if (row.outcome !== "pending" || !row.data) continue;
      setRows((prev) => prev.map((r) => (r.rowNumber === row.rowNumber ? { ...r, outcome: "importing" } : r)));
      try {
        await createProduct.mutateAsync(row.data);
        created += 1;
        setRows((prev) => prev.map((r) => (r.rowNumber === row.rowNumber ? { ...r, outcome: "created" } : r)));
      } catch (err) {
        failed += 1;
        const message = err instanceof ApiError ? err.message : "Failed to create this product.";
        setRows((prev) => prev.map((r) => (r.rowNumber === row.rowNumber ? { ...r, outcome: "failed", apiError: message } : r)));
      }
    }

    setIsImporting(false);
    if (failed === 0) {
      push(`${created} product${created === 1 ? "" : "s"} imported.`);
    } else {
      push(`${created} imported, ${failed} failed — see details below.`, failed > 0 ? "danger" : "success");
    }
  };

  const statusIcon: Record<RowOutcome, React.ReactNode> = {
    pending: null,
    importing: <Loader2 className="size-4 animate-spin text-primary" aria-hidden />,
    created: <CircleCheck className="size-4 text-success" aria-hidden />,
    failed: <CircleX className="size-4 text-danger" aria-hidden />,
    skipped: <TriangleAlert className="size-4 text-warning" aria-hidden />,
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      title="Bulk import products"
      footer={
        rows.length > 0 ? (
          <>
            <Button variant="secondary" onClick={handleClose} disabled={isImporting}>
              {rows.some((r) => r.outcome === "created" || r.outcome === "failed") ? "Close" : "Cancel"}
            </Button>
            {validCount > 0 && (
              <Button onClick={handleImport} loading={isImporting} disabled={rows.every((r) => r.outcome !== "pending")}>
                Import {validCount} product{validCount === 1 ? "" : "s"}
              </Button>
            )}
          </>
        ) : (
          <Button variant="secondary" onClick={handleClose}>
            Cancel
          </Button>
        )
      }
    >
      <div className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-3 rounded-md border border-border bg-muted/50 px-4 py-3">
          <p className="text-sm text-muted-foreground">
            Columns: <code className="font-mono text-xs">internal_sku, product_name, mrp, cost_price, gst_rate</code>,
            plus optional <code className="font-mono text-xs">hsn_code, category_primary, category_sub, weight_grams</code>.
            Prices are in rupees.
          </p>
          <Button variant="ghost" size="sm" onClick={downloadTemplate} icon={<Download className="size-3.5" aria-hidden />}>
            Template
          </Button>
        </div>

        {rows.length === 0 ? (
          <label
            htmlFor="product-csv-input"
            className="flex cursor-pointer flex-col items-center justify-center gap-2.5 rounded-md border-2 border-dashed border-border px-6 py-8 text-center transition-colors duration-150 hover:border-primary-300 hover:bg-muted"
          >
            <div className="flex size-10 items-center justify-center rounded-full bg-primary-50 text-primary">
              <FileUp className="size-5" aria-hidden />
            </div>
            <p className="text-base font-medium text-foreground">
              Drop a CSV here, or <span className="text-primary underline">browse</span>
            </p>
            <input
              id="product-csv-input"
              type="file"
              accept=".csv"
              className="sr-only"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFile(file);
                e.target.value = "";
              }}
            />
          </label>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="font-medium text-foreground">{rows.length} rows read</span>
              {validCount > 0 && <span className="text-muted-foreground">· {validCount} ready to import</span>}
              {skippedCount > 0 && <span className="text-warning">· {skippedCount} skipped (fix and re-upload)</span>}
            </div>
            <div className="max-h-80 overflow-y-auto rounded-md border border-border">
              <table className="w-full text-left">
                <thead className="sticky top-0 bg-surface">
                  <tr className="border-b border-border text-sm text-muted-foreground">
                    <th className="py-2 pl-3 pr-2 font-medium">Row</th>
                    <th className="px-2 py-2 font-medium">SKU</th>
                    <th className="px-2 py-2 font-medium">Product</th>
                    <th className="py-2 pl-2 pr-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.rowNumber} className={cn("border-b border-border last:border-0", row.outcome === "skipped" && "bg-warning-soft/40")}>
                      <td className="py-2 pl-3 pr-2 text-sm tabular-nums text-muted-foreground">{row.rowNumber}</td>
                      <td className="px-2 py-2 font-mono text-sm text-foreground">{row.raw.internal_sku || "—"}</td>
                      <td className="px-2 py-2 text-sm text-foreground">{row.raw.product_name || "—"}</td>
                      <td className="py-2 pl-2 pr-3">
                        <div className="flex items-center gap-1.5 text-sm">
                          {statusIcon[row.outcome]}
                          {row.outcome === "skipped" && <span className="text-warning">{row.errors.join("; ")}</span>}
                          {row.outcome === "failed" && <span className="text-danger">{row.apiError}</span>}
                          {row.outcome === "created" && <span className="text-success">Created</span>}
                          {row.outcome === "pending" && <span className="text-muted-foreground">Ready</span>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </Dialog>
  );
}
