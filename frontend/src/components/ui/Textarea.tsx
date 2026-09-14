import { forwardRef, useId, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  error?: string;
  helperText?: string;
  hideLabel?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, helperText, hideLabel, id, className, required, rows = 3, ...props }, ref) => {
    const autoId = useId();
    const textareaId = id ?? autoId;
    const errorId = `${textareaId}-error`;
    const helperId = `${textareaId}-helper`;

    return (
      <div className="flex flex-col gap-1.5">
        <label htmlFor={textareaId} className={cn("text-sm font-medium text-foreground", hideLabel && "sr-only")}>
          {label}
          {required && <span className="text-danger ml-0.5" aria-hidden>*</span>}
        </label>
        <textarea
          ref={ref}
          id={textareaId}
          rows={rows}
          required={required}
          aria-invalid={Boolean(error) || undefined}
          aria-describedby={error ? errorId : helperText ? helperId : undefined}
          className={cn(
            "rounded border bg-surface px-3.5 py-2.5 text-base text-foreground placeholder:text-muted-foreground",
            "transition-colors duration-150 resize-y",
            "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-ring",
            error ? "border-danger" : "border-border hover:border-primary-300",
            className,
          )}
          {...props}
        />
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
Textarea.displayName = "Textarea";
