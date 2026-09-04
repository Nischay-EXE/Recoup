const INDIA_TIME_ZONE = "Asia/Kolkata"

function parseBackendDate(value: string) {
  // Backend timestamps are currently persisted as naive UTC datetimes.
  // Treat timezone-less values as UTC; preserve values that already carry
  // an explicit timezone or Z suffix.
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
  return new Date(hasTimezone ? value : `${value}Z`)
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) return "—"

  const date = parseBackendDate(value)
  if (Number.isNaN(date.getTime())) return "Invalid date"

  return new Intl.DateTimeFormat("en-IN", {
    timeZone: INDIA_TIME_ZONE,
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date)
}

export function formatDateShort(value: string | null | undefined) {
  if (!value) return "—"

  const date = parseBackendDate(value)
  if (Number.isNaN(date.getTime())) return "Invalid date"

  return new Intl.DateTimeFormat("en-IN", {
    timeZone: INDIA_TIME_ZONE,
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date)
}
