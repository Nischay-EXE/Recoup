import { useQuery } from "@tanstack/react-query"
import { motion } from "motion/react"
import {
  Activity,
  CheckCircle2,
  Database,
  HeartPulse,
  Radio,
  Server,
  ShieldCheck,
  Wifi,
  XCircle,
} from "lucide-react"

import { apiGet } from "../../lib/api"

type HealthComponent = {
  status: "healthy" | "unavailable" | "configured" | "degraded"
  detail: string
  last_heartbeat?: string | null
  age_seconds?: number
}

type HealthResponse = {
  status: "healthy" | "degraded"
  checked_at?: string
  components?: Record<string, HealthComponent>
}

type HealthCardProps = {
  name: string
  description: string
  status: "healthy" | "unavailable" | "configured" | "not_exposed"
  icon: React.ComponentType<{ className?: string }>
  detail: string
}

function HealthCard({
  name,
  description,
  status,
  icon: Icon,
  detail,
}: HealthCardProps) {
  const config = {
    healthy: {
      label: "Healthy",
      dot: "bg-emerald-500",
      badge: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300",
    },
    unavailable: {
      label: "Unavailable",
      dot: "bg-red-500",
      badge: "bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-300",
    },
    configured: {
      label: "Configured",
      dot: "bg-amber-500",
      badge: "bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300",
    },
    not_exposed: {
      label: "Not exposed",
      dot: "bg-slate-400",
      badge: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
    },
  }[status]

  return (
    <motion.article
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          <Icon className="h-5 w-5" />
        </div>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${config.badge}`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${config.dot}`} />
          {config.label}
        </span>
      </div>

      <h2 className="mt-4 font-semibold text-slate-900 dark:text-white">{name}</h2>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>
      <p className="mt-4 text-xs leading-5 text-slate-400 dark:text-slate-500">{detail}</p>
    </motion.article>
  )
}

export default function DeveloperSystemHealth() {
  const query = useQuery({
    queryKey: ["system-health"],
    queryFn: () => apiGet<HealthResponse>("/health"),
    refetchInterval: 15000,
  })

  const apiReachable = !query.isError && !query.isLoading
  const apiStatus: HealthCardProps["status"] = query.isError ? "unavailable" : query.isLoading ? "not_exposed" : "healthy"

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-blue-600 dark:text-blue-400">
            Developer Console
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">
            System Health
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-500 dark:text-slate-400">
            Operational visibility for the recovery engine. Only components
            backed by a real frontend API probe are marked healthy.
          </p>
        </div>

        <div
          className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs font-medium ${
            apiReachable
              ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-300"
              : "border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300"
          }`}
        >
          <span
            className={`h-2 w-2 rounded-full ${apiReachable ? "bg-emerald-500" : "bg-red-500"}`}
          />
          {query.isLoading ? "Checking API…" : apiReachable ? "API reachable" : "API unavailable"}
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <HealthCard
          name="FastAPI"
          description="Webhook gateway and recovery API"
          status={apiStatus}
          icon={Server}
          detail={
            query.isLoading
              ? "Checking /health…"
              : query.isError
                ? "The health endpoint could not be reached."
                : query.data?.components?.api?.detail ?? "FastAPI is responding."
          }
        />
        <HealthCard
          name="Redis Streams"
          description="Event queue and consumer transport"
          status={query.data?.components?.redis?.status === "healthy" ? "healthy" : query.isLoading ? "not_exposed" : "unavailable"}
          icon={Radio}
          detail={query.data?.components?.redis?.detail ?? "Waiting for the backend health probe."}
        />
        <HealthCard
          name="PostgreSQL"
          description="Audit history and recovery state"
          status={query.data?.components?.database?.status === "healthy" ? "healthy" : query.isLoading ? "not_exposed" : "unavailable"}
          icon={Database}
          detail={query.data?.components?.database?.detail ?? "Waiting for the backend health probe."}
        />
        <HealthCard
          name="Recovery Worker"
          description="Event consumer and orchestration"
          status={query.data?.components?.worker?.status === "healthy" ? "healthy" : query.isLoading ? "not_exposed" : "unavailable"}
          icon={Activity}
          detail={query.data?.components?.worker?.detail ?? "Waiting for worker heartbeat."}
        />
        <HealthCard
          name="Recovery Scheduler"
          description="Due-attempt polling and stopping rules"
          status={query.data?.components?.scheduler?.status === "healthy" ? "healthy" : query.isLoading ? "not_exposed" : "unavailable"}
          icon={HeartPulse}
          detail={query.data?.components?.scheduler?.detail ?? "Waiting for scheduler heartbeat."}
        />
        <HealthCard
          name="Razorpay"
          description="Payment execution and outcome provider"
          status={query.data?.components?.razorpay?.status === "configured" ? "configured" : query.isLoading ? "not_exposed" : "unavailable"}
          icon={Wifi}
          detail={query.data?.components?.razorpay?.detail ?? "Waiting for the backend provider configuration probe."}
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center gap-2">
            {apiReachable ? (
              <CheckCircle2 className="h-5 w-5 text-emerald-500" />
            ) : (
              <XCircle className="h-5 w-5 text-red-500" />
            )}
            <div>
              <h2 className="font-semibold text-slate-900 dark:text-white">
                Observability status
              </h2>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                What the current frontend can verify without inventing runtime state.
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl bg-slate-50 p-4 dark:bg-slate-950">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Verified now
              </p>
              <p className="mt-2 text-sm font-medium text-slate-900 dark:text-white">
                Runtime probes
              </p>
              <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">
                The frontend polls the real /health endpoint every 15 seconds and displays DB, Redis, worker, scheduler, and provider configuration state.
              </p>
            </div>
            <div className="rounded-xl bg-slate-50 p-4 dark:bg-slate-950">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Needs runtime probes
              </p>
              <p className="mt-2 text-sm font-medium text-slate-900 dark:text-white">
                External provider reachability
              </p>
              <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">
                Razorpay is reported as configured rather than falsely claiming live provider reachability.
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-blue-500" />
            <h2 className="font-semibold text-slate-900 dark:text-white">
              Pipeline safeguards
            </h2>
          </div>

          <div className="mt-5 space-y-3">
            {[
              ["Duplicate events", "Handled idempotently at the event boundary."],
              ["Terminal cases", "Stopping rules prevent further execution."],
              ["Audit history", "Decisions, guardrails, executions and outcomes remain correlated."],
            ].map(([title, description]) => (
              <div key={title} className="rounded-xl bg-slate-50 p-4 dark:bg-slate-950">
                <p className="text-sm font-medium text-slate-900 dark:text-white">{title}</p>
                <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="font-semibold text-slate-900 dark:text-white">Health response</h2>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Raw response from the backend health endpoint.
            </p>
          </div>
          <span className="text-xs text-slate-400 dark:text-slate-500">15s polling</span>
        </div>
        <pre className="mt-4 max-h-48 overflow-auto rounded-xl bg-slate-950 p-4 font-mono text-xs leading-5 text-slate-300">
          {query.isLoading
            ? "Checking…"
            : JSON.stringify(query.data ?? { error: "Health endpoint unavailable" }, null, 2)}
        </pre>
      </section>
    </div>
  )
}
