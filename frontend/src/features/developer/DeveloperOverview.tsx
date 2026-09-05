import { Activity, AlertTriangle, CheckCircle2, Cpu, Database, ShieldCheck, Zap } from "lucide-react"
import { useQuery } from "@tanstack/react-query"
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { apiGet } from "../../lib/api"
import type {
  RecoveryBreakdowns,
  RecoveryMetrics,
} from "../../types/recovery"

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value)
}

function formatLabel(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function StatCard({
  icon,
  label,
  value,
  description,
  tone = "default",
}: {
  icon: React.ReactNode
  label: string
  value: string | number
  description: string
  tone?: "default" | "success" | "warning" | "danger" | "info"
}) {
  const toneClasses = {
    default:
      "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
    success:
      "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400",
    warning:
      "bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-400",
    danger:
      "bg-red-50 text-red-600 dark:bg-red-950/50 dark:text-red-400",
    info:
      "bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400",
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div
        className={`flex h-10 w-10 items-center justify-center rounded-xl ${toneClasses[tone]}`}
      >
        {icon}
      </div>

      <div className="mt-5">
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
          {label}
        </p>

        <p className="mt-1 text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">
          {value}
        </p>

        <p className="mt-2 text-xs text-slate-400 dark:text-slate-500">
          {description}
        </p>
      </div>
    </div>
  )
}

function DeveloperOverview() {
  const metricsQuery = useQuery({
    queryKey: ["recovery", "metrics"],
    queryFn: () => apiGet<RecoveryMetrics>("/recovery/metrics"),
  })

  const breakdownsQuery = useQuery({
    queryKey: ["recovery", "breakdowns"],
    queryFn: () => apiGet<RecoveryBreakdowns>("/recovery/metrics/breakdowns"),
  })

  const metrics = metricsQuery.data
  const breakdowns = breakdownsQuery.data

  const objectChartData = breakdowns
    ? Object.entries(breakdowns.by_revenue_object).map(
        ([name, data]) => ({
          name: formatLabel(name),
          attempts: data.attempts,
          recovered: data.recovered_attempts,
        }),
      )
    : []

  const actionChartData = breakdowns
    ? Object.entries(breakdowns.by_action).map(
        ([name, data]) => ({
          name: formatLabel(name),
          attempts: data.attempts,
          recovered: data.recovered_attempts,
        }),
      )
    : []

  const loading = metricsQuery.isLoading || breakdownsQuery.isLoading
  const error = metricsQuery.error || breakdownsQuery.error

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <div className="h-4 w-32 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
          <div className="mt-3 h-8 w-64 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
          <div className="mt-2 h-4 w-96 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div
              key={index}
              className="h-40 animate-pulse rounded-2xl bg-slate-200 dark:bg-slate-900"
            />
          ))}
        </div>
      </div>
    )
  }

  if (error || !metrics) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-6 dark:border-red-900/50 dark:bg-red-950/30">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-red-500" />

          <div>
            <h2 className="font-semibold text-red-700 dark:text-red-400">
              Unable to load developer metrics
            </h2>

            <p className="mt-1 text-sm text-red-600 dark:text-red-400/80">
              The recovery API did not return the expected data.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 xl:flex-row xl:items-end">
        <div>
          <div className="flex items-center gap-2 text-sm font-medium text-blue-500">
            <Cpu className="h-4 w-4" />
            Recovery Engine
          </div>

          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 dark:text-white">
            Developer Overview
          </h1>

          <p className="mt-2 max-w-2xl text-sm text-slate-500 dark:text-slate-400">
            Inspect the health and behavior of the revenue recovery engine
            using live backend data.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start rounded-full border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-400 xl:self-auto">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          Engine operational
        </div>
      </div>

      {/* Technical metrics */}
      <section>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-slate-950 dark:text-white">
            Engine activity
          </h2>

          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Current recovery workload and outcomes.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard
            icon={<Database className="h-5 w-5" />}
            label="Recovery cases"
            value={metrics.total_cases}
            description="Cases created by the recovery engine."
            tone="info"
          />

          <StatCard
            icon={<Activity className="h-5 w-5" />}
            label="Recovery attempts"
            value={metrics.total_attempts}
            description="Actions created for recovery."
          />

          <StatCard
            icon={<CheckCircle2 className="h-5 w-5" />}
            label="Recovered cases"
            value={metrics.recovered_cases}
            description={`${metrics.recovery_rate.toFixed(2)}% overall recovery rate.`}
            tone="success"
          />

          <StatCard
            icon={<AlertTriangle className="h-5 w-5" />}
            label="Escalated cases"
            value={metrics.escalated_cases}
            description="Cases requiring human intervention."
            tone="danger"
          />
        </div>
      </section>

      {/* Money flow */}
      <section>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-slate-950 dark:text-white">
            Revenue flow
          </h2>

          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Financial impact generated by the recovery engine.
          </p>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <StatCard
            icon={<ShieldCheck className="h-5 w-5" />}
            label="Revenue at risk"
            value={formatCurrency(metrics.amount_at_risk)}
            description="Total revenue identified for recovery."
            tone="warning"
          />

          <StatCard
            icon={<CheckCircle2 className="h-5 w-5" />}
            label="Revenue recovered"
            value={formatCurrency(metrics.amount_recovered)}
            description="Revenue successfully recovered."
            tone="success"
          />

          <StatCard
            icon={<Zap className="h-5 w-5" />}
            label="Revenue remaining"
            value={formatCurrency(
              metrics.amount_at_risk - metrics.amount_recovered,
            )}
            description="Revenue still requiring recovery or escalation."
            tone="danger"
          />
        </div>
      </section>

      {/* Recovery pipeline */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
          <div>
            <h2 className="text-lg font-semibold text-slate-950 dark:text-white">
              Recovery pipeline
            </h2>

            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              High-level state of cases processed by the engine.
            </p>
          </div>

          <div className="rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-right dark:border-blue-900/50 dark:bg-blue-950/30">
            <p className="text-xs text-blue-600 dark:text-blue-400">
              Recovery rate
            </p>

            <p className="text-xl font-semibold text-blue-700 dark:text-blue-300">
              {metrics.recovery_rate.toFixed(2)}%
            </p>
          </div>
        </div>

        <div className="mt-6 space-y-4">
          {[
            {
              label: "Total cases",
              value: metrics.total_cases,
              tone: "bg-blue-500",
            },
            {
              label: "Recovered",
              value: metrics.recovered_cases,
              tone: "bg-emerald-500",
            },
            {
              label: "Escalated",
              value: metrics.escalated_cases,
              tone: "bg-red-500",
            },
            {
              label: "Unresolved",
              value: metrics.unresolved_cases,
              tone: "bg-amber-500",
            },
          ].map((item) => {
            const percentage =
              metrics.total_cases > 0
                ? (item.value / metrics.total_cases) * 100
                : 0

            return (
              <div key={item.label}>
                <div className="mb-2 flex items-center justify-between text-sm">
                  <span className="font-medium text-slate-700 dark:text-slate-300">
                    {item.label}
                  </span>

                  <span className="text-slate-500 dark:text-slate-400">
                    {item.value} · {percentage.toFixed(1)}%
                  </span>
                </div>

                <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                  <div
                    className={`h-full rounded-full ${item.tone}`}
                    style={{
                      width: `${Math.min(percentage, 100)}%`,
                    }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </section>

      {/* Charts */}
      <div className="grid gap-6 xl:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-slate-950 dark:text-white">
              Attempts by revenue object
            </h2>

            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Payment, subscription, and invoice recovery activity.
            </p>
          </div>

          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={objectChartData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  className="stroke-slate-200 dark:stroke-slate-800"
                />

                <XAxis
                  dataKey="name"
                  tickLine={false}
                  axisLine={false}
                  tick={{
                    fill: "currentColor",
                    fontSize: 12,
                  }}
                  className="text-slate-400"
                />

                <YAxis
                  allowDecimals={false}
                  tickLine={false}
                  axisLine={false}
                  tick={{
                    fill: "currentColor",
                    fontSize: 12,
                  }}
                  className="text-slate-400"
                />

                <Tooltip />

                <Bar
                  dataKey="attempts"
                  name="Attempts"
                  radius={[6, 6, 0, 0]}
                  fill="#3b82f6"
                />

                <Bar
                  dataKey="recovered"
                  name="Recovered"
                  radius={[6, 6, 0, 0]}
                  fill="#10b981"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-slate-950 dark:text-white">
              Attempts by action
            </h2>

            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Recovery strategies executed by the engine.
            </p>
          </div>

          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={actionChartData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  className="stroke-slate-200 dark:stroke-slate-800"
                />

                <XAxis
                  dataKey="name"
                  tickLine={false}
                  axisLine={false}
                  tick={{
                    fill: "currentColor",
                    fontSize: 11,
                  }}
                  className="text-slate-400"
                  interval={0}
                />

                <YAxis
                  allowDecimals={false}
                  tickLine={false}
                  axisLine={false}
                  tick={{
                    fill: "currentColor",
                    fontSize: 12,
                  }}
                  className="text-slate-400"
                />

                <Tooltip />

                <Bar
                  dataKey="attempts"
                  name="Attempts"
                  radius={[6, 6, 0, 0]}
                  fill="#6366f1"
                />

                <Bar
                  dataKey="recovered"
                  name="Recovered"
                  radius={[6, 6, 0, 0]}
                  fill="#10b981"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      {/* Control plane notice */}
      <section className="rounded-2xl border border-blue-200 bg-blue-50/70 p-5 dark:border-blue-900/50 dark:bg-blue-950/20">
        <div className="flex gap-3">
          <Cpu className="mt-0.5 h-5 w-5 shrink-0 text-blue-600 dark:text-blue-400" />

          <div>
            <h3 className="font-semibold text-blue-900 dark:text-blue-300">
              Live control-plane data
            </h3>

            <p className="mt-1 text-sm leading-6 text-blue-800/80 dark:text-blue-300/70">
              These values are read directly from the recovery API. Detailed
              event lineage, AI decisions, guardrail evaluations, and
              executions will be exposed in the Developer Console pages next.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}

export default DeveloperOverview
