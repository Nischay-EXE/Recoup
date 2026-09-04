import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { motion } from "motion/react"
import {
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  CircleDot,
  Filter,
  Search,
  X,
} from "lucide-react"
import { useNavigate } from "react-router-dom"

import {
  getRecoveryEvents,
  type EventExplorerParams,
} from "../events/eventApi"
import type { RecoveryEvent } from "../../types/recovery"
import { formatDateTime } from "../../lib/formatters"

const PAGE_SIZE = 25

function formatAmount(
  amount: number | null | undefined,
  currency: string | null | undefined,
) {
  if (amount == null) return "—"

  if (currency === "INR") {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(amount)
  }

  return `${amount.toLocaleString()} ${currency ?? ""}`.trim()
}


function shortId(value: string | null | undefined) {
  if (!value) return "—"
  if (value.length <= 24) return value

  return `${value.slice(0, 12)}…${value.slice(-8)}`
}

function eventStatusClass(eventType: string) {
  if (
    eventType.includes("failed") ||
    eventType.includes("cancelled") ||
    eventType.includes("expired")
  ) {
    return "bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-300"
  }

  if (
    eventType.includes("paid") ||
    eventType.includes("captured") ||
    eventType.includes("charged") ||
    eventType.includes("succeeded")
  ) {
    return "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300"
  }

  if (
    eventType.includes("pending") ||
    eventType.includes("created")
  ) {
    return "bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300"
  }

  return "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
}

function objectBadgeClass(objectType: string) {
  if (objectType === "payment") {
    return "bg-emerald-950/70 text-emerald-300 ring-1 ring-inset ring-emerald-800"
  }

  if (objectType === "subscription") {
    return "bg-blue-950/70 text-blue-300 ring-1 ring-inset ring-blue-800"
  }

  if (objectType === "invoice") {
    return "bg-violet-950/70 text-violet-300 ring-1 ring-inset ring-violet-800"
  }

  return "bg-slate-800 text-slate-300 ring-1 ring-inset ring-slate-700"
}

function revenueObject(event: RecoveryEvent) {
  const normalized = event.normalized

  if (normalized?.payment_id) return "payment"
  if (normalized?.subscription_id) return "subscription"
  if (normalized?.invoice_id) return "invoice"

  return "unknown"
}

function DetailValue({
  label,
  value,
  mono = false,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="min-w-0 rounded-xl border border-slate-800 bg-slate-950/70 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </p>
      <p
        className={`mt-1 break-all text-xs text-slate-200 ${
          mono ? "font-mono" : ""
        }`}
      >
        {value}
      </p>
    </div>
  )
}

