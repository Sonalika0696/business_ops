/**
 * The API stores/returns UTC ISO8601 (DESIGN.md §1). IST display is a
 * frontend-only concern (ARCHITECTURE.md §6) — centralized here so no
 * screen hand-rolls a timezone offset.
 */

const IST_TIMEZONE = "Asia/Kolkata";

const dateTimeFormatter = new Intl.DateTimeFormat("en-IN", {
  timeZone: IST_TIMEZONE,
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: true,
});

const dateFormatter = new Intl.DateTimeFormat("en-IN", {
  timeZone: IST_TIMEZONE,
  day: "2-digit",
  month: "short",
  year: "numeric",
});

const relativeFormatter = new Intl.RelativeTimeFormat("en-IN", { numeric: "auto" });

export function formatDateTimeIST(iso: string | null | undefined): string {
  if (!iso) return "—";
  return `${dateTimeFormatter.format(new Date(iso))} IST`;
}

export function formatDateIST(iso: string | null | undefined): string {
  if (!iso) return "—";
  return dateFormatter.format(new Date(iso));
}

export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return "—";
  const diffMs = new Date(iso).getTime() - Date.now();
  const diffMinutes = Math.round(diffMs / 60000);
  if (Math.abs(diffMinutes) < 60) return relativeFormatter.format(diffMinutes, "minute");
  const diffHours = Math.round(diffMinutes / 60);
  if (Math.abs(diffHours) < 24) return relativeFormatter.format(diffHours, "hour");
  const diffDays = Math.round(diffHours / 24);
  return relativeFormatter.format(diffDays, "day");
}
