import type { RejectedRowDetail } from "@/api/types";

export function RejectedRowsPanel({ rows }: { rows: RejectedRowDetail[] }) {
  return (
    <ul className="flex flex-col gap-3 p-5">
      {rows.map((row) => (
        <li key={row.row_number} className="rounded border border-danger/20 bg-danger-soft/40 p-4">
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm font-semibold text-danger">Row {row.row_number}</span>
          </div>
          <p className="mt-1 text-base text-foreground">{row.reason}</p>
          <dl className="mt-2.5 grid grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-2">
            {Object.entries(row.raw_row).map(([key, value]) => (
              <div key={key} className="flex gap-1.5 text-sm">
                <dt className="shrink-0 text-muted-foreground">{key}:</dt>
                <dd className="truncate font-mono text-xs text-foreground">{String(value)}</dd>
              </div>
            ))}
          </dl>
        </li>
      ))}
    </ul>
  );
}