function EventDetailDialog({
  event,
  onClose,
}: {
  event: RecoveryEvent
  onClose: () => void
}) {
  const navigate = useNavigate()
  const normalized = event.normalized
  const objectType = revenueObject(event)
  const primaryId =
    normalized?.payment_id ??
    normalized?.subscription_id ??
    normalized?.invoice_id ??
    normalized?.order_id

  function openCase() {
    if (!event.recovery_case?.case_id) return
    onClose()
    navigate(`/merchant/cases/${event.recovery_case.case_id}`)
  }

  function openDecision() {
    if (!event.recovery_case?.case_id) return
    onClose()
    navigate(`/developer/decisions/${event.recovery_case.case_id}`)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm"
      role="presentation"
      onMouseDown={(mouseEvent) => {
        if (mouseEvent.target === mouseEvent.currentTarget) onClose()
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 12, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.16 }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="event-detail-title"
        className="max-h-[88vh] w-full max-w-4xl overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl"
      >
        <div className="flex items-start justify-between gap-4 border-b border-slate-800 px-5 py-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold capitalize ${objectBadgeClass(
                  objectType,
                )}`}
              >
                {objectType}
              </span>
              <span
                className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-medium ${eventStatusClass(
                  event.event_type,
                )}`}
              >
                {normalized?.status ?? event.event_type}
              </span>
            </div>
            <h2
              id="event-detail-title"
              className="mt-2 truncate text-lg font-semibold text-white"
            >
              {event.event_type}
            </h2>
            <p
              className="mt-1 break-all font-mono text-[11px] text-slate-500"
              title={event.event_id}
            >
              {event.event_id}
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close event details"
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-700 text-slate-400 transition hover:bg-slate-800 hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="max-h-[calc(88vh-76px)] overflow-y-auto p-5">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <DetailValue label="Source" value={event.source} />
            <DetailValue label="Received" value={formatDateTime(event.received_at)} />
            <DetailValue
              label="Occurred"
              value={formatDateTime(normalized?.occurred_at)}
            />
            <DetailValue
              label="Revenue object"
              value={primaryId ? `${objectType} · ${primaryId}` : "Not resolved"}
              mono={Boolean(primaryId)}
            />
            <DetailValue
              label="Customer"
              value={normalized?.customer_id ?? "Not available"}
              mono={Boolean(normalized?.customer_id)}
            />
            <DetailValue
              label="Amount"
              value={formatAmount(normalized?.amount, normalized?.currency)}
            />
          </div>

          <section className="mt-5 rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  Recovery lineage
                </p>
                <p className="mt-1 text-sm font-medium text-white">
                  {event.recovery_case
                    ? "This event is linked to a recovery case."
                    : event.recovery_case_match === "ambiguous"
                      ? "Multiple cases match this event; lineage is intentionally unresolved."
                      : "No recovery case is linked to this event."}
                </p>
              </div>

              <span
                className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${
                  event.recovery_case_match === "exact"
                    ? "bg-emerald-950/60 text-emerald-300"
                    : event.recovery_case_match === "ambiguous"
                      ? "bg-amber-950/60 text-amber-300"
                      : "bg-slate-800 text-slate-400"
                }`}
              >
                {event.recovery_case_match === "exact"
                  ? "Exact match"
                  : event.recovery_case_match === "ambiguous"
                    ? "Ambiguous match"
                    : "No match"}
              </span>
            </div>

            {event.recovery_case && (
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <DetailValue
                  label="Case"
                  value={event.recovery_case.case_id}
                  mono
                />
                <DetailValue
                  label="Case status"
                  value={event.recovery_case.status}
                />
                <DetailValue
                  label="At risk"
                  value={formatAmount(
                    event.recovery_case.amount_at_risk,
                    normalized?.currency,
                  )}
                />
                <DetailValue
                  label="Recovered"
                  value={formatAmount(
                    event.recovery_case.amount_recovered,
                    normalized?.currency,
                  )}
                />
              </div>
            )}

            {event.recovery_case && (
              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={openCase}
                  className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-blue-500"
                >
                  Open recovery case
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={openDecision}
                  className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:bg-slate-800"
                >
                  Open AI decision trace
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </button>
              </div>
            )}
          </section>

          <section className="mt-5 rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  Normalized event
                </p>
                <p className="mt-1 text-sm font-medium text-white">
                  Canonical revenue context persisted by the recovery engine.
                </p>
              </div>
              <span className="text-xs text-slate-500">
                {event.payload_available
                  ? "Raw payload available"
                  : "Raw payload not exposed"}
              </span>
            </div>

            {normalized ? (
              <pre className="mt-4 overflow-x-auto rounded-xl border border-slate-800 bg-slate-950 p-4 font-mono text-[11px] leading-5 text-slate-300">
                {JSON.stringify(normalized, null, 2)}
              </pre>
            ) : (
              <p className="mt-4 rounded-xl border border-slate-800 bg-slate-950 p-4 text-xs text-slate-500">
                This event does not have a normalized record available.
              </p>
            )}
          </section>
        </div>
      </motion.div>
    </div>
  )
}

function EventRow({
  event,
  onOpen,
}: {
  event: RecoveryEvent
  onOpen: (event: RecoveryEvent) => void
}) {
  const normalized = event.normalized
  const objectType = revenueObject(event)

  const primaryId =
    normalized?.payment_id ??
    normalized?.subscription_id ??
    normalized?.invoice_id ??
    normalized?.order_id

  return (
    <motion.button
      type="button"
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={() => onOpen(event)}
      className="group grid w-full grid-cols-[minmax(240px,1.5fr)_130px_minmax(180px,1fr)_150px_130px] gap-4 border-t border-slate-800 px-5 py-4 text-left transition hover:bg-slate-800/45 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 first:border-t-0"
      aria-label={`Open details for ${event.event_type}`}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <CircleDot className="h-3.5 w-3.5 shrink-0 text-slate-500 transition group-hover:text-blue-400" />

          <span className="truncate text-sm font-medium text-slate-100">
            {event.event_type}
          </span>
        </div>

        <p
          className="mt-1 truncate pl-5 font-mono text-[11px] text-slate-500"
          title={event.event_id}
        >
          {event.event_id}
        </p>
      </div>

      <div>
        <span
          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium capitalize ${objectBadgeClass(
            objectType,
          )}`}
        >
          {objectType}
        </span>
      </div>

      <div className="min-w-0">
        <p
          className="truncate font-mono text-xs text-slate-400"
          title={primaryId ?? undefined}
        >
          {primaryId ? shortId(primaryId) : "No revenue object ID"}
        </p>

        <p
          className="mt-1 truncate font-mono text-xs text-slate-600"
          title={normalized?.customer_id ?? undefined}
        >
          {normalized?.customer_id
            ? shortId(normalized.customer_id)
            : "No customer ID"}
        </p>
      </div>

      <div>
        <p className="text-sm font-medium text-slate-100">
          {formatAmount(normalized?.amount, normalized?.currency)}
        </p>

        <p className="mt-1 text-xs text-slate-500">
          {normalized?.status ?? "—"}
        </p>
      </div>

      <div className="text-right">
        <p className="text-xs text-slate-500">
          {formatDateTime(event.received_at)}
        </p>
        <p className="mt-1 text-[10px] font-medium text-blue-400 opacity-0 transition group-hover:opacity-100">
          View details →
        </p>
      </div>
    </motion.button>
  )
}

