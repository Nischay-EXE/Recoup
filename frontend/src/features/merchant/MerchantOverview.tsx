import { motion, type Variants } from "motion/react"
import { useQuery } from "@tanstack/react-query"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  IndianRupee,
  Layers3,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  WalletCards,
} from "lucide-react"

import { apiGet } from "../../lib/api"
import type {
  RecoveryBreakdowns,
  RecoveryMetrics,
} from "../../types/recovery"

const cardVariants: Variants = {
  hidden: {
    opacity: 0,
    y: 16,
  },

  visible: (index: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.45,
      delay: index * 0.06,
      ease: "easeOut",
    },
  }),
}

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value)

const formatNumber = (value: number) =>
  new Intl.NumberFormat("en-IN").format(value)

const formatLabel = (value: string) =>
  value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase())

function MetricCard({
  index,
  title,
  value,
  subtitle,
  icon: Icon,
  iconClassName,
  trend,
}: {
  index: number
  title: string
  value: string
  subtitle: string
  icon: typeof IndianRupee
  iconClassName: string
  trend?: {
    value: string
    positive?: boolean
  }
}) {
  return (
    <motion.div
      custom={index}
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      whileHover={{
        y: -3,
        transition: { duration: 0.2 },
      }}
      className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md dark:border-slate-800 dark:bg-slate-900 dark:hover:shadow-black/20"
    >
      <div className="flex items-start justify-between">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconClassName}`}
        >
          <Icon size={19} strokeWidth={2} />
        </div>

        {trend && (
          <div
            className={`flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium ${
              trend.positive
                ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300"
                : "bg-amber-50 text-amber-700 dark:bg-amber-950/60 dark:text-amber-300"
            }`}
          >
            {trend.positive ? (
              <ArrowUpRight size={13} />
            ) : (
              <ArrowDownRight size={13} />
            )}
            {trend.value}
          </div>
        )}
      </div>

      <div className="mt-5">
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
          {title}
        </p>

        <p className="mt-1 text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">
          {value}
        </p>

        <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
          {subtitle}
        </p>
      </div>
    </motion.div>
  )
}

function StatusCard({
  index,
  icon: Icon,
  title,
  value,
  description,
  iconClassName,
}: {
  index: number
  icon: typeof CheckCircle2
  title: string
  value: number
  description: string
  iconClassName: string
}) {
  return (
    <motion.div
      custom={index}
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      whileHover={{ y: -2 }}
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:hover:shadow-black/20"
    >
      <div className="flex items-center gap-3">
        <div
          className={`flex h-9 w-9 items-center justify-center rounded-lg ${iconClassName}`}
        >
          <Icon size={18} />
        </div>

        <div>
          <p className="text-sm font-medium text-slate-600 dark:text-slate-300">
            {title}
          </p>

          <p className="text-xl font-semibold text-slate-950 dark:text-white">
            {formatNumber(value)}
          </p>
        </div>
      </div>

      <p className="mt-4 text-xs leading-5 text-slate-400 dark:text-slate-500">
        {description}
      </p>
    </motion.div>
  )
}

export default function MerchantOverview() {
  const metricsQuery = useQuery({
    queryKey: ["recovery", "metrics"],
    queryFn: () => apiGet<RecoveryMetrics>("/recovery/metrics"),
  })

  const breakdownsQuery = useQuery({
    queryKey: ["recovery", "breakdowns"],
    queryFn: () =>
      apiGet<RecoveryBreakdowns>("/recovery/metrics/breakdowns"),
  })

  if (metricsQuery.isLoading || breakdownsQuery.isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-64 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800" />

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {[1, 2, 3, 4].map((item) => (
            <div
              key={item}
              className="h-40 animate-pulse rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
            />
          ))}
        </div>

        <div className="h-96 animate-pulse rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900" />
      </div>
    )
  }

  if (metricsQuery.isError || breakdownsQuery.isError) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-6 dark:border-red-900 dark:bg-red-950/30">
        <div className="flex items-center gap-3">
          <AlertTriangle className="text-red-600 dark:text-red-400" size={20} />

          <div>
            <p className="font-semibold text-red-900 dark:text-red-200">
              Unable to load recovery metrics
            </p>

            <p className="mt-1 text-sm text-red-700 dark:text-red-300">
              Check that the FastAPI backend is running and reachable.
            </p>
          </div>
        </div>
      </div>
    )
  }

  const metrics = metricsQuery.data
  const breakdowns = breakdownsQuery.data

  if (!metrics || !breakdowns) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Recovery data is currently unavailable.
        </p>
      </div>
    )
  }

  const revenueRemaining =
    metrics.amount_at_risk - metrics.amount_recovered

  const objectChartData = Object.entries(
    breakdowns.by_revenue_object,
  ).map(([name, data]) => ({
    name: formatLabel(name),
    recovered: data.amount_recovered,
    attempts: data.attempts,
  }))

  const recoveryProgress =
    metrics.amount_at_risk > 0
      ? Math.min(
          100,
          (metrics.amount_recovered / metrics.amount_at_risk) * 100,
        )
      : 0

  const successfulAttempts = Object.values(
    breakdowns.by_action,
  ).reduce(
    (total, item) => total + item.recovered_attempts,
    0,
  )

  const averageRecovered =
    metrics.recovered_cases > 0
      ? metrics.amount_recovered / metrics.recovered_cases
      : 0

  return (
    <div className="space-y-7">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="flex flex-col justify-between gap-4 md:flex-row md:items-end"
      >
        <div>
          <div className="flex items-center gap-2">
            <Sparkles size={18} className="text-blue-600 dark:text-blue-400" />

            <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">
              Revenue Recovery
            </span>
          </div>

          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 dark:text-white">
            Merchant Overview
          </h1>

          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            See how much revenue is at risk, recovered, and where the engine
            needs attention.
          </p>
        </div>

        <div className="flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </span>

          Recovery engine operational
        </div>
      </motion.div>

      {/* Primary financial metrics */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          index={0}
          title="Revenue at risk"
          value={formatCurrency(metrics.amount_at_risk)}
          subtitle="Total revenue identified for recovery"
          icon={ShieldAlert}
          iconClassName="bg-red-50 text-red-600 dark:bg-red-950/50 dark:text-red-400"
        />

        <MetricCard
          index={1}
          title="Revenue recovered"
          value={formatCurrency(metrics.amount_recovered)}
          subtitle="Revenue successfully recovered"
          icon={WalletCards}
          iconClassName="bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400"
          trend={{
            value: `${metrics.recovery_rate.toFixed(1)}% recovery`,
            positive: true,
          }}
        />

        <MetricCard
          index={2}
          title="Revenue remaining"
          value={formatCurrency(revenueRemaining)}
          subtitle="Still requiring recovery or escalation"
          icon={IndianRupee}
          iconClassName="bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-400"
        />

        <MetricCard
          index={3}
          title="Recovery rate"
          value={`${metrics.recovery_rate.toFixed(2)}%`}
          subtitle="Recovered revenue / revenue at risk"
          icon={TrendingUp}
          iconClassName="bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400"
        />
      </div>

      {/* Recovery progress */}
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.28, duration: 0.45 }}
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"
      >
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <h2 className="font-semibold text-slate-950 dark:text-white">
              Recovery progress
            </h2>

            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Portion of identified at-risk revenue already recovered.
            </p>
          </div>

          <span className="text-2xl font-semibold text-slate-950 dark:text-white">
            {metrics.recovery_rate.toFixed(1)}%
          </span>
        </div>

        <div className="mt-5 h-3 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${recoveryProgress}%` }}
            transition={{
              delay: 0.45,
              duration: 0.9,
              ease: "easeOut",
            }}
            className="h-full rounded-full bg-blue-600"
          />
        </div>

        <div className="mt-3 flex justify-between text-xs text-slate-400 dark:text-slate-500">
          <span>
            {formatCurrency(metrics.amount_recovered)} recovered
          </span>

          <span>
            {formatCurrency(metrics.amount_at_risk)} at risk
          </span>
        </div>
      </motion.div>

      {/* Case status */}
      <div>
        <div className="mb-4">
          <h2 className="font-semibold text-slate-950 dark:text-white">
            Case status
          </h2>

          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            What happened to the revenue cases processed by the engine.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatusCard
            index={4}
            icon={Layers3}
            title="Total cases"
            value={metrics.total_cases}
            description="Revenue recovery cases created."
            iconClassName="bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
          />

          <StatusCard
            index={5}
            icon={CheckCircle2}
            title="Recovered"
            value={metrics.recovered_cases}
            description="Cases where revenue was successfully recovered."
            iconClassName="bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400"
          />

          <StatusCard
            index={6}
            icon={AlertTriangle}
            title="Escalated"
            value={metrics.escalated_cases}
            description="Cases requiring human intervention."
            iconClassName="bg-red-50 text-red-600 dark:bg-red-950/50 dark:text-red-400"
          />

          <StatusCard
            index={7}
            icon={Clock3}
            title="Unresolved"
            value={metrics.unresolved_cases}
            description="Cases still requiring recovery action."
            iconClassName="bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-400"
          />
        </div>
      </div>

      {/* Revenue recovered by object */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.5 }}
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"
      >
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
          <div>
            <h2 className="font-semibold text-slate-950 dark:text-white">
              Recovery by revenue object
            </h2>

            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Recovered revenue across payments, subscriptions, and invoices.
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
            <TrendingUp size={14} />
            Live backend data
          </div>
        </div>

        <div className="mt-6 h-72">
          {objectChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={objectChartData}
                margin={{
                  top: 10,
                  right: 10,
                  left: 0,
                  bottom: 0,
                }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke="#334155"
                  className="opacity-30"
                />

                <XAxis
                  dataKey="name"
                  axisLine={false}
                  tickLine={false}
                  tick={{
                    fill: "#94a3b8",
                    fontSize: 12,
                  }}
                />

                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{
                    fill: "#94a3b8",
                    fontSize: 11,
                  }}
                  tickFormatter={(value) =>
                    `₹${Math.round(value / 100000)}L`
                  }
                />

                <Tooltip
                  cursor={{ fill: "rgba(148, 163, 184, 0.08)" }}
                  formatter={(value, name) => [
                    name === "recovered"
                      ? formatCurrency(Number(value))
                      : formatNumber(Number(value)),
                    name === "recovered"
                      ? "Recovered"
                      : "Attempts",
                  ]}
                  contentStyle={{
                    borderRadius: "12px",
                    border: "1px solid #334155",
                    background: "#0f172a",
                    color: "#f8fafc",
                    boxShadow:
                      "0 10px 30px rgba(0, 0, 0, 0.25)",
                  }}
                  labelStyle={{
                    color: "#cbd5e1",
                  }}
                />

                <Bar
                  dataKey="recovered"
                  radius={[7, 7, 0, 0]}
                  maxBarSize={54}
                >
                  {objectChartData.map((entry) => (
                    <Cell
                      key={entry.name}
                      fill="#2563eb"
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-slate-400 dark:text-slate-500">
              No recovery breakdown data available.
            </div>
          )}
        </div>
      </motion.div>

      {/* Engine activity */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.5 }}
        className="grid gap-4 md:grid-cols-3"
      >
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400">
              <Layers3 size={18} />
            </div>

            <div>
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
                Recovery attempts
              </p>

              <p className="text-xl font-semibold text-slate-950 dark:text-white">
                {formatNumber(metrics.total_attempts)}
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400">
              <CheckCircle2 size={18} />
            </div>

            <div>
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
                Successful attempts
              </p>

              <p className="text-xl font-semibold text-slate-950 dark:text-white">
                {formatNumber(successfulAttempts)}
              </p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-50 text-purple-600 dark:bg-purple-950/50 dark:text-purple-400">
              <TrendingUp size={18} />
            </div>

            <div>
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
                Average recovered / case
              </p>

              <p className="text-xl font-semibold text-slate-950 dark:text-white">
                {formatCurrency(averageRecovered)}
              </p>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
