import { useState } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { motion } from "motion/react"
import { Activity, ArrowRight, Layers3, Play, Plus, X } from "lucide-react"

import { apiGet } from "../../lib/api"
import { formatDateTime } from "../../lib/formatters"
import type { RecoveryBatch, RecoveryBatchesResponse } from "../../types/batches"

const currency = (value: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value)

function StatusBadge({ status }: { status: string }) {
  const active = status === "active"
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
      active
        ? "bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300"
        : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
    }`}>
      <span className={`h-1.5 w-1.5 rounded-full ${active ? "bg-blue-500" : "bg-slate-400"}`} />
      {active ? "Active" : "Completed"}
    </span>
  )
}

function BatchCard({ batch }: { batch: RecoveryBatch }) {
  return (
    <Link to={`/merchant/batches/${batch.batch_id}`} className="block">
      <motion.div
        whileHover={{ y: -2 }}
        className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md dark:border-slate-800 dark:bg-slate-900"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <Layers3 size={17} className="text-blue-500" />
              <h2 className="truncate font-semibold text-slate-950 dark:text-white">{batch.name}</h2>
            </div>
            <p className="mt-1 font-mono text-[11px] text-slate-400">{batch.batch_id}</p>
          </div>
          <StatusBadge status={batch.status} />
        </div>

        <p className="mt-4 line-clamp-2 text-sm text-slate-500 dark:text-slate-400">
          {batch.description || "Events and recovery activity captured from the batch start onward."}
        </p>

        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            ["Events", batch.event_count.toLocaleString("en-IN")],
            ["Cases", batch.case_count.toLocaleString("en-IN")],
            ["At risk", currency(batch.amount_at_risk)],
            ["Recovered", currency(batch.amount_recovered)],
          ].map(([label, value]) => (
            <div key={label} className="rounded-xl bg-slate-50 p-3 dark:bg-slate-950">
              <p className="text-[11px] uppercase tracking-wide text-slate-400">{label}</p>
              <p className="mt-1 text-sm font-semibold text-slate-900 dark:text-white">{value}</p>
            </div>
          ))}
        </div>

        <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
          <span>Started {formatDateTime(batch.started_at)}</span>
          <span className="flex items-center gap-1 text-blue-600 dark:text-blue-400">Open batch <ArrowRight size={13} /></span>
        </div>
      </motion.div>
    </Link>
  )
}

export default function MerchantBatches() {
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const query = useQuery({
    queryKey: ["recovery-batches"],
    queryFn: () => apiGet<RecoveryBatchesResponse>("/recovery/batches?limit=50&offset=0"),
    refetchInterval: 15000,
  })

  async function startBatch() {
    setSubmitting(true)
    setError(null)
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}/recovery/batches`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, description: description || null }),
        },
      )
      if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new Error(body?.detail || `Unable to start batch (${response.status})`)
      }
      setName("")
      setDescription("")
      setShowCreate(false)
      await queryClient.invalidateQueries({ queryKey: ["recovery-batches"] })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start batch")
    } finally {
      setSubmitting(false)
    }
  }

  const batches = query.data?.items ?? []
  const activeBatch = batches.find((batch) => batch.status === "active")

  return (
    <div className="min-h-full bg-slate-50 px-4 py-6 text-slate-900 dark:bg-slate-950 dark:text-slate-100 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-[1500px]">
        <div className="mb-7 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2 text-sm font-medium text-blue-600 dark:text-blue-400"><Layers3 size={16} />Revenue Recovery</div>
            <h1 className="text-3xl font-semibold tracking-tight">Batches</h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-500 dark:text-slate-400">Create a reporting boundary for a recovery run without deleting or changing historical data.</p>
          </div>
          <button onClick={() => setShowCreate(true)} disabled={Boolean(activeBatch)} className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 text-sm font-medium text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"><Plus size={17} />Start batch</button>
        </div>

        {activeBatch && (
          <div className="mb-6 flex flex-col gap-3 rounded-2xl border border-blue-200 bg-blue-50 p-4 dark:border-blue-900/60 dark:bg-blue-950/30 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3"><div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-100 text-blue-600 dark:bg-blue-900/60 dark:text-blue-300"><Play size={16} /></div><div><p className="text-sm font-semibold text-slate-900 dark:text-white">Active batch: {activeBatch.name}</p><p className="text-xs text-slate-500 dark:text-slate-400">New webhook events are assigned to this batch.</p></div></div>
            <Link to={`/merchant/batches/${activeBatch.batch_id}`} className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:underline dark:text-blue-400">View live batch <ArrowRight size={14} /></Link>
          </div>
        )}

        {query.isLoading ? <div className="grid gap-4 lg:grid-cols-2">{[1,2,3,4].map((i)=><div key={i} className="h-64 animate-pulse rounded-2xl bg-white dark:bg-slate-900" />)}</div> : query.isError ? <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300">Unable to load batches.</div> : batches.length === 0 ? <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center dark:border-slate-700 dark:bg-slate-900"><Layers3 className="mx-auto text-slate-400" size={30}/><h2 className="mt-4 font-semibold">No batches yet</h2><p className="mx-auto mt-1 max-w-md text-sm text-slate-500 dark:text-slate-400">Start a batch when you are ready to isolate a new recovery run.</p></div> : <div className="grid gap-4 lg:grid-cols-2">{batches.map((batch)=><BatchCard key={batch.batch_id} batch={batch}/>)}</div>}

        <div className="mt-8 flex items-center gap-2 text-xs text-slate-400"><Activity size={14}/> Historical records remain available in the main dashboard; batches only define a reporting and operational boundary.</div>
      </div>

      {showCreate && <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4"><motion.div initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-900"><div className="flex items-start justify-between"><div><h2 className="text-lg font-semibold">Start recovery batch</h2><p className="mt-1 text-sm text-slate-500 dark:text-slate-400">All newly ingested events will be assigned to this batch.</p></div><button onClick={()=>setShowCreate(false)} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"><X size={18}/></button></div><div className="mt-6 space-y-4"><div><label className="text-sm font-medium">Batch name</label><input value={name} onChange={e=>setName(e.target.value)} placeholder="Core recovery E2E — September 2026" className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 text-sm outline-none focus:border-blue-400 dark:border-slate-700 dark:bg-slate-950"/></div><div><label className="text-sm font-medium">Description <span className="font-normal text-slate-400">optional</span></label><textarea value={description} onChange={e=>setDescription(e.target.value)} rows={3} placeholder="Payment, normal invoice, and partial invoice validation" className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm outline-none focus:border-blue-400 dark:border-slate-700 dark:bg-slate-950"/></div>{error&&<div className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/30 dark:text-red-300">{error}</div>}<div className="flex justify-end gap-2 pt-2"><button onClick={()=>setShowCreate(false)} className="h-10 rounded-xl px-4 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">Cancel</button><button onClick={startBatch} disabled={!name.trim()||submitting} className="h-10 rounded-xl bg-blue-600 px-4 text-sm font-medium text-white disabled:opacity-50">{submitting?"Starting…":"Start batch"}</button></div></div></motion.div></div>}
    </div>
  )
}