export default function DeveloperEventExplorer() {
  const [search, setSearch] = useState("")
  const [eventType, setEventType] = useState("")
  const [revenueObjectType, setRevenueObjectType] = useState("")
  const [page, setPage] = useState(0)
  const [selectedEvent, setSelectedEvent] = useState<RecoveryEvent | null>(
    null,
  )

  const params = useMemo<EventExplorerParams>(
    () => ({
      search: search.trim() || undefined,
      eventType: eventType || undefined,
      revenueObjectType: revenueObjectType || undefined,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    }),
    [search, eventType, revenueObjectType, page],
  )

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["recovery-events", params],
    queryFn: () => getRecoveryEvents(params),
  })

  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / PAGE_SIZE))

  const hasFilters = search.trim() || eventType || revenueObjectType

  function clearFilters() {
    setSearch("")
    setEventType("")
    setRevenueObjectType("")
    setPage(0)
  }

  function changeEventType(value: string) {
    setEventType(value)
    setPage(0)
  }

  function changeRevenueObjectType(value: string) {
    setRevenueObjectType(value)
    setPage(0)
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-blue-400">Developer Console</p>

            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-white">
              Event Explorer
            </h1>

            <p className="mt-2 max-w-2xl text-sm text-slate-400">
              Inspect persisted revenue events and their normalized payment,
              subscription, and invoice context.
            </p>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-3">
            <p className="text-xs text-slate-500">Persisted events</p>

            <p className="mt-1 text-xl font-semibold text-white">
              {data?.total?.toLocaleString("en-IN") ?? "—"}
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row">
          <div className="relative min-w-0 flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />

            <input
              value={search}
              onChange={(event) => {
                setSearch(event.target.value)
                setPage(0)
              }}
              placeholder="Search event, customer, payment, order, subscription or invoice..."
              className="h-10 w-full rounded-xl border border-slate-700 bg-slate-950 pl-9 pr-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-slate-500" />

            <select
              value={eventType}
              onChange={(event) => changeEventType(event.target.value)}
              className="h-10 rounded-xl border border-slate-700 bg-slate-950 px-3 text-sm text-slate-300 outline-none"
            >
              <option value="">All event types</option>
              <option value="payment.failed">payment.failed</option>
              <option value="payment.captured">payment.captured</option>
              <option value="subscription.pending">subscription.pending</option>
              <option value="subscription.charged">subscription.charged</option>
              <option value="invoice.paid">invoice.paid</option>
            </select>

            <select
              value={revenueObjectType}
              onChange={(event) =>
                changeRevenueObjectType(event.target.value)
              }
              className="h-10 rounded-xl border border-slate-700 bg-slate-950 px-3 text-sm text-slate-300 outline-none"
            >
              <option value="">All revenue objects</option>
              <option value="payment">Payment</option>
              <option value="subscription">Subscription</option>
              <option value="invoice">Invoice</option>
            </select>

            {hasFilters && (
              <button
                type="button"
                onClick={clearFilters}
                className="inline-flex h-10 items-center gap-1.5 rounded-xl border border-slate-700 px-3 text-sm text-slate-300 transition hover:bg-slate-800"
              >
                <X className="h-4 w-4" />
                Clear
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900 shadow-sm">
        <div className="grid grid-cols-[minmax(240px,1.5fr)_130px_minmax(180px,1fr)_150px_130px] gap-4 bg-slate-950 px-5 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          <span>Event</span>
          <span>Object</span>
          <span>Revenue context</span>
          <span>Amount / status</span>
          <span className="text-right">Received</span>
        </div>

        {isLoading && (
          <div className="space-y-3 p-5">
            {Array.from({ length: 8 }).map((_, index) => (
              <div
                key={index}
                className="h-14 animate-pulse rounded-xl bg-slate-800"
              />
            ))}
          </div>
        )}

        {isError && !isLoading && (
          <div className="p-10 text-center">
            <p className="text-sm font-medium text-white">Could not load events.</p>

            <button
              type="button"
              onClick={() => refetch()}
              className="mt-3 rounded-lg bg-white px-3 py-2 text-sm font-medium text-slate-900"
            >
              Try again
            </button>
          </div>
        )}

        {!isLoading && !isError && data?.items.length === 0 && (
          <div className="p-10 text-center">
            <p className="text-sm font-medium text-white">No events found.</p>

            <p className="mt-1 text-sm text-slate-500">
              Try changing the search or filters.
            </p>
          </div>
        )}

        {!isLoading &&
          !isError &&
          data?.items.map((event) => (
            <EventRow
              key={event.event_id}
              event={event}
              onOpen={setSelectedEvent}
            />
          ))}

        <div className="flex items-center justify-between border-t border-slate-800 px-5 py-3">
          <p className="text-xs text-slate-500">
            {data?.total
              ? `${data.offset + 1}–${Math.min(
                  data.offset + data.limit,
                  data.total,
                )} of ${data.total}`
              : "0 events"}
          </p>

          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page === 0}
              onClick={() =>
                setPage((current) => Math.max(0, current - 1))
              }
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-700 text-slate-300 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>

            <span className="min-w-16 text-center text-xs font-medium text-slate-400">
              Page {page + 1} / {totalPages}
            </span>

            <button
              type="button"
              disabled={page + 1 >= totalPages}
              onClick={() =>
                setPage((current) => Math.min(totalPages - 1, current + 1))
              }
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-700 text-slate-300 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {selectedEvent && (
        <EventDetailDialog
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      )}
    </div>
  )
}
