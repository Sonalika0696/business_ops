import { AlertTriangle, WifiOff } from "lucide-react";
import { ApiError } from "@/api/client";
import { Button } from "./Button";

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const isNetwork = ApiError.isNetworkFailure(error);
  const message =
    error instanceof ApiError ? error.message : "Something went wrong while loading this data.";

  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
      <div className="flex size-12 items-center justify-center rounded-full bg-danger-soft text-danger">
        {isNetwork ? <WifiOff className="size-6" aria-hidden /> : <AlertTriangle className="size-6" aria-hidden />}
      </div>
      <div className="space-y-1">
        <p className="text-lg font-semibold text-foreground">
          {isNetwork ? "Can't reach the server" : "Couldn't load this"}
        </p>
        <p className="mx-auto max-w-sm text-base text-muted-foreground">{message}</p>
      </div>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
