import { useState, type ReactNode } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate, useParams } from "react-router-dom"
import {
  Activity,
  ArrowLeft,
  BriefcaseBusiness,
  CheckCircle2,
  Clock3,
  FileJson,
  Layers3,
  RotateCcw,
  Square,
  Trash2,
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
  RecoveryEventDetail,
  RecoveryEventsResponse,
} from "../../types/recovery"

const currency = (value: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value)

const label = (value: string) =>
  value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())

type MetricKey = "events" | "cases" | "risk" | "recovered"

function DetailModal({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children: ReactNode
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4" onMouseDown={onClose}>
      <div
        className="max-h-[88vh] w-full max-w-4xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-900"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 dark:border-slate-800">
          <h2 className="font-semibold">{title}</h2>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"><X size={18} /></button>
        </div>
        <div className="max-h-[calc(88vh-65px)] overflow-y-auto p-5">{children}</div>
      </div>
    </div>
  )
}

function MetricCard({
  title,
  value,
  Icon,
  clickable,
  onClick,
}: {
  title: string
  value: string
  Icon: LucideIcon
  clickable: boolean
  onClick?: () => void
}) {
  const content = (
    <>
      <div className="flex items-center gap-2 text-slate-400">
        <Icon size={16} />
        <span className="text-xs font-medium">{title}</span>
      </div>
      <p className="mt-3 text-xl font-semibold">{value}</p>
      {clickable && <p className="mt-1 text-[11px] font-medium text-blue-600 dark:text-blue-400">View details →</p>}
    </>
  )
  if (!clickable) {
    return <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">{content}</div>
  }
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-blue-700"
    >
      {content}
    </button>
  )
}

function CaseList({
  cases,
  empty,
  onCase,
}: {
  cases: RecoveryCase[]
  empty: string
  onCase: (item: RecoveryCase) => void
}) {
  if (!cases.length) return <p className="py-10 text-center text-sm text-slate-500">{empty}</p>
  return (
    <div className="divide-y divide-slate-100 dark:divide-slate-800">
      {cases.map((item) => (
        <button key={item.case_id} type="button" onClick={() => onCase(item)} className="block w-full px-2 py-4 text-left hover:bg-slate-50 dark:hover:bg-slate-950">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold">{item.case_id}</p>
              <p className="mt-1 text-xs text-slate-500">{label(item.revenue_object_type)} · {item.customer_id || "Customer unavailable"}</p>
            </div>
            <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-medium dark:bg-slate-800">{label(item.status)}</span>
          </div>
          <div className="mt-3 flex flex-wrap gap-5 text-xs text-slate-500 dark:text-slate-400">
            <span>At risk {currency(item.amount_at_risk)}</span>
            <span>Recovered {currency(item.amount_recovered)}</span>
            <span>Remaining {currency(item.amount_remaining)}</span>
            <span>Attempt {item.current_attempt}</span>
          </div>
        </button>
      ))}
    </div>
  )
}

