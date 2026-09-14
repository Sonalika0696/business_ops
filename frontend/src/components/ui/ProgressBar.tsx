import { cn } from "@/lib/cn";

export function ProgressBar({
  value,
  indeterminate,
  tone = "primary",
}: {
  value?: number;
  indeterminate?: boolean;
  tone?: "primary" | "success" | "danger";
}) {
  const barColor = {
    primary: "bg-primary",
    success: "bg-success",
    danger: "bg-danger",
  }[tone];

  return (
    <div
      className="h-2 w-full overflow-hidden rounded-full bg-muted"
      role="progressbar"
      aria-valuenow={indeterminate ? undefined : Math.round(value ?? 0)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      {indeterminate ? (
        <div className={cn("h-full w-1/3 animate-[indeterminate_1.2s_ease-in-out_infinite] rounded-full", barColor)} />
      ) : (
        <div
          className={cn("h-full rounded-full transition-[width] duration-300 ease-out", barColor)}
          style={{ width: `${Math.min(100, Math.max(0, value ?? 0))}%` }}
        />
      )}
      <style>{`
        @keyframes indeterminate {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(300%); }
        }
      `}</style>
    </div>
  );
}
