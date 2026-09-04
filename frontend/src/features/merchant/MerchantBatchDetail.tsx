import { useMemo, useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Link, useNavigate, useParams } from "react-router-dom"
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  BriefcaseBusiness,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  ExternalLink,
  FileJson2,
  Layers3,
  Search,
  Square,
  X,
  type LucideIcon,
} from "lucide-react"

import { apiGet } from "../../lib/api"
import { formatDateTime } from "../../lib/formatters"
import type { RecoveryBatch } from "../../types/batches"
import type {
  RecoveryCase,
  RecoveryCasesResponse,
  RecoveryEvent,
  RecoveryEventsResponse,
} from "../../types/recovery"

const PAGE_SIZE = 25

const currency = (value: number | null | undefined) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value ?? 0)

const label = (value: string | null | undefined) =>
  value
    ? value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())
    : "—"

const metricItems = (batch: RecoveryBatch): Array<[string, string, LucideIcon]> => [
  ["Events", batch.event_count.toLocaleString("en-IN"), Activity],
  ["Payments", batch.payment_count.toLocaleString("en-IN"), CheckCircle2],
  ["Cases", batch.case_count.toLocaleString("en-IN"), BriefcaseBusiness],
  ["Attempts", batch.attempt_count.toLocaleString("en-IN"), Clock3],
  ["At risk", currency(batch.amount_at_risk), Layers3],
  ["Recovered", currency(batch.amount_recovered), CheckCircle2],
]

function Pagination({
  offset,
  total,
  onChange,
}: {
  offset: number
  total: number
  onChange: (offset: number) => void
}) {
  const page = Math.floor(offset / PAGE_SIZE) + 1
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const hasPrevious = offset > 0
  const hasNext = offset + PAGE_SIZE < total

  return (
    <div className="flex items-center justify-between border-t border-slate-200 px-5 py-3 dark:border-slate-800">
      <span className="text-xs text-slate-500 dark:text-slate-400">
        {total === 0 ? "0 items" : `${offset + 1}–${Math.min(offset + PAGE_SIZE, total)} of ${total}`}
      </span>
      <div className="flex items-center gap-2">
        <span className="mr-1 text-xs text-slate-400">Page {page} of {pages}</span>
        <button
          type="button"
          disabled={!hasPrevious}
          onClick={() => onChange(Math.max(0, offset - PAGE_SIZE))}
          className="rounded-lg border border-slate-200 p-1.5 text-slate-500 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:hover:bg-slate-800"
          aria-label="Previous page"
        >
          <ChevronLeft size={15} />
        </button>
        <button
          type="button"
          disabled={!hasNext}
          onClick={() => onChange(offset + PAGE_SIZE)}
          className="rounded-lg border border-slate-200 p-1.5 text-slate-500 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:hover:bg-slate-800"
          aria-label="Next page"
        >
          <ChevronRight size={15} />
        </button>
      </div>
    </div>
  )
}

function EventDetails({
  event,
  onClose,
}: {
  event: RecoveryEvent
  onClose: () => void
}) {
  const normalized = event.normalized

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm">
      <div className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-start justify-between border-b border-slate-200 px-6 py-5 dark:border-slate-800">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-xs font-medium text-blue-600 dark:text-blue-400">
              <Activity size={14} /> Batch event
            </div>
            <h2 className="mt-1 truncate text-lg font-semibold text-slate-950 dark:text-white">
              {label(event.event_type)}
            </h2>
            <p className="mt-1 break-all font-mono text-[11px] text-slate-400">{event.event_id}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="Close event details"
          >
            <X size={18} />
          </button>
        </div>

        <div className="overflow-y-auto p-6">
          <div className="grid gap-3 sm:grid-cols-2">
            <Detail label="Source" value={event.source} />
            <Detail label="Batch" value={event.batch_id ?? "—"} mono />
            <Detail label="Received" value={formatDateTime(event.received_at)} />
            <Detail label="Occurred" value={normalized?.occurred_at ? formatDateTime(normalized.occurred_at) : "—"} />
            <Detail label="Customer" value={normalized?.customer_id} mono />
            <Detail label="Payment" value={normalized?.payment_id} mono />
            <Detail label="Order" value={normalized?.order_id} mono />
            <Detail label="Subscription" value={normalized?.subscription_id} mono />
            <Detail label="Invoice" value={normalized?.invoice_id} mono />
            <Detail label="Amount" value={normalized?.amount != null ? `${currency(normalized.amount)} ${normalized.currency ?? ""}` : "—"} />
            <Detail label="Status" value={label(normalized?.status)} />
            <Detail label="Case match" value={label(event.recovery_case_match)} />
          </div>

          {event.recovery_case && (
            <div className="mt-5 rounded-xl border border-blue-200 bg-blue-50 p-4 dark:border-blue-900/60 dark:bg-blue-950/20">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-blue-600 dark:text-blue-400">Recovery lineage</p>
                  <p className="mt-1 font-mono text-sm text-slate-900 dark:text-white">{event.recovery_case.case_id}</p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {label(event.recovery_case.revenue_object_type)} · {label(event.recovery_case.status)} · attempt #{event.recovery_case.current_attempt}
                  </p>
                </div>
                <Link
                  to={`/merchant/cases/${event.recovery_case.case_id}`}
                  onClick={onClose}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-xs font-medium text-white hover:bg-blue-700"
                >
                  Open case <ExternalLink size={13} />
                </Link>
              </div>
            </div>
          )}

          <div className="mt-5 rounded-xl border border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-3 text-sm font-semibold dark:border-slate-800">
              <FileJson2 size={15} /> Normalized event
            </div>
            <pre className="max-h-72 overflow-auto bg-slate-50 p-4 text-xs leading-5 text-slate-700 dark:bg-slate-950 dark:text-slate-300">
              {JSON.stringify(normalized ?? {}, null, 2)}
            </pre>
          </div>

          {!event.payload_available && (
            <p className="mt-3 text-xs text-slate-400">Raw provider payload is not exposed by the current recovery API.</p>
          )}
        </div>
      </div>
    </div>
  )
}

