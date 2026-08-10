/** Formats an astronomical instant without hiding the UTC/local distinction. */
export function formatLocalAndUtcTime(
  value: string | Date,
  timeZone?: string,
  locale?: string,
): string {
  const instant = value instanceof Date ? value : new Date(value);
  const local = new Intl.DateTimeFormat(locale, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
    timeZone,
    timeZoneName: "short",
  }).format(instant);
  const utc = [
    instant.getUTCHours(),
    instant.getUTCMinutes(),
    instant.getUTCSeconds(),
  ].map((part) => String(part).padStart(2, "0")).join(":");
  return `${local} · ${utc} UTC`;
}