export default function MerchantBatchDetail() {
  const { batchId = "" } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [busy, setBusy] = useState(false)
  const [modal, setModal] = useState<MetricKey | "event" | "case" | null>(null)
  const [selectedEvent, setSelectedEvent] = useState<RecoveryEventDetail | null>(null)
  const [eventLoading, setEventLoading] = useState(false)

  const batchQuery = useQuery({ queryKey: ["recovery-batch", batchId], queryFn: () => apiGet<RecoveryBatch>(`/recovery/batches/${batchId}`), refetchInterval: 10000 })
  const eventsQuery = useQuery({ queryKey: ["batch-events", batchId], queryFn: () => apiGet<RecoveryEventsResponse>(`/recovery/events?batch_id=${encodeURIComponent(batchId)}&limit=100&offset=0`), refetchInterval: 10000 })
  const casesQuery = useQuery({ queryKey: ["batch-cases", batchId], queryFn: () => apiGet<RecoveryCasesResponse>(`/recovery/cases?batch_id=${encodeURIComponent(batchId)}&limit=100&offset=0`), refetchInterval: 10000 })

  const batch = batchQuery.data
  const events = eventsQuery.data?.items ?? []
  const cases = casesQuery.data?.items ?? []

  async function toggleBatch() {
    if (!batch) return
    const active = batch.status === "active"
    const action = active ? "disable" : "enable"
    const message = active
      ? `Disable "${batch.name}"?\n\nNew incoming events will no longer be assigned to this batch. Existing records stay intact.`
      : `Enable "${batch.name}"?\n\nNew incoming events will be assigned to this batch. Another active batch cannot exist at the same time.`
    if (!window.confirm(message)) return
    setBusy(true)
    try {
      const endpoint = active ? "close" : "open"
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}/recovery/batches/${encodeURIComponent(batchId)}/${endpoint}`, { method: "POST" })
      if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new Error(body?.detail || `Unable to ${action} batch`)
      }
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["recovery-batch", batchId] }),
        queryClient.invalidateQueries({ queryKey: ["recovery-batches"] }),
      ])
    } catch (error) {
      window.alert(error instanceof Error ? error.message : `Unable to ${action} batch`)
    } finally {
      setBusy(false)
    }
  }

  async function deleteBatch() {
    if (!window.confirm(`Delete "${batch?.name}"?\n\nThis removes only the batch boundary. Events, cases, attempts, decisions, and audit history are NOT deleted.`)) return
    setBusy(true)
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}/recovery/batches/${encodeURIComponent(batchId)}`, { method: "DELETE" })
      if (!response.ok) throw new Error("Unable to delete batch")
      navigate("/merchant/batches")
      await queryClient.invalidateQueries({ queryKey: ["recovery-batches"] })
    } finally {
      setBusy(false)
    }
  }

  async function openEvent(event: RecoveryEvent) {
    setEventLoading(true)
    setModal("event")
    try {
      const detail = await apiGet<RecoveryEventDetail>(`/recovery/events/${encodeURIComponent(event.event_id)}`)
      setSelectedEvent(detail)
    } finally {
      setEventLoading(false)
    }
  }

  function openCase(item: RecoveryCase) {
    navigate(`/merchant/cases/${encodeURIComponent(item.case_id)}`)
  }

  if (batchQuery.isLoading) return <div className="p-8 text-sm text-slate-500">Loading batch…</div>
  if (!batch) return <div className="p-8 text-sm text-red-500">Batch not found.</div>

  const atRiskCases = cases.filter((item) => item.amount_remaining > 0)
  const recoveredCases = cases.filter((item) => item.amount_recovered > 0)

  const metricItems: Array<{ key: MetricKey; title: string; value: string; Icon: LucideIcon; clickable: boolean }> = [
    { key: "events", title: "Events", value: batch.event_count.toLocaleString("en-IN"), Icon: Activity, clickable: true },
    { key: "cases", title: "Cases", value: batch.case_count.toLocaleString("en-IN"), Icon: BriefcaseBusiness, clickable: true },
    { key: "risk", title: "At risk", value: currency(batch.amount_at_risk), Icon: Layers3, clickable: true },
    { key: "recovered", title: "Recovered", value: currency(batch.amount_recovered), Icon: CheckCircle2, clickable: true },
  ]

  return (
    <div className="min-h-full bg-slate-50 px-4 py-6 text-slate-900 dark:bg-slate-950 dark:text-slate-100 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-[1600px]">
        <button onClick={() => navigate("/merchant/batches")} className="mb-5 inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"><ArrowLeft size={15}/>Batches</button>

        <div className="mb-7 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2 text-sm font-medium text-blue-600 dark:text-blue-400"><Layers3 size={16}/>Recovery Batch</div>
            <h1 className="text-3xl font-semibold tracking-tight">{batch.name}</h1>
            <p className="mt-1 font-mono text-xs text-slate-400">{batch.batch_id}</p>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Started {formatDateTime(batch.started_at)}{batch.ended_at ? ` · disabled ${formatDateTime(batch.ended_at)}` : " · live"}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button onClick={toggleBatch} disabled={busy} className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:bg-slate-800">{batch.status === "active" ? <Square size={14}/> : <RotateCcw size={14}/>} {busy ? "Working…" : batch.status === "active" ? "Disable batch" : "Enable batch"}</button>
            {batch.status !== "active" && <button onClick={deleteBatch} disabled={busy} className="inline-flex h-10 items-center gap-2 rounded-xl border border-red-200 bg-white px-4 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50 dark:border-red-900/60 dark:bg-slate-900 dark:text-red-300 dark:hover:bg-red-950/30"><Trash2 size={14}/>{busy ? "Deleting…" : "Delete batch"}</button>}
            <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium ${batch.status === "active" ? "bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"}`}><span className="h-1.5 w-1.5 rounded-full bg-current"/>{batch.status === "active" ? "Active" : "Disabled"}</span>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
          {metricItems.map((item) => (
            <MetricCard key={item.key} title={item.title} value={item.value} Icon={item.Icon} clickable={item.clickable} onClick={() => setModal(item.key)} />
          ))}
          <MetricCard title="Payments" value={batch.payment_count.toLocaleString("en-IN")} Icon={CheckCircle2} clickable={false} />
          <MetricCard title="Attempts" value={batch.attempt_count.toLocaleString("en-IN")} Icon={Clock3} clickable={false} />
        </div>

        <div className="mt-6 grid gap-6 xl:grid-cols-[1.1fr_1fr]">
          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-800">
              <div className="flex items-center justify-between">
                <div><h2 className="font-semibold">Batch events</h2><p className="mt-1 text-xs text-slate-500">Click an event to inspect the persisted webhook payload and lineage.</p></div>
                <span className="text-xs text-slate-400">{eventsQuery.data?.total ?? 0} total</span>
              </div>
            </div>
            <div className="max-h-[600px] overflow-y-auto">
              {events.length === 0 ? <div className="p-10 text-center text-sm text-slate-500">No events yet.</div> : events.map((event) => (
                <button key={event.event_id} type="button" onClick={() => openEvent(event)} className="block w-full border-b border-slate-100 px-5 py-4 text-left last:border-0 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-950">
                  <div className="flex items-start justify-between gap-4"><div><p className="text-sm font-medium">{label(event.event_type)}</p><p className="mt-1 font-mono text-[11px] text-slate-400">{event.event_id}</p></div><span className="text-xs text-slate-400">{formatDateTime(event.received_at)}</span></div>
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400"><span>{event.normalized?.payment_id || event.normalized?.invoice_id || event.normalized?.subscription_id || "No revenue ID"}</span><span>{event.normalized?.amount != null ? currency(event.normalized.amount) : "—"}</span><span>{event.recovery_case_match === "exact" ? "Case matched" : event.recovery_case_match === "ambiguous" ? "Ambiguous case" : "No case"}</span></div>
                </button>
              ))}
            </div>
          </section>

          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-800"><div className="flex items-center justify-between"><div><h2 className="font-semibold">Recovery cases</h2><p className="mt-1 text-xs text-slate-500">Click a case to open its full recovery timeline.</p></div><span className="text-xs text-slate-400">{casesQuery.data?.total ?? 0} total</span></div></div>
            <div className="max-h-[600px] overflow-y-auto">
              <CaseList cases={cases} empty="No recovery cases yet." onCase={openCase} />
            </div>
          </section>
        </div>
      </div>

      {modal === "events" && <DetailModal title={`Batch events · ${events.length}`} onClose={() => setModal(null)}><div className="divide-y divide-slate-100 dark:divide-slate-800">{events.map((event) => <button key={event.event_id} type="button" onClick={() => openEvent(event)} className="block w-full px-2 py-4 text-left hover:bg-slate-50 dark:hover:bg-slate-950"><p className="text-sm font-semibold">{label(event.event_type)}</p><p className="mt-1 font-mono text-[11px] text-slate-400">{event.event_id}</p><p className="mt-2 text-xs text-slate-500">{formatDateTime(event.received_at)}</p></button>)}</div></DetailModal>}

      {modal === "cases" && <DetailModal title={`Recovery cases · ${cases.length}`} onClose={() => setModal(null)}><CaseList cases={cases} empty="No recovery cases in this batch." onCase={openCase} /></DetailModal>}

      {modal === "risk" && <DetailModal title={`At risk · ${atRiskCases.length} cases`} onClose={() => setModal(null)}><CaseList cases={atRiskCases} empty="No outstanding recovery cases." onCase={openCase} /></DetailModal>}

      {modal === "recovered" && <DetailModal title={`Recovered · ${recoveredCases.length} cases`} onClose={() => setModal(null)}><CaseList cases={recoveredCases} empty="No recovered cases in this batch." onCase={openCase} /></DetailModal>}

      {modal === "event" && <DetailModal title={selectedEvent ? label(selectedEvent.event_type) : "Event detail"} onClose={() => { setModal(null); setSelectedEvent(null) }}>
        {eventLoading && <p className="py-10 text-center text-sm text-slate-500">Loading event…</p>}
        {!eventLoading && selectedEvent && (
          <div className="space-y-5">
            <div className="grid gap-4 rounded-xl bg-slate-50 p-4 dark:bg-slate-950 md:grid-cols-2">
              <div><p className="text-xs text-slate-400">Event ID</p><p className="mt-1 break-all font-mono text-sm">{selectedEvent.event_id}</p></div>
              <div><p className="text-xs text-slate-400">Received</p><p className="mt-1 text-sm font-medium">{formatDateTime(selectedEvent.received_at)}</p></div>
              <div><p className="text-xs text-slate-400">Revenue object</p><p className="mt-1 text-sm font-medium">{selectedEvent.normalized?.payment_id ? "Payment" : selectedEvent.normalized?.invoice_id ? "Invoice" : selectedEvent.normalized?.subscription_id ? "Subscription" : "Unknown"}</p></div>
              <div><p className="text-xs text-slate-400">Recovery case</p><p className="mt-1 text-sm font-medium">{selectedEvent.recovery_case?.case_id || "No linked case"}</p></div>
              {selectedEvent.normalized?.payment_id && <div><p className="text-xs text-slate-400">Payment ID</p><p className="mt-1 break-all font-mono text-sm">{selectedEvent.normalized.payment_id}</p></div>}
              {selectedEvent.normalized?.order_id && <div><p className="text-xs text-slate-400">Order ID</p><p className="mt-1 break-all font-mono text-sm">{selectedEvent.normalized.order_id}</p></div>}
              {selectedEvent.normalized?.invoice_id && <div><p className="text-xs text-slate-400">Invoice ID</p><p className="mt-1 break-all font-mono text-sm">{selectedEvent.normalized.invoice_id}</p></div>}
              {selectedEvent.normalized?.amount != null && <div><p className="text-xs text-slate-400">Amount</p><p className="mt-1 text-sm font-semibold">{currency(selectedEvent.normalized.amount)}</p></div>}
            </div>
            <div><div className="mb-2 flex items-center gap-2 text-sm font-semibold"><FileJson size={16}/>Raw webhook payload</div><pre className="max-h-[420px] overflow-auto rounded-xl bg-slate-950 p-4 text-xs leading-5 text-slate-200">{JSON.stringify(selectedEvent.payload, null, 2)}</pre></div>
          </div>
        )}
      </DetailModal>}
    </div>
  )
}
