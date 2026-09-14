import { forwardRef, useId, type SelectHTMLAttributes } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  error?: string;
  helperText?: string;
  hideLabel?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, helperText, hideLabel, id, className, required, children, ...props }, ref) => {
    const autoId = useId();
    const selectId = id ?? autoId;
    const errorId = `${selectId}-error`;
    const helperId = `${selectId}-helper`;

    return (
      <div className="flex flex-col gap-1.5">
        <label htmlFor={selectId} className={cn("text-sm font-medium text-foreground", hideLabel && "sr-only")}>
          {label}
          {required && <span className="text-danger ml-0.5" aria-hidden>*</span>}
        </label>
        <div className="relative">
          <select
            ref={ref}
            id={selectId}
            required={required}
            aria-invalid={Boolean(error) || undefined}
            aria-describedby={error ? errorId : helperText ? helperId : undefined}
            className={cn(
              "h-11 w-full appearance-none rounded border bg-surface pl-3.5 pr-10 text-base text-foreground",
              "transition-colors duration-150",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring",
              error ? "border-danger" : "border-border hover:border-primary-300",
              "disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed",
              className,
            )}
            {...props}
          >
            {children}
          </select>
          <ChevronDown
            className="pointer-events-none absolute right-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
        </div>
        {error ? (
          <p id={errorId} className="text-sm text-danger" role="alert">
            {error}
          </p>
        ) : helperText ? (
          <p id={helperId} className="text-sm text-muted-foreground">
            {helperText}
          </p>
        ) : null}
      </div>
    );
  },
);
Select.displayName = "Select";
