import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "./Button";
import { formatNumber } from "@/lib/number";

export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  return (
    <div className="flex items-center justify-between border-t border-border px-5 py-3.5">
      <p className="text-sm text-muted-foreground">
        Showing <span className="tabular-nums font-medium text-foreground">{formatNumber(start)}</span>–
        <span className="tabular-nums font-medium text-foreground">{formatNumber(end)}</span> of{" "}
        <span className="tabular-nums font-medium text-foreground">{formatNumber(total)}</span>
      </p>
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          aria-label="Previous page"
        >
          <ChevronLeft className="size-4" aria-hidden />
          Previous
        </Button>
        <span className="text-sm tabular-nums text-muted-foreground px-1">
          Page {page} of {totalPages}
        </span>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          aria-label="Next page"
        >
          Next
          <ChevronRight className="size-4" aria-hidden />
        </Button>
      </div>
    </div>
  );
}
