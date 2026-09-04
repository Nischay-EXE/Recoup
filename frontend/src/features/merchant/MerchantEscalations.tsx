import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  FileText,
  Loader2,
  MessageSquare,
  UserRound,
  Users,
} from "lucide-react"

import { apiGet } from "../../lib/api"
import { formatDateShort } from "../../lib/formatters"

type RecoveryCase = {
  case_id: string
  customer_id: string
  revenue_object_type: string
  amount_at_risk: number
  amount_recovered: number
  amount_remaining: number
  status: string
  current_attempt: number
  created_at: string
}

type RecoveryCasesResponse = {
  items: RecoveryCase[]
  total: number
  limit: number
  offset: number
}

type Escalation = {
  case_id: string
  status: string
  reason_code: string
  priority: string
  assigned_team: string | null
  assigned_to: string | null
  summary: string
  diagnosis: string
  recommended_action: string
  amount_at_risk: number
  amount_recovered: number
  amount_remaining: number
  created_at: string
  resolved_at: string | null
}

type EscalationNote = {
  id: number
  case_id: string
  note: string
  created_by: string | null
  created_at: string
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value)
}


function labelize(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

async function apiRequest<T>(
  path: string,
  options: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  })

  if (!response.ok) {
    let message = `Request failed: ${response.status}`

    try {
      const body = await response.json()
      if (body.detail) {
        message = body.detail
      }
    } catch {
      // Keep the default error message.
    }

    throw new Error(message)
  }

  return response.json() as Promise<T>
}

function StatusBadge({ status }: { status: string }) {
  const resolved = status === "resolved"

  return (
    <span
      className={[
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1",
        "text-xs font-medium",
        resolved
          ? "border border-blue-500/20 bg-blue-500/10 text-blue-600 dark:text-blue-300"
          : "border border-red-500/20 bg-red-500/10 text-red-600 dark:text-red-300",
      ].join(" ")}
    >
      {resolved ? (
        <CheckCircle2 size={13} />
      ) : (
        <AlertTriangle size={13} />
      )}
      {labelize(status)}
    </span>
  )
}

function Metric({
  label,
  value,
  tone = "default",
}: {
  label: string
  value: string
  tone?: "default" | "danger" | "success"
}) {
  return (
    <div>
      <p className="text-xs text-slate-500 dark:text-slate-400">
        {label}
      </p>

      <p
        className={[
          "mt-1 text-lg font-semibold",
          tone === "danger"
            ? "text-red-600 dark:text-red-400"
            : tone === "success"
              ? "text-emerald-600 dark:text-emerald-400"
              : "text-slate-900 dark:text-white",
        ].join(" ")}
      >
        {value}
      </p>
    </div>
  )
}

