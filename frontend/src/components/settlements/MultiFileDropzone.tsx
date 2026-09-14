import { useId, useRef, useState, type DragEvent } from "react";
import { FileUp } from "lucide-react";
import { cn } from "@/lib/cn";

export function MultiFileDropzone({ onFilesAdded, accept = ".txt,.csv,.tsv" }: { onFilesAdded: (files: File[]) => void; accept?: string }) {
  const [isDragActive, setIsDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const inputId = useId();

  const handleDrop = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setIsDragActive(false);
    if (e.dataTransfer.files?.length) onFilesAdded(Array.from(e.dataTransfer.files));
  };

  return (
    <label
      htmlFor={inputId}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragActive(true);
      }}
      onDragLeave={() => setIsDragActive(false)}
      onDrop={handleDrop}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-2.5 rounded-md border-2 border-dashed px-6 py-8 text-center transition-colors duration-150",
        isDragActive ? "border-primary bg-primary-50" : "border-border hover:border-primary-300 hover:bg-muted",
      )}
    >
      <div className="flex size-10 items-center justify-center rounded-full bg-primary-50 text-primary">
        <FileUp className="size-5" aria-hidden />
      </div>
      <p className="text-base font-medium text-foreground">
        Drop settlement files here, or <span className="text-primary underline">browse</span>
      </p>
      <p className="text-sm text-muted-foreground">One file per marketplace payout split — select as many as you have for this period</p>
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        multiple
        accept={accept}
        className="sr-only"
        onChange={(e) => {
          if (e.target.files?.length) onFilesAdded(Array.from(e.target.files));
          e.target.value = "";
        }}
      />
    </label>
  );
}