function Detail({ label: title, value, mono = false }: { label: string; value: string | null | undefined; mono?: boolean }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-950">
      <p className="text-[10px] font-medium uppercase tracking-wide text-slate-400">{title}</p>
      <p className={`mt-1 break-all text-xs text-slate-800 dark:text-slate-200 ${mono ? "font-mono" : ""}`}>{value || "—"}</p>
    </div>
  )
}

function CaseRow({ item }: { item: RecoveryCase }) {
  return (
    <Link
      to={`/merchant/cases/${item.case_id}`}
      className="block border-b border-slate-100 px-5 py-4 last:border-0 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-950"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="break-all text-sm font-medium">{item.case_id}</span>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              {label(item.revenue_object_type)}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">{item.customer_id || "Customer unavailable"}</p>
        </div>
        <span className="shrink-0 text-xs font-medium capitalize text-slate-500">{label(item.status)}</span>
      </div>
      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
        <span>Risk {currency(item.amount_at_risk)}</span>
        <span>Recovered {currency(item.amount_recovered)}</span>
        <span>Remaining {currency(item.amount_remaining)}</span>
        <span>Attempt #{item.current_attempt}</span>
      </div>
    </Link>
  )
}

export default function MerchantBatchDetail() {
  const { batchId = "" } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [closing, setClosing] = useState(false)
  const [eventOffset, setEventOffset] = useState(0)
  const [caseOffset, setCaseOffset] = useState(0)
  const [eventSearch, setEventSearch] = useState("")
  const [selectedEvent, setSelectedEvent] = useState<RecoveryEvent | null>(null)

  const batchQuery = useQuery({
    queryKey: ["recovery-batch", batchId],
    queryFn: () => apiGet<RecoveryBatch>(`/recovery/batches/${batchId}`),
    refetchInterval: 10000,
  })

  const eventsQuery = useQuery({
    queryKey: ["batch-events", batchId, eventOffset],
    queryFn: () => apiGet<RecoveryEventsResponse>(`/recovery/events?batch_id=${encodeURIComponent(batchId)}&limit=${PAGE_SIZE}&offset=${eventOffset}`),
    refetchInterval: 10000,
  })

  const casesQuery = useQuery({
    queryKey: ["batch-cases", batchId, caseOffset],
    queryFn: () => apiGet<RecoveryCasesResponse>(`/recovery/cases?batch_id=${encodeURIComponent(batchId)}&limit=${PAGE_SIZE}&offset=${caseOffset}`),
    refetchInterval: 10000,
  })

  const batch = batchQuery.data
  const events = eventsQuery.data?.items ?? []
  const cases = casesQuery.data?.items ?? []

  const filteredEvents = useMemo(() => {
    const needle = eventSearch.trim().toLowerCase()
    if (!needle) return events
    return events.filter((event) =>
      [event.event_id, event.event_type, event.source, event.normalized?.payment_id, event.normalized?.invoice_id, event.normalized?.subscription_id]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(needle)),
    )
  }, [events, eventSearch])

  async function closeBatch() {
    setClosing(true)
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}/recovery/batches/${encodeURIComponent(batchId)}/close`, { method: "POST" })
      if (!response.ok) throw new Error("Unable to close batch")
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["recovery-batch", batchId] }),
        queryClient.invalidateQueries({ queryKey: ["recovery-batches"] }),
      ])
    } finally {
      setClosing(false)
    }
  }

  if (batchQuery.isLoading) return <div className="p-8 text-sm text-slate-500">Loading batch…</div>
  if (!batch) return <div className="p-8 text-sm text-red-500">Batch not found.</div>

  return (
    <div className="min-h-full bg-slate-50 px-4 py-6 text-slate-900 dark:bg-slate-950 dark:text-slate-100 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-[1600px]">
        <button onClick={() => navigate("/merchant/batches")} className="mb-5 inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white">
          <ArrowLeft size={15} /> Batches
        </button>

        <div className="mb-7 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2 text-sm font-medium text-blue-600 dark:text-blue-400"><Layers3 size={16} /> Recovery Batch</div>
            <h1 className="text-3xl font-semibold tracking-tight">{batch.name}</h1>
            <p className="mt-1 font-mono text-xs text-slate-400">{batch.batch_id}</p>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Started {formatDateTime(batch.started_at)}{batch.ended_at ? ` · ended ${formatDateTime(batch.ended_at)}` : " · live"}</p>
          </div>
          <div className="flex items-center gap-2">
            {batch.status === "active" && (
              <button onClick={closeBatch} disabled={closing} className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:bg-slate-800">
                <Square size={14} /> {closing ? "Closing…" : "Close batch"}
              </button>
            )}
            <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium ${batch.status === "active" ? "bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"}`}>
              <span className="h-1.5 w-1.5 rounded-full bg-current" /> {batch.status === "active" ? "Active" : "Completed"}
            </span>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
          {metricItems(batch).map(([title, value, Icon]) => (
            <div key={title} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-center gap-2 text-slate-400"><Icon size={16} /><span className="text-xs font-medium">{title}</span></div>
              <p className="mt-3 text-xl font-semibold">{value}</p>
            </div>
          ))}
        </div>

        <div className="mt-6 grid gap-6 xl:grid-cols-[1.1fr_1fr]">
          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-800">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="font-semibold">Batch events</h2>
                  <p className="mt-1 text-xs text-slate-500">Every event assigned to this batch. Click any event to inspect its normalized data and recovery lineage.</p>
                </div>
                <span className="shrink-0 text-xs text-slate-400">{eventsQuery.data?.total ?? 0} total</span>
              </div>
              <div className="relative mt-4">
                <Search className="absolute left-3 top-2.5 text-slate-400" size={15} />
                <input value={eventSearch} onChange={(e) => setEventSearch(e.target.value)} placeholder="Search this page by event, payment, invoice…" className="h-9 w-full rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-3 text-xs outline-none focus:border-blue-400 dark:border-slate-700 dark:bg-slate-950" />
              </div>
            </div>
            <div className="max-h-[620px] overflow-y-auto">
              {eventsQuery.isLoading ? <div className="p-10 text-center text-sm text-slate-500">Loading events…</div> : filteredEvents.length === 0 ? <div className="p-10 text-center text-sm text-slate-500">No matching events on this page.</div> : filteredEvents.map((event) => (
                <button key={event.event_id} type="button" onClick={() => setSelectedEvent(event)} className="block w-full border-b border-slate-100 px-5 py-4 text-left last:border-0 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-950">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="text-sm font-medium">{label(event.event_type)}</p>
                      <p className="mt-1 truncate font-mono text-[11px] text-slate-400">{event.event_id}</p>
                    </div>
                    <span className="shrink-0 text-xs text-slate-400">{formatDateTime(event.received_at)}</span>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
                    <span className="font-mono">{event.normalized?.payment_id || event.normalized?.invoice_id || event.normalized?.subscription_id || "No revenue ID"}</span>
                    <span>{event.normalized?.amount != null ? currency(event.normalized.amount) : "—"}</span>
                    <span>{event.recovery_case_match === "exact" ? "Case matched" : event.recovery_case_match === "ambiguous" ? "Ambiguous case" : "No case"}</span>
                    <span className="ml-auto inline-flex items-center gap-1 text-blue-600 dark:text-blue-400">Inspect <ArrowRight size={12} /></span>
                  </div>
                </button>
              ))}
            </div>
            <Pagination offset={eventOffset} total={eventsQuery.data?.total ?? 0} onChange={(next) => { setEventOffset(next); setEventSearch("") }} />
          </section>

          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-800">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="font-semibold">Recovery cases</h2>
                  <p className="mt-1 text-xs text-slate-500">Open a case to inspect the full recovery timeline, decisions, attempts and outcomes.</p>
                </div>
                <span className="shrink-0 text-xs text-slate-400">{casesQuery.data?.total ?? 0} total</span>
              </div>
            </div>
            <div className="max-h-[680px] overflow-y-auto">
              {casesQuery.isLoading ? <div className="p-10 text-center text-sm text-slate-500">Loading cases…</div> : cases.length === 0 ? <div className="p-10 text-center text-sm text-slate-500">No recovery cases yet.</div> : cases.map((item) => <CaseRow key={item.case_id} item={item} />)}
            </div>
            <Pagination offset={caseOffset} total={casesQuery.data?.total ?? 0} onChange={setCaseOffset} />
          </section>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-slate-400">
          <span className="inline-flex items-center gap-2"><Activity size={14} /> Batch membership is persisted; historical records remain untouched.</span>
          <Link to="/developer/events" className="inline-flex items-center gap-1 text-blue-600 hover:underline dark:text-blue-400">Open Developer Event Explorer <ExternalLink size={12} /></Link>
        </div>
      </div>

      {selectedEvent && <EventDetails event={selectedEvent} onClose={() => setSelectedEvent(null)} />}
    </div>
  )
}