export default function MerchantEscalations() {
  const queryClient = useQueryClient()

  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(
    null,
  )

  const [assignedTeam, setAssignedTeam] = useState("")
  const [assignedTo, setAssignedTo] = useState("")
  const [note, setNote] = useState("")
  const [actionError, setActionError] = useState<string | null>(null)

  const casesQuery = useQuery({
    queryKey: ["recovery-cases", "escalated"],
    queryFn: () =>
      apiGet<RecoveryCasesResponse>(
        "/recovery/cases?status=escalated&limit=100",
      ),
  })

  const escalationQuery = useQuery({
    queryKey: ["escalation", selectedCaseId],
    queryFn: () =>
      apiGet<Escalation>(
        `/recovery/cases/${selectedCaseId}/escalation`,
      ),
    enabled: Boolean(selectedCaseId),
  })

  const escalation = escalationQuery.data

  const assignmentMutation = useMutation({
    mutationFn: () =>
      apiRequest<Escalation>(
        `/recovery/cases/${selectedCaseId}/escalation/assignment`,
        {
          method: "PATCH",
          body: JSON.stringify({
            assigned_team: assignedTeam || null,
            assigned_to: assignedTo || null,
          }),
        },
      ),
    onSuccess: (data) => {
      queryClient.setQueryData(
        ["escalation", selectedCaseId],
        data,
      )
      setActionError(null)
    },
    onError: (error) => {
      setActionError(
        error instanceof Error
          ? error.message
          : "Unable to update assignment.",
      )
    },
  })

  const noteMutation = useMutation({
    mutationFn: () =>
      apiRequest<EscalationNote>(
        `/recovery/cases/${selectedCaseId}/escalation/notes`,
        {
          method: "POST",
          body: JSON.stringify({
            note: note.trim(),
            created_by: "merchant-portal",
          }),
        },
      ),
    onSuccess: () => {
      setNote("")
      setActionError(null)
    },
    onError: (error) => {
      setActionError(
        error instanceof Error
          ? error.message
          : "Unable to add note.",
      )
    },
  })

  const resolveMutation = useMutation({
    mutationFn: () =>
      apiRequest<Escalation>(
        `/recovery/cases/${selectedCaseId}/escalation/resolve`,
        {
          method: "POST",
        },
      ),
    onSuccess: (data) => {
      queryClient.setQueryData(
        ["escalation", selectedCaseId],
        data,
      )

      queryClient.invalidateQueries({
        queryKey: ["recovery-cases", "escalated"],
      })

      setActionError(null)
    },
    onError: (error) => {
      setActionError(
        error instanceof Error
          ? error.message
          : "Unable to resolve escalation.",
      )
    },
  })

  const selectEscalation = (caseItem: RecoveryCase) => {
    setSelectedCaseId(caseItem.case_id)
    setActionError(null)
    setAssignedTeam("")
    setAssignedTo("")
    setNote("")
  }

  if (casesQuery.isLoading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <Loader2 className="animate-spin text-blue-500" size={24} />
      </div>
    )
  }

  if (casesQuery.isError) {
    return (
      <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-6">
        <h1 className="text-lg font-semibold text-red-600 dark:text-red-400">
          Unable to load escalations
        </h1>

        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          {casesQuery.error instanceof Error
            ? casesQuery.error.message
            : "The recovery API could not be reached."}
        </p>
      </div>
    )
  }

  const cases = casesQuery.data?.items ?? []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-blue-500">
            Revenue Recovery
          </p>

          <h1 className="mt-1 text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">
            Escalations
          </h1>

          <p className="mt-2 max-w-2xl text-sm text-slate-500 dark:text-slate-400">
            Review cases that require human intervention and understand
            why automated recovery stopped.
          </p>
        </div>

        <div className="rounded-full border border-red-500/20 bg-red-500/5 px-3 py-1.5 text-sm font-medium text-red-600 dark:text-red-300">
          {cases.length} open escalations
        </div>
      </div>

      {/* Main layout */}
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_430px]">
        {/* Escalation list */}
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="border-b border-slate-200 px-5 py-4 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <AlertTriangle
                size={17}
                className="text-red-500"
              />

              <h2 className="font-semibold text-slate-900 dark:text-white">
                Cases requiring attention
              </h2>
            </div>

            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Select a case to inspect the recovery history and support
              context.
            </p>
          </div>

          {cases.length === 0 ? (
            <div className="p-10 text-center">
              <CheckCircle2
                className="mx-auto text-emerald-500"
                size={32}
              />

              <h3 className="mt-3 font-semibold text-slate-900 dark:text-white">
                No escalations
              </h3>

              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                All currently processed cases have an automated path.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-slate-200 dark:divide-slate-800">
              {cases.map((caseItem) => (
                <button
                  key={caseItem.case_id}
                  type="button"
                  onClick={() => selectEscalation(caseItem)}
                  className={[
                    "w-full px-5 py-4 text-left transition",
                    "hover:bg-slate-50 dark:hover:bg-slate-800/50",
                    selectedCaseId === caseItem.case_id
                      ? "bg-blue-500/5 dark:bg-blue-500/10"
                      : "",
                  ].join(" ")}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-900 dark:text-white">
                        {caseItem.case_id}
                      </p>

                      <p className="mt-1 truncate text-xs text-slate-500 dark:text-slate-400">
                        {caseItem.customer_id}
                      </p>

                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium capitalize text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                          {caseItem.revenue_object_type}
                        </span>

                        <StatusBadge status={caseItem.status} />
                      </div>
                    </div>

                    <div className="shrink-0 text-right">
                      <p className="text-sm font-semibold text-slate-900 dark:text-white">
                        {formatCurrency(caseItem.amount_remaining)}
                      </p>

                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        remaining
                      </p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </section>

        {/* Detail */}
        <aside className="xl:sticky xl:top-6 xl:self-start">
          {!selectedCaseId ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center dark:border-slate-700 dark:bg-slate-900">
              <FileText
                className="mx-auto text-slate-400"
                size={30}
              />

              <h3 className="mt-3 font-semibold text-slate-900 dark:text-white">
                Select an escalation
              </h3>

              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                The support context for the selected case will appear
                here.
              </p>
            </div>
          ) : escalationQuery.isLoading ? (
            <div className="flex min-h-[300px] items-center justify-center rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
              <Loader2
                className="animate-spin text-blue-500"
                size={24}
              />
            </div>
          ) : escalationQuery.isError || !escalation ? (
            <div className="rounded-2xl border border-red-500/20 bg-white p-6 dark:bg-slate-900">
              <p className="font-semibold text-red-600 dark:text-red-400">
                Unable to load escalation
              </p>

              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                {escalationQuery.error instanceof Error
                  ? escalationQuery.error.message
                  : "Escalation details were not found."}
              </p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
              {/* Detail header */}
              <div className="border-b border-slate-200 p-5 dark:border-slate-800">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <AlertTriangle
                        size={18}
                        className="text-red-500"
                      />

                      <span className="text-xs font-medium uppercase tracking-wide text-red-500">
                        Human intervention
                      </span>
                    </div>

                    <h2 className="mt-2 break-all text-lg font-semibold text-slate-900 dark:text-white">
                      {escalation.case_id}
                    </h2>
                  </div>

                  <StatusBadge status={escalation.status} />
                </div>
              </div>

              {/* Financial exposure */}
              <div className="grid grid-cols-3 gap-4 border-b border-slate-200 p-5 dark:border-slate-800">
                <Metric
                  label="At risk"
                  value={formatCurrency(
                    escalation.amount_at_risk,
                  )}
                  tone="danger"
                />

                <Metric
                  label="Recovered"
                  value={formatCurrency(
                    escalation.amount_recovered,
                  )}
                  tone="success"
                />

                <Metric
                  label="Remaining"
                  value={formatCurrency(
                    escalation.amount_remaining,
                  )}
                  tone={
                    escalation.amount_remaining > 0
                      ? "danger"
                      : "success"
                  }
                />
              </div>

              <div className="space-y-5 p-5">
                {/* Why */}
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                    Escalation reason
                  </p>

                  <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-white">
                    {labelize(escalation.reason_code)}
                  </p>
                </div>

                {/* Summary */}
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                    Summary
                  </p>

                  <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                    {escalation.summary}
                  </p>
                </div>

                {/* Diagnosis */}
                <div className="rounded-xl border border-purple-500/20 bg-purple-500/5 p-4">
                  <div className="flex items-center gap-2">
                    <FileText
                      size={15}
                      className="text-purple-500"
                    />

                    <p className="text-xs font-semibold uppercase tracking-wide text-purple-600 dark:text-purple-300">
                      Recovery diagnosis
                    </p>
                  </div>

                  <p className="mt-2 text-sm leading-6 text-slate-700 dark:text-slate-300">
                    {escalation.diagnosis}
                  </p>
                </div>

                {/* Recommended action */}
                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-300">
                    Recommended action
                  </p>

                  <p className="mt-2 text-sm leading-6 text-slate-700 dark:text-slate-300">
                    {escalation.recommended_action}
                  </p>
                </div>

                {/* Assignment */}
                <div>
                  <div className="flex items-center gap-2">
                    <Users size={15} className="text-slate-400" />

                    <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                      Assignment
                    </p>
                  </div>

                  <div className="mt-3 grid gap-3">
                    <input
                      value={assignedTeam}
                      onChange={(event) =>
                        setAssignedTeam(event.target.value)
                      }
                      placeholder={
                        escalation.assigned_team ??
                        "Team, e.g. payments"
                      }
                      disabled={
                        escalation.status === "resolved"
                      }
                      className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
                    />

                    <input
                      value={assignedTo}
                      onChange={(event) =>
                        setAssignedTo(event.target.value)
                      }
                      placeholder={
                        escalation.assigned_to ??
                        "Person / owner"
                      }
                      disabled={
                        escalation.status === "resolved"
                      }
                      className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
                    />

                    <button
                      type="button"
                      disabled={
                        escalation.status === "resolved" ||
                        assignmentMutation.isPending
                      }
                      onClick={() =>
                        assignmentMutation.mutate()
                      }
                      className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {assignmentMutation.isPending && (
                        <Loader2
                          size={15}
                          className="animate-spin"
                        />
                      )}

                      Save assignment
                    </button>
                  </div>

                  {(escalation.assigned_team ||
                    escalation.assigned_to) && (
                    <div className="mt-3 rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60">
                      <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                        <UserRound size={13} />
                        Currently assigned
                      </div>

                      <p className="mt-1 text-sm font-medium text-slate-900 dark:text-white">
                        {escalation.assigned_team ??
                          "No team"}{" "}
                        {escalation.assigned_to
                          ? `· ${escalation.assigned_to}`
                          : ""}
                      </p>
                    </div>
                  )}
                </div>

                {/* Notes */}
                <div>
                  <div className="flex items-center gap-2">
                    <MessageSquare
                      size={15}
                      className="text-slate-400"
                    />

                    <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                      Support note
                    </p>
                  </div>

                  <textarea
                    value={note}
                    onChange={(event) =>
                      setNote(event.target.value)
                    }
                    disabled={
                      escalation.status === "resolved"
                    }
                    placeholder="Add context for the support team..."
                    rows={4}
                    className="mt-3 w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-blue-500 dark:border-slate-700 dark:bg-slate-950 dark:text-white"
                  />

                  <button
                    type="button"
                    disabled={
                      escalation.status === "resolved" ||
                      !note.trim() ||
                      noteMutation.isPending
                    }
                    onClick={() => noteMutation.mutate()}
                    className="mt-2 inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                  >
                    {noteMutation.isPending && (
                      <Loader2
                        size={15}
                        className="animate-spin"
                      />
                    )}

                    Add note
                  </button>
                </div>

                {actionError && (
                  <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-600 dark:text-red-300">
                    {actionError}
                  </div>
                )}

                {/* Resolve */}
                {escalation.status !== "resolved" && (
                  <div className="border-t border-slate-200 pt-5 dark:border-slate-800">
                    <button
                      type="button"
                      disabled={resolveMutation.isPending}
                      onClick={() => resolveMutation.mutate()}
                      className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {resolveMutation.isPending ? (
                        <Loader2
                          size={16}
                          className="animate-spin"
                        />
                      ) : (
                        <CheckCircle2 size={16} />
                      )}

                      Resolve escalation
                    </button>
                  </div>
                )}

                {/* Metadata */}
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <Clock3 size={13} />
                  Created {formatDateShort(escalation.created_at)}
                </div>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}