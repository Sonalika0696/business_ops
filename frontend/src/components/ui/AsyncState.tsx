import type { ReactNode } from "react";
import { Spinner } from "./Spinner";
import { ErrorState } from "./ErrorState";

interface AsyncStateProps {
  isLoading: boolean;
  isError: boolean;
  error?: unknown;
  onRetry?: () => void;
  isEmpty?: boolean;
  emptyState?: ReactNode;
  children: ReactNode;
  loadingLabel?: string;
}

/**
 * The one place the four canonical states (loading / error / empty /
 * success) are rendered consistently (frontend/PLAN.md's cross-cutting
 * rule) — every list/detail screen wraps its content in this instead of
 * hand-rolling the same four branches.
 */
export function AsyncState({
  isLoading,
  isError,
  error,
  onRetry,
  isEmpty,
  emptyState,
  children,
  loadingLabel = "Loading",
}: AsyncStateProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Spinner className="size-7" label={loadingLabel} />
      </div>
    );
  }
  if (isError) {
    return <ErrorState error={error} onRetry={onRetry} />;
  }
  if (isEmpty && emptyState) {
    return <>{emptyState}</>;
  }
  return <>{children}</>;
}
