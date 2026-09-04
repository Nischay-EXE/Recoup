import { motion } from "motion/react"
import { useQuery } from "@tanstack/react-query"
import {
  AlertTriangle,
  ArrowLeft,
  Bot,
  CheckCircle2,
  Clock3,
  ExternalLink,
  FileCheck2,
  Mail,
  ShieldCheck,
  UserRound,
  Zap,
} from "lucide-react"
import { Link, useParams } from "react-router-dom"

import { apiGet } from "../../lib/api"
import type {
  RecoveryCaseTimeline,
  RecoveryTimelineEvent,
} from "../../types/recovery"
import { formatDateTime } from "../../lib/formatters"

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value)

const formatLabel = (value: string) =>
  value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase())


function StatusBadge({ status }: { status: string }) {
  const config: Record<
    string,
    {
      className: string
      icon: typeof CheckCircle2
    }
  > = {
    recovered: {
      className:
        "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
      icon: CheckCircle2,
    },
    resolved: {
      className:
        "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
      icon: CheckCircle2,
    },
    escalated: {
      className:
        "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300",
      icon: AlertTriangle,
    },
    open: {
      className:
        "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
      icon: Clock3,
    },
  }

  const current = config[status] ?? {
    className:
      "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
    icon: Clock3,
  }

  const Icon = current.icon

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${current.className}`}
    >
      <Icon size={13} />
      {formatLabel(status)}
    </span>
  )
}

function getEventIcon(eventType: string) {
  switch (eventType) {
    case "case_created":
      return FileCheck2
    case "decision_created":
      return Bot
    case "guardrail_evaluated":
      return ShieldCheck
    case "attempt_created":
      return Zap
    case "attempt_scheduled":
      return Clock3
    case "attempt_executed":
      return ExternalLink
    case "attempt_resolved":
      return CheckCircle2
    case "case_resolved":
      return CheckCircle2
    case "escalation_created":
      return AlertTriangle
    default:
      return Clock3
  }
}

function getEventIconClass(eventType: string) {
  switch (eventType) {
    case "decision_created":
      return "bg-purple-50 text-purple-600 dark:bg-purple-950 dark:text-purple-300"

    case "guardrail_evaluated":
      return "bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-blue-300"

    case "attempt_executed":
      return "bg-indigo-50 text-indigo-600 dark:bg-indigo-950 dark:text-indigo-300"

    case "attempt_resolved":
    case "case_resolved":
      return "bg-emerald-50 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-300"

    case "escalation_created":
      return "bg-red-50 text-red-600 dark:bg-red-950 dark:text-red-300"

    default:
      return "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
  }
}

function DetailValue({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div>
      <p className="text-xs text-slate-400 dark:text-slate-500">
        {label}
      </p>

      <p className="mt-1 break-all text-sm font-medium text-slate-900 dark:text-slate-100">
        {value}
      </p>
    </div>
  )
}

function TimelineDetails({
  event,
}: {
  event: RecoveryTimelineEvent
}) {
  const details = event.details as Record<
    string,
    string | number | boolean | null
  >

  if (event.event_type === "decision_created") {
    return (
      <div className="mt-4 grid gap-3 rounded-xl border border-purple-100 bg-purple-50/50 p-4 dark:border-purple-900 dark:bg-purple-950/30 md:grid-cols-2">
        <DetailValue
          label="Action"
          value={String(details.action ?? "Unknown")}
        />

        <DetailValue
          label="Channel"
          value={String(details.channel ?? "Unknown")}
        />

        <DetailValue
          label="Priority"
          value={String(details.priority ?? "Unknown")}
        />

        <DetailValue
          label="Confidence"
          value={
            details.confidence !== null &&
            details.confidence !== undefined
              ? `${Number(details.confidence) * 100}%`
              : "Unknown"
          }
        />

        <div className="md:col-span-2">
          <DetailValue
            label="Reason"
            value={String(
              details.reason ?? "No reason provided",
            )}
          />
        </div>

        {details.message != null && (
          <div className="md:col-span-2 flex gap-3 rounded-lg border border-purple-100 bg-white p-3 dark:border-purple-900 dark:bg-slate-900">
            <Mail
              size={16}
              className="mt-0.5 shrink-0 text-purple-600"
            />

            <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
              {String(details.message)}
            </p>
          </div>
        )}
      </div>
    )
  }

  if (event.event_type === "guardrail_evaluated") {
    const approved = details.policy_result === "approved"

    return (
      <div
        className={`mt-4 rounded-xl border p-4 ${
          approved
            ? "border-emerald-100 bg-emerald-50/50 dark:border-emerald-900 dark:bg-emerald-950/30"
            : "border-red-100 bg-red-50/50 dark:border-red-900 dark:bg-red-950/30"
        }`}
      >
        <div className="flex items-center gap-2">
          <ShieldCheck
            size={17}
            className={
              approved
                ? "text-emerald-600"
                : "text-red-600"
            }
          />

          <span
            className={`text-sm font-semibold ${
              approved
                ? "text-emerald-700 dark:text-emerald-300"
                : "text-red-700 dark:text-red-300"
            }`}
          >
            Policy {approved ? "approved" : "blocked"}
          </span>
        </div>

        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          {String(
            details.policy_reason ??
              "No policy reason provided.",
          )}
        </p>

        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <span className="rounded-md bg-white px-2 py-1 text-slate-600 dark:bg-slate-900 dark:text-slate-300">
            Action: {String(details.action ?? "Unknown")}
          </span>

          <span className="rounded-md bg-white px-2 py-1 text-slate-600 dark:bg-slate-900 dark:text-slate-300">
            Channel: {String(details.channel ?? "Unknown")}
          </span>
        </div>
      </div>
    )
  }

  if (event.event_type === "attempt_executed") {
    return (
      <div className="mt-4 grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/50 md:grid-cols-2">
        <DetailValue
          label="Action"
          value={String(details.action ?? "Unknown")}
        />

        <DetailValue
          label="Channel"
          value={String(details.channel ?? "Unknown")}
        />

        <DetailValue
          label="Status"
          value={String(details.status ?? "Unknown")}
        />

        <DetailValue
          label="Provider"
          value={String(
            details.execution_provider ?? "Unknown",
          )}
        />

        {details.external_execution_id != null && (
          <DetailValue
            label="External execution ID"
            value={String(details.external_execution_id)}
          />
        )}

        {details.execution_error != null && (
          <div className="md:col-span-2">
            <DetailValue
              label="Execution error"
              value={String(details.execution_error)}
            />
          </div>
        )}
      </div>
    )
  }

  if (event.event_type === "attempt_resolved") {
    return (
      <div className="mt-4 rounded-xl border border-emerald-100 bg-emerald-50/50 p-4 dark:border-emerald-900 dark:bg-emerald-950/30">
        <div className="grid gap-3 md:grid-cols-2">
          <DetailValue
            label="Result"
            value={String(details.status ?? "Unknown")}
          />

          <DetailValue
            label="Amount recovered"
            value={formatCurrency(
              Number(details.amount_recovered ?? 0),
            )}
          />
        </div>
      </div>
    )
  }

  return null
}

function TimelineEvent({
  event,
  index,
  isLast,
}: {
  event: RecoveryTimelineEvent
  index: number
  isLast: boolean
}) {
  const Icon = getEventIcon(event.event_type)

  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{
        duration: 0.35,
        delay: Math.min(index * 0.06, 0.4),
      }}
      className="relative flex gap-4"
    >
      <div className="relative flex shrink-0 flex-col items-center">
        <div
          className={`z-10 flex h-10 w-10 items-center justify-center rounded-xl ${getEventIconClass(
            event.event_type,
          )}`}
        >
          <Icon size={18} />
        </div>

        {!isLast && (
          <div className="absolute top-10 h-[calc(100%+1rem)] w-px bg-slate-200 dark:bg-slate-700" />
        )}
      </div>

      <div className="min-w-0 flex-1 pb-8">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <div className="flex flex-col justify-between gap-2 sm:flex-row">
            <div>
              <h3 className="font-semibold text-slate-900 dark:text-white">
                {event.description}
              </h3>

              <p className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">
                {formatLabel(event.event_type)}
              </p>
            </div>

            <time className="shrink-0 text-xs text-slate-400 dark:text-slate-500">
              {formatDateTime(event.timestamp)}
            </time>
          </div>

          <TimelineDetails event={event} />
        </div>
      </div>
    </motion.div>
  )
}

export default function MerchantCaseDetail() {
  const { caseId } = useParams<{ caseId: string }>()

  const caseQuery = useQuery({
    queryKey: ["recovery", "case-timeline", caseId],
    queryFn: () =>
      apiGet<RecoveryCaseTimeline>(
        `/recovery/cases/${caseId}/timeline`,
      ),
    enabled: Boolean(caseId),
  })

  if (caseQuery.isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800" />

        <div className="h-52 animate-pulse rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900" />

        <div className="h-[700px] animate-pulse rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900" />
      </div>
    )
  }

  if (caseQuery.isError || !caseQuery.data) {
    return (
      <div className="space-y-5">
        <Link
          to="/merchant/cases"
          className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
        >
          <ArrowLeft size={16} />
          Back to recovery cases
        </Link>

        <div className="rounded-2xl border border-red-200 bg-red-50 p-6 dark:border-red-900 dark:bg-red-950/30">
          <div className="flex items-center gap-3">
            <AlertTriangle
              className="text-red-600"
              size={20}
            />

            <div>
              <p className="font-semibold text-red-900 dark:text-red-200">
                Recovery case not found
              </p>

              <p className="mt-1 text-sm text-red-700 dark:text-red-300">
                The case may no longer exist or the backend is
                unavailable.
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const recoveryCase = caseQuery.data

  const remaining =
    recoveryCase.amount_at_risk -
    recoveryCase.amount_recovered

  const recoveryPercentage =
    recoveryCase.amount_at_risk > 0
      ? Math.min(
          100,
          (recoveryCase.amount_recovered /
            recoveryCase.amount_at_risk) *
            100,
        )
      : 0

  const decisionEvent = recoveryCase.timeline.find(
    (event) => event.event_type === "decision_created",
  )

  const guardrailEvent = recoveryCase.timeline.find(
    (event) => event.event_type === "guardrail_evaluated",
  )

  const executionEvent = recoveryCase.timeline.find(
    (event) => event.event_type === "attempt_executed",
  )

  return (
    <div className="space-y-6">
      <Link
        to="/merchant/cases"
        className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 transition hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
      >
        <ArrowLeft size={16} />
        Back to recovery cases
      </Link>

      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900"
      >
        <div className="flex flex-col justify-between gap-5 lg:flex-row">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                {formatLabel(
                  recoveryCase.revenue_object_type,
                )}
              </span>

              <StatusBadge status={recoveryCase.status} />
            </div>

            <h1 className="mt-3 break-all text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">
              {recoveryCase.case_id}
            </h1>

            <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-slate-500 dark:text-slate-400">
              <span className="flex items-center gap-1.5">
                <UserRound size={14} />
                {recoveryCase.customer_id ??
                  "No customer ID"}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-6 lg:min-w-[480px]">
            <div>
              <p className="text-xs text-slate-400 dark:text-slate-500">
                At risk
              </p>

              <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-white">
                {formatCurrency(
                  recoveryCase.amount_at_risk,
                )}
              </p>
            </div>

            <div>
              <p className="text-xs text-slate-400 dark:text-slate-500">
                Recovered
              </p>

              <p className="mt-1 text-xl font-semibold text-emerald-600 dark:text-emerald-400">
                {formatCurrency(
                  recoveryCase.amount_recovered,
                )}
              </p>
            </div>

            <div>
              <p className="text-xs text-slate-400 dark:text-slate-500">
                Remaining
              </p>

              <p className="mt-1 text-xl font-semibold text-slate-950 dark:text-white">
                {formatCurrency(remaining)}
              </p>
            </div>
          </div>
        </div>

        <div className="mt-6 border-t border-slate-100 pt-5 dark:border-slate-800">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-slate-500 dark:text-slate-400">
              Recovery progress
            </span>

            <span className="font-semibold text-slate-900 dark:text-white">
              {recoveryPercentage.toFixed(1)}%
            </span>
          </div>

          <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
            <motion.div
              initial={{ width: 0 }}
              animate={{
                width: `${recoveryPercentage}%`,
              }}
              transition={{
                duration: 0.8,
                ease: "easeOut",
              }}
              className="h-full rounded-full bg-blue-600"
            />
          </div>
        </div>
      </motion.div>

      {(decisionEvent ||
        guardrailEvent ||
        executionEvent) && (
        <div className="grid gap-4 lg:grid-cols-3">
          {decisionEvent && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="rounded-2xl border border-purple-100 bg-purple-50/60 p-5 dark:border-purple-900 dark:bg-purple-950/20"
            >
              <div className="flex items-center gap-2 text-purple-700 dark:text-purple-300">
                <Bot size={18} />
                <span className="text-sm font-semibold">
                  AI strategy
                </span>
              </div>

              <p className="mt-3 text-lg font-semibold text-slate-950 dark:text-white">
                {formatLabel(
                  String(
                    decisionEvent.details.action ??
                      "No action",
                  ),
                )}
              </p>

              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                via{" "}
                {formatLabel(
                  String(
                    decisionEvent.details.channel ??
                      "unknown",
                  ),
                )}
              </p>

              <p className="mt-4 text-sm leading-6 text-slate-600 dark:text-slate-300">
                {String(
                  decisionEvent.details.reason ??
                    "No strategy reason provided.",
                )}
              </p>
            </motion.div>
          )}

          {guardrailEvent && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.16 }}
              className="rounded-2xl border border-blue-100 bg-blue-50/60 p-5 dark:border-blue-900 dark:bg-blue-950/20"
            >
              <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300">
                <ShieldCheck size={18} />
                <span className="text-sm font-semibold">
                  Guardrail
                </span>
              </div>

              <p className="mt-3 text-lg font-semibold text-slate-950 dark:text-white">
                {formatLabel(
                  String(
                    guardrailEvent.details
                      .policy_result ?? "Unknown",
                  ),
                )}
              </p>

              <p className="mt-4 text-sm leading-6 text-slate-600 dark:text-slate-300">
                {String(
                  guardrailEvent.details
                    .policy_reason ??
                    "No policy reason provided.",
                )}
              </p>
            </motion.div>
          )}

          {executionEvent && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.22 }}
              className="rounded-2xl border border-emerald-100 bg-emerald-50/60 p-5 dark:border-emerald-900 dark:bg-emerald-950/20"
            >
              <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
                <Zap size={18} />
                <span className="text-sm font-semibold">
                  Execution
                </span>
              </div>

              <p className="mt-3 text-lg font-semibold text-slate-950 dark:text-white">
                {formatLabel(
                  String(
                    executionEvent.details.status ??
                      "Unknown",
                  ),
                )}
              </p>

              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                {formatLabel(
                  String(
                    executionEvent.details
                      .execution_provider ??
                      "Unknown provider",
                  ),
                )}
              </p>

              <p className="mt-4 text-sm leading-6 text-slate-600 dark:text-slate-300">
                {formatLabel(
                  String(
                    executionEvent.details.action ??
                      "Unknown action",
                  ),
                )}{" "}
                via{" "}
                {formatLabel(
                  String(
                    executionEvent.details.channel ??
                      "unknown channel",
                  ),
                )}
              </p>
            </motion.div>
          )}
        </div>
      )}

      <div>
        <div className="mb-5">
          <h2 className="text-xl font-semibold text-slate-950 dark:text-white">
            Recovery timeline
          </h2>

          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Complete audit trail of how this case was
            handled.
          </p>
        </div>

        <div>
          {recoveryCase.timeline.map((event, index) => (
            <TimelineEvent
              key={`${event.timestamp}-${event.event_type}-${index}`}
              event={event}
              index={index}
              isLast={
                index === recoveryCase.timeline.length - 1
              }
            />
          ))}
        </div>
      </div>
    </div>
  )
}