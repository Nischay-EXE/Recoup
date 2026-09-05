import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { motion } from "motion/react"
import { Bot, ChevronLeft, ChevronRight, Search, ShieldCheck } from "lucide-react"

import { apiGet } from "../../lib/api"
import BatchSelector from "../../components/filters/BatchSelector"
import type { RecoveryCasesResponse } from "../../types/recovery"

const PAGE_SIZE = 12

function label(value: string | null | undefined) {
  if (!value) return "—"
  return value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())
}

function money(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(value)
}

function statusClass(status: string) {
  if (status === "recovered" || status === "resolved") return "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300"
  if (status === "escalated") return "bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-300"
  if (status === "open" || status === "recovering") return "bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300"
  return "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
}

export default function DeveloperAIDecisions() {
  const [search, setSearch] = useState("")
  const [batchId, setBatchId] = useState("")
  const [page, setPage] = useState(0)

  const query = useQuery({
    queryKey: ["developer-ai-decisions", page, batchId],
    queryFn: () =>
      apiGet<RecoveryCasesResponse>(
        `/recovery/cases?limit=${PAGE_SIZE}&offset=${page * PAGE_SIZE}${batchId ? `&batch_id=${encodeURIComponent(batchId)}` : ""}`,
      ),
  })

  const items = useMemo(() => {
    const term = search.trim().toLowerCase()
    if (!term) return query.data?.items ?? []
    return (query.data?.items ?? []).filter((item) =>
      [
        item.case_id,
        item.customer_id,
        item.original_payment_id,
        item.current_payment_id,
        item.subscription_id,
        item.invoice_id,
        item.revenue_object_type,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(term)),
    )
  }, [query.data?.items, search])

  const totalPages = Math.max(1, Math.ceil((query.data?.total ?? 0) / PAGE_SIZE))

  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm font-medium text-blue-600 dark:text-blue-400">Developer Console</p>
        <div className="mt-1 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">AI Decisions</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-500 dark:text-slate-400">
              Inspect the analyst, strategist, and deterministic guardrail decision recorded for each recovery case.
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs text-slate-500 dark:text-slate-400">Cases with decision history</p>
            <p className="mt-1 text-xl font-semibold text-slate-900 dark:text-white">{query.data?.total?.toLocaleString("en-IN") ?? "—"}</p>
          </div>
        </div>
      </header>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <BatchSelector value={batchId} onChange={(value) => { setBatchId(value); setPage(0) }} />
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0) }}
            placeholder="Search case, customer, payment, subscription or invoice..."
            className="h-10 w-full rounded-xl border border-slate-200 bg-slate-50 pl-9 pr-3 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
          />
        </div>
      </div>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="grid grid-cols-[minmax(230px,1.4fr)_150px_170px_130px_110px] gap-4 bg-slate-50 px-5 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:bg-slate-950 dark:text-slate-400">
          <span>Case</span><span>Revenue object</span><span>Recovery decision</span><span>Guardrail</span><span>Status</span>
        </div>

        {query.isLoading && (
          <div className="space-y-2 p-4">{Array.from({ length: 7 }).map((_, i) => <div key={i} className="h-16 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800" />)}</div>
        )}

        {query.isError && !query.isLoading && (
          <div className="p-10 text-center">
            <p className="font-medium text-slate-900 dark:text-white">Could not load AI decision history.</p>
            <button onClick={() => query.refetch()} className="mt-3 rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white dark:bg-white dark:text-slate-900">Try again</button>
          </div>
        )}

        {!query.isLoading && !query.isError && items.map((item, index) => (
          <motion.div
            key={item.case_id}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(index * 0.025, 0.2) }}
            className="grid grid-cols-[minmax(230px,1.4fr)_150px_170px_130px_110px] items-center gap-4 border-t border-slate-200 px-5 py-4 first:border-t-0 dark:border-slate-800"
          >
            <Link to={`/developer/decisions/${item.case_id}`} className="min-w-0 group">
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4 shrink-0 text-purple-500" />
                <span className="truncate text-sm font-semibold text-slate-900 group-hover:text-blue-600 dark:text-white dark:group-hover:text-blue-400">{item.case_id}</span>
              </div>
              <p className="mt-1 truncate pl-6 text-xs text-slate-500 dark:text-slate-400">{item.customer_id ?? "No customer ID"} · {money(item.amount_at_risk)}</p>
            </Link>

            <span className="text-sm text-slate-600 dark:text-slate-300">{label(item.revenue_object_type)}</span>

            <div>
              <p className="text-sm font-medium text-slate-900 dark:text-white">{item.current_attempt > 0 ? `Attempt ${item.current_attempt}` : "Not executed"}</p>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Open detail for AI trace</p>
            </div>

            <div className="flex items-center gap-1.5 text-sm text-slate-600 dark:text-slate-300">
              <ShieldCheck className="h-4 w-4 text-blue-500" /> deterministic
            </div>

            <span className={`inline-flex w-fit rounded-full px-2.5 py-1 text-xs font-medium capitalize ${statusClass(item.status)}`}>{label(item.status)}</span>
          </motion.div>
        ))}

        {!query.isLoading && !query.isError && items.length === 0 && (
          <div className="p-10 text-center text-sm text-slate-500 dark:text-slate-400">No decision records match the current search.</div>
        )}

        <div className="flex items-center justify-between border-t border-slate-200 px-5 py-3 dark:border-slate-800">
          <span className="text-xs text-slate-500 dark:text-slate-400">{query.data?.total ? `${query.data.offset + 1}–${Math.min(query.data.offset + query.data.limit, query.data.total)} of ${query.data.total}` : "0 cases"}</span>
          <div className="flex items-center gap-2">
            <button disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))} className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 disabled:opacity-40 dark:border-slate-700"><ChevronLeft className="h-4 w-4" /></button>
            <span className="min-w-16 text-center text-xs text-slate-600 dark:text-slate-300">Page {page + 1} / {totalPages}</span>
            <button disabled={page + 1 >= totalPages} onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 disabled:opacity-40 dark:border-slate-700"><ChevronRight className="h-4 w-4" /></button>
          </div>
        </div>
      </section>
    </div>
  )
}
