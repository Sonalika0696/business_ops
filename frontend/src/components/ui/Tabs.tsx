import { motion } from "framer-motion";
import { cn } from "@/lib/cn";

export interface TabItem {
  key: string;
  label: string;
  count?: number;
}

export function Tabs({
  items,
  active,
  onChange,
  id = "tabs",
}: {
  items: TabItem[];
  active: string;
  onChange: (key: string) => void;
  id?: string;
}) {
  return (
    <div role="tablist" className="flex gap-1 border-b border-border px-2">
      {items.map((item) => {
        const isActive = item.key === active;
        return (
          <button
            key={item.key}
            role="tab"
            aria-selected={isActive}
            type="button"
            onClick={() => onChange(item.key)}
            className={cn(
              "relative flex cursor-pointer items-center gap-2 px-3.5 py-3 text-base font-medium transition-colors duration-150",
              isActive ? "text-primary" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {item.label}
            {item.count !== undefined && (
              <span
                className={cn(
                  "rounded-full px-1.5 py-0.5 text-xs font-semibold tabular-nums transition-colors duration-150",
                  isActive ? "bg-primary-50 text-primary-700" : "bg-muted text-muted-foreground",
                )}
              >
                {item.count}
              </span>
            )}
            {isActive && (
              <motion.span
                layoutId={`${id}-underline`}
                className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-primary"
                transition={{ type: "spring", stiffness: 500, damping: 40 }}
                aria-hidden
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
