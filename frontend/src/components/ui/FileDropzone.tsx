import { useCallback, useId, useRef, useState } from "react";
import type { DragEvent } from "react";
import { motion } from "framer-motion";
import { FileUp, FileText, X } from "lucide-react";
import { cn } from "@/lib/cn";

const MAX_SIZE_BYTES = 25 * 1024 * 1024;

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileDropzone({
  file,
  onFileSelected,
  onClear,
  error,
  accept = ".txt,.csv,.tsv",
}: {
  file: File | null;
  onFileSelected: (file: File) => void;
  onClear: () => void;
  error?: string;
  accept?: string;
}) {
  const [isDragActive, setIsDragActive] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const inputId = useId();

  const validateAndSelect = useCallback(
    (candidate: File) => {
      if (candidate.size > MAX_SIZE_BYTES) {
        setLocalError(`"${candidate.name}" is ${formatBytes(candidate.size)} — the limit is 25 MB.`);
        return;
      }
      setLocalError(null);
      onFileSelected(candidate);
    },
    [onFileSelected],
  );

  const handleDrop = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setIsDragActive(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) validateAndSelect(dropped);
  };

  const effectiveError = error ?? localError ?? undefined;

  if (file) {
    return (
      <div>
        <div className="flex items-center gap-3 rounded-md border border-border bg-surface px-4 py-3.5">
          <div className="flex size-10 shrink-0 items-center justify-center rounded bg-primary-50 text-primary">
            <FileText className="size-5" aria-hidden />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-base font-medium text-foreground">{file.name}</p>
            <p className="text-sm text-muted-foreground">{formatBytes(file.size)}</p>
          </div>
          <button
            type="button"
            onClick={onClear}
            aria-label={`Remove ${file.name}`}
            className="shrink-0 cursor-pointer rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="size-5" aria-hidden />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <motion.label
        htmlFor={inputId}
        animate={{ scale: isDragActive ? 1.015 : 1 }}
        transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragActive(true);
        }}
        onDragLeave={() => setIsDragActive(false)}
        onDrop={handleDrop}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2.5 rounded-md border px-6 py-10 text-center transition-colors duration-150",
          isDragActive ? "border-primary bg-primary-50" : "border-border bg-muted/40 hover:border-primary-300 hover:bg-muted",
        )}
      >
        <div className="flex size-11 items-center justify-center rounded-full bg-primary-50 text-primary">
          <FileUp className="size-5" aria-hidden />
        </div>
        <p className="text-base font-medium text-foreground">
          Drop your settlement file here, or <span className="text-primary underline">browse</span>
        </p>
        <p className="text-sm text-muted-foreground">Tab-separated .txt export, up to 25 MB</p>
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept={accept}
          className="sr-only"
          onChange={(e) => {
            const selected = e.target.files?.[0];
            if (selected) validateAndSelect(selected);
            e.target.value = "";
          }}
        />
      </motion.label>
      {effectiveError && (
        <p className="mt-1.5 text-sm text-danger" role="alert">
          {effectiveError}
        </p>
      )}
    </div>
  );
}
