import { useMemo, useState } from "react"
import { useQueries, useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { motion } from "motion/react"
import {
  CheckCircle2,
  Clock3,
  ExternalLink,
  RefreshCw,
  Terminal,
  XCircle,
} from "lucide-react"

import { apiGet } from "../../lib/api"
import BatchSelector from "../../components/filters/BatchSelector"
import { formatDateTime } from "../../lib/formatters"
import type {
  RecoveryCase,
  RecoveryCasesResponse,
  RecoveryCaseTimeline,
} from "../../types/recovery"

const CASE_PAGE_SIZE = 30

type AttemptRow = {
  caseId: string
  event: RecoveryCaseTimeline["timeline"][number]
  attempt: RecoveryCaseTimeline["timeline"][number]["details"]["attempt_number"]
}

function label(value: string | null | undefined) {
  if (!value) return "—"
  return value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())
}

function resultClass(status: string) {
  if (status === "succeeded" || status === "resolved") {
    return "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300"
  }
  if (status === "failed") {
    return "bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-300"
  }
  return "bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300"
}

function TimelineQuery({ cases }: { cases: RecoveryCase[] }) {
  const queries = useQueries({
    queries: cases.map((item) => ({
      queryKey: ["execution-timeline", item.case_id],
      queryFn: () =>
        apiGet<RecoveryCaseTimeline>(
          `/recovery/cases/${item.case_id}/timeline`,
        ),
    })),
  })

  const rows = useMemo<AttemptRow[]>(() => {
    return queries
      .flatMap((query, index) => {
        const caseId = cases[index].case_id
        return (query.data?.timeline ?? [])
          .filter((event) => event.event_type === "attempt_executed")
          .map((event) => ({
            caseId,
            event,
            attempt: event.details.attempt_number ?? "—",
          }))
      })
      .sort(
        (a, b) =>
          new Date(b.event.timestamp).getTime() -
          new Date(a.event.timestamp).getTime(),
      )
  }, [cases, queries])

  if (queries.some((q) => q.isLoading)) {
    return (
      <div className="p-8 text-sm text-slate-500 dark:text-slate-400">
        Loading execution history…
      </div>
    )
  }

  if (queries.some((q) => q.isError)) {
    return (
      <div className="border-b border-amber-200 bg-amber-50 p-5 text-sm text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
        Some case timelines could not be loaded. Showing executions from the
        timelines that responded successfully.
      </div>
    )
  }

  if (rows.length === 0) {
    return (
      <div className="p-10 text-center text-sm text-slate-500 dark:text-slate-400">
        No executed attempts found in the loaded case window.
      </div>
    )
  }

  return (
    <div>
      <div className="hidden grid-cols-[90px_minmax(220px,1fr)_minmax(190px,1fr)_160px_130px] gap-4 border-b border-slate-200 bg-slate-50 px-5 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400 md:grid">
        <span>Attempt</span>
        <span>Case</span>
        <span>Action</span>
        <span>Provider</span>
        <span>Status</span>
      </div>

      {rows.map((row, index) => {
        const status = String(row.event.details.status ?? "pending")
        return (
          <motion.div
            key={`${row.caseId}-${row.event.timestamp}-${index}`}
            initial={{ opacity: 0, y: 3 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid gap-3 border-t border-slate-200 px-5 py-4 first:border-t-0 dark:border-slate-800 md:grid-cols-[90px_minmax(220px,1fr)_minmax(190px,1fr)_160px_130px] md:items-center md:gap-4"
          >
            <div>
              <span className="font-mono text-xs text-slate-500 dark:text-slate-400">
                #{String(row.attempt)}
              </span>
              <p className="mt-1 text-[11px] text-slate-400 dark:text-slate-500">
                {formatDateTime(row.event.timestamp)}
              </p>
            </div>

            <Link
              to={`/merchant/cases/${row.caseId}`}
              className="group min-w-0"
            >
              <span className="break-all text-sm font-medium text-blue-600 group-hover:underline dark:text-blue-400">
                {row.caseId}
              </span>
              <span className="mt-1 flex items-center gap-1 text-xs text-slate-400 dark:text-slate-500">
                Open case <ExternalLink className="h-3 w-3" />
              </span>
            </Link>

            <div>
              <p className="text-sm font-medium text-slate-900 dark:text-white">
                {label(String(row.event.details.action ?? "unknown"))}
              </p>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                {label(String(row.event.details.channel ?? "unknown"))}
              </p>
            </div>

            <span className="text-sm text-slate-600 dark:text-slate-300">
              {String(row.event.details.execution_provider ?? "—")}
            </span>

            <span
              className={`inline-flex w-fit rounded-full px-2.5 py-1 text-xs font-medium capitalize ${resultClass(status)}`}
            >
              {label(status)}
            </span>
          </motion.div>
        )
      })}
    </div>
  )
}

export default function DeveloperExecutions() {
  const [casePage, setCasePage] = useState(0)
  const [batchId, setBatchId] = useState("")

  const query = useQuery({
    queryKey: ["developer-executions-cases", casePage, batchId],
    queryFn: () =>
      apiGet<RecoveryCasesResponse>(
        `/recovery/cases?limit=${CASE_PAGE_SIZE}&offset=${casePage * CASE_PAGE_SIZE}${batchId ? `&batch_id=${encodeURIComponent(batchId)}` : ""}`,
      ),
    refetchInterval: 30000,
  })

  const cases = query.data?.items ?? []
  const totalCases = query.data?.total ?? 0
  const hasNext = (casePage + 1) * CASE_PAGE_SIZE < totalCases
  const hasPrevious = casePage > 0

  const terminal = cases.filter((c) =>
    ["recovered", "resolved"].includes(c.status),
  ).length
  const active = cases.filter((c) =>
    ["open", "recovering", "escalated"].includes(c.status),
  ).length
  const caseAttempts = cases.reduce(
    (total, item) => total + Math.max(item.current_attempt, 0),
    0,
  )

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-blue-600 dark:text-blue-400">
            Developer Console
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">
            Execution Monitor
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-500 dark:text-slate-400">
            Inspect persisted execution events and follow each attempt back to
            its recovery case. Load additional case windows to inspect older
            executions.
          </p>
        </div>

        <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
          <RefreshCw className="h-3.5 w-3.5" />
          Refreshes every 30s
        </div>
      </header>

      <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <BatchSelector value={batchId} onChange={(value) => { setBatchId(value); setCasePage(0) }} />
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {[
          { title: "Cases loaded", count: cases.length, Icon: Terminal },
          { title: "Attempts in window", count: caseAttempts, Icon: RefreshCw },
          { title: "Resolved cases", count: terminal, Icon: CheckCircle2 },
          { title: "Active / escalated", count: active, Icon: Clock3 },
        ].map(({ title, count, Icon }) => (
          <div
            key={title}
            className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
          >
            <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
              <Icon className="h-4 w-4" />
              <span className="text-sm">{title}</span>
            </div>
            <p className="mt-3 text-2xl font-semibold text-slate-900 dark:text-white">
              {count}
            </p>
          </div>
        ))}
      </div>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-4 dark:border-slate-800">
          <div>
            <h2 className="font-semibold text-slate-900 dark:text-white">
              Recent executions
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Persisted <code>attempt_executed</code> timeline events. No
              execution state is invented in the UI.
            </p>
          </div>

          <div className="text-xs text-slate-500 dark:text-slate-400">
            Case window {casePage + 1} · {Math.min(casePage * CASE_PAGE_SIZE + 1, totalCases)}–
            {Math.min((casePage + 1) * CASE_PAGE_SIZE, totalCases)} of {totalCases}
          </div>
        </div>

        {query.isLoading && (
          <div className="p-10 text-center text-sm text-slate-500 dark:text-slate-400">
            Loading execution cases…
          </div>
        )}

        {query.isError && !query.isLoading && (
          <div className="p-10 text-center">
            <XCircle className="mx-auto h-8 w-8 text-red-500" />
            <p className="mt-3 text-sm font-medium text-slate-900 dark:text-white">
              Execution source unavailable.
            </p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              The recovery case API could not be loaded.
            </p>
          </div>
        )}

        {!query.isLoading && !query.isError && <TimelineQuery cases={cases} />}

        <div className="flex items-center justify-between border-t border-slate-200 px-5 py-3 dark:border-slate-800">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Older execution records remain available through the case-window controls.
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={!hasPrevious}
              onClick={() => setCasePage((page) => Math.max(0, page - 1))}
              className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={!hasNext}
              onClick={() => setCasePage((page) => page + 1)}
              className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Next cases
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}
