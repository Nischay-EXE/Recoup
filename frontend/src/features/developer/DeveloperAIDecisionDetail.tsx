import { useQuery } from "@tanstack/react-query"
import { Link, useParams } from "react-router-dom"
import { ArrowLeft, Bot, CheckCircle2, ShieldCheck, Terminal, Zap } from "lucide-react"

import { apiGet } from "../../lib/api"
import type { RecoveryCaseTimeline, RecoveryTimelineEvent } from "../../types/recovery"

function label(value: string | null | undefined) {
  if (!value) return "—"
  return value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())
}
function money(value: number) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(value)
}
function value(event: RecoveryTimelineEvent | undefined, key: string) {
  return event?.details?.[key] == null ? "—" : String(event.details[key])
}
function Card({ title, icon, children, className = "" }: { title: string; icon: React.ReactNode; children: React.ReactNode; className?: string }) {
  return <section className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 ${className}`}><div className="mb-5 flex items-center gap-2">{icon}<h2 className="font-semibold text-slate-900 dark:text-white">{title}</h2></div>{children}</section>
}

export default function DeveloperAIDecisionDetail() {
  const { caseId } = useParams<{ caseId: string }>()
  const query = useQuery({
    queryKey: ["developer-ai-decision", caseId],
    queryFn: () => apiGet<RecoveryCaseTimeline>(`/recovery/cases/${caseId}/timeline`),
    enabled: Boolean(caseId),
  })

  if (query.isLoading) return <div className="space-y-5"><div className="h-8 w-48 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800" /><div className="h-36 animate-pulse rounded-2xl bg-white dark:bg-slate-900" /><div className="h-72 animate-pulse rounded-2xl bg-white dark:bg-slate-900" /></div>

  if (query.isError || !query.data) return <div className="rounded-2xl border border-red-200 bg-red-50 p-6 dark:border-red-900 dark:bg-red-950/30"><p className="font-semibold text-red-900 dark:text-red-200">Decision trace unavailable</p><p className="mt-1 text-sm text-red-700 dark:text-red-300">The case timeline could not be loaded.</p></div>

  const timeline = query.data.timeline
  const decision = timeline.find((e) => e.event_type === "decision_created")
  const guardrail = timeline.find((e) => e.event_type === "guardrail_evaluated")
  const execution = timeline.find((e) => e.event_type === "attempt_executed")
  const approved = value(guardrail, "policy_result") === "approved"

  return <div className="space-y-6">
    <Link to="/developer/decisions" className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"><ArrowLeft className="h-4 w-4" /> Back to AI decisions</Link>

    <header className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
      <div>
        <p className="text-sm font-medium text-blue-600 dark:text-blue-400">Developer Console · AI Decision Detail</p>
        <h1 className="mt-1 break-all text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">{caseId}</h1>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">{label(query.data.revenue_object_type)} · {query.data.customer_id ?? "No customer ID"}</p>
      </div>
      <div className="text-left lg:text-right"><p className="text-xs text-slate-500 dark:text-slate-400">Revenue at risk</p><p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">{money(query.data.amount_at_risk)}</p></div>
    </header>

    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div><p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Decision status</p><p className={`mt-2 text-lg font-semibold ${approved ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"}`}>{approved ? "Approved by guardrail" : guardrail ? "Blocked by guardrail" : "Decision recorded"}</p></div>
        <div className="flex flex-wrap gap-2 text-xs">{decision && <span className="rounded-lg bg-purple-50 px-3 py-2 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300">Analyst + Strategist</span>}{guardrail && <span className="rounded-lg bg-blue-50 px-3 py-2 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">Deterministic guardrail</span>}{execution && <span className="rounded-lg bg-emerald-50 px-3 py-2 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">Execution trace</span>}</div>
      </div>
    </section>

    <div className="grid gap-5 lg:grid-cols-2">
      <Card title="Analyst report" icon={<Bot className="h-5 w-5 text-purple-500" />}>
        <dl className="grid gap-5 sm:grid-cols-2">
          <div><dt className="text-xs text-slate-400">Failure classification</dt><dd className="mt-1 text-sm font-medium text-slate-900 dark:text-white">{value(decision, "failure_classification") === "—" ? "See recovery decision below" : value(decision, "failure_classification")}</dd></div>
          <div><dt className="text-xs text-slate-400">Confidence</dt><dd className="mt-1 text-sm font-medium text-slate-900 dark:text-white">{decision ? value(decision, "confidence") : "—"}</dd></div>
          <div className="sm:col-span-2"><dt className="text-xs text-slate-400">Recommended direction</dt><dd className="mt-1 text-sm font-medium text-slate-900 dark:text-white">{value(decision, "action") !== "—" ? `${label(value(decision, "action"))} via ${label(value(decision, "channel"))}` : "—"}</dd></div>
          <div className="sm:col-span-2"><dt className="text-xs text-slate-400">Reason</dt><dd className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">{value(decision, "reason")}</dd></div>
        </dl>
      </Card>

      <Card title="Strategist decision" icon={<Terminal className="h-5 w-5 text-indigo-500" />}>
        <dl className="grid gap-5 sm:grid-cols-2">
          <div><dt className="text-xs text-slate-400">Action</dt><dd className="mt-1 text-sm font-medium text-slate-900 dark:text-white">{label(value(decision, "action"))}</dd></div>
          <div><dt className="text-xs text-slate-400">Channel</dt><dd className="mt-1 text-sm font-medium text-slate-900 dark:text-white">{label(value(decision, "channel"))}</dd></div>
          <div><dt className="text-xs text-slate-400">Priority</dt><dd className="mt-1 text-sm font-medium text-slate-900 dark:text-white">{label(value(decision, "priority"))}</dd></div>
          <div className="sm:col-span-2"><dt className="text-xs text-slate-400">Reason</dt><dd className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">{value(decision, "reason")}</dd></div>
        </dl>
      </Card>
    </div>

    <Card title="Deterministic guardrail" icon={<ShieldCheck className={`h-5 w-5 ${approved ? "text-emerald-500" : "text-red-500"}`} />}>
      <div className="grid gap-4 md:grid-cols-4">
        <div><p className="text-xs text-slate-400">Capability</p><p className="mt-1 text-sm font-medium text-slate-900 dark:text-white">{value(guardrail, "capability")}</p></div>
        <div><p className="text-xs text-slate-400">Channel allowed</p><p className="mt-1 text-sm font-medium text-slate-900 dark:text-white">{value(guardrail, "channel")}</p></div>
        <div><p className="text-xs text-slate-400">Attempt</p><p className="mt-1 text-sm font-medium text-slate-900 dark:text-white">{query.data.timeline.filter((e) => e.event_type === "attempt_created").length} / 3</p></div>
        <div><p className="text-xs text-slate-400">Result</p><p className={`mt-1 inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${approved ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300" : "bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-300"}`}>{approved ? "APPROVED" : "BLOCKED"}</p></div>
      </div>
      <p className="mt-5 text-sm text-slate-500 dark:text-slate-400">{value(guardrail, "policy_reason")}</p>
    </Card>

    <Card title="Execution trace" icon={<Zap className="h-5 w-5 text-amber-500" />}>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <span className="rounded-lg bg-slate-100 px-3 py-2 dark:bg-slate-800">Decision</span><span>→</span>
        <span className="rounded-lg bg-blue-50 px-3 py-2 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">Guardrail</span><span>→</span>
        <span className="rounded-lg bg-indigo-50 px-3 py-2 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300">Executor</span><span>→</span>
        <span className="rounded-lg bg-emerald-50 px-3 py-2 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">Outcome</span>
      </div>
      {execution ? <div className="mt-5 grid gap-4 md:grid-cols-3"><div><p className="text-xs text-slate-400">Provider</p><p className="mt-1 text-sm font-medium text-slate-900 dark:text-white">{value(execution, "execution_provider")}</p></div><div><p className="text-xs text-slate-400">Status</p><p className="mt-1 text-sm font-medium text-slate-900 dark:text-white">{label(value(execution, "status"))}</p></div><div><p className="text-xs text-slate-400">External execution</p><p className="mt-1 break-all font-mono text-xs text-slate-600 dark:text-slate-300">{value(execution, "external_execution_id")}</p></div></div> : <p className="mt-5 text-sm text-slate-500 dark:text-slate-400">No execution has been recorded for this decision yet.</p>}
    </Card>

    <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> Audit records remain attached to the case timeline.</div>
  </div>
}
