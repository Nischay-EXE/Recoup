import { motion } from "motion/react"
import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Filter,
  Search,
  WalletCards,
} from "lucide-react"
import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"

import { apiGet } from "../../lib/api"
import { formatDateShort } from "../../lib/formatters"

type RecoveryCase = {
  case_id: string
  customer_id: string
  order_id?: string | null
  revenue_object_type: string
  subscription_id?: string | null
  invoice_id?: string | null
  original_payment_id?: string | null
  current_payment_id?: string | null
  amount_at_risk: number
  amount_recovered: number
  amount_remaining: number
  status: string
  current_attempt: number
  created_at: string
  resolved_at?: string | null
}

type RecoveryCasesResponse = {
  items: RecoveryCase[]
  total: number
  limit: number
  offset: number
}

const PAGE_SIZE = 20

const statusOptions = [
  { value: "", label: "All statuses" },
  { value: "open", label: "Open" },
  { value: "recovered", label: "Recovered" },
  { value: "escalated", label: "Escalated" },
  { value: "resolved", label: "Resolved" },
]

const revenueObjectOptions = [
  { value: "", label: "All revenue objects" },
  { value: "payment", label: "Payment" },
  { value: "subscription", label: "Subscription" },
  { value: "invoice", label: "Invoice" },
]

function formatINR(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value)
}


function statusConfig(status: string) {
  switch (status) {
    case "recovered":
      return {
        label: "Recovered",
        className:
          "bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:ring-emerald-900",
        icon: CheckCircle2,
      }

    case "escalated":
      return {
        label: "Escalated",
        className:
          "bg-red-50 text-red-700 ring-red-200 dark:bg-red-950/40 dark:text-red-300 dark:ring-red-900",
        icon: AlertTriangle,
      }

    case "resolved":
      return {
        label: "Resolved",
        className:
          "bg-blue-50 text-blue-700 ring-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:ring-blue-900",
        icon: CheckCircle2,
      }

    default:
      return {
        label: "Open",
        className:
          "bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:ring-amber-900",
        icon: Clock3,
      }
  }
}

function revenueObjectLabel(value: string) {
  switch (value) {
    case "payment":
      return "Payment"
    case "subscription":
      return "Subscription"
    case "invoice":
      return "Invoice"
    default:
      return value
  }
}

export default function MerchantRecoveryCases() {
  const [status, setStatus] = useState("")
  const [revenueObjectType, setRevenueObjectType] = useState("")
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(0)

  const offset = page * PAGE_SIZE

  const { data, isLoading, isError, error } = useQuery({
    queryKey: [
      "recovery-cases",
      status,
      revenueObjectType,
      page,
    ],
    queryFn: () =>
      apiGet<RecoveryCasesResponse>(
        `/recovery/cases?limit=${PAGE_SIZE}&offset=${offset}${
          status ? `&status=${encodeURIComponent(status)}` : ""
        }${
          revenueObjectType
            ? `&revenue_object_type=${encodeURIComponent(
                revenueObjectType,
              )}`
            : ""
        }`,
      ),
  })

  const cases = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const filteredCases = useMemo(() => {
    const query = search.trim().toLowerCase()

    if (!query) {
      return cases
    }

    return cases.filter((item) =>
      [
        item.case_id,
        item.customer_id,
        item.order_id,
        item.subscription_id,
        item.invoice_id,
        item.original_payment_id,
        item.current_payment_id,
        item.revenue_object_type,
      ]
        .filter(Boolean)
        .some((value) =>
          String(value).toLowerCase().includes(query),
        ),
    )
  }, [cases, search])

  function resetFilters() {
    setStatus("")
    setRevenueObjectType("")
    setSearch("")
    setPage(0)
  }

  function changeStatus(value: string) {
    setStatus(value)
    setPage(0)
  }

  function changeRevenueObject(value: string) {
    setRevenueObjectType(value)
    setPage(0)
  }

  return (
    <div className="min-h-full bg-slate-50 px-4 py-6 text-slate-900 dark:bg-slate-950 dark:text-slate-100 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-[1600px]">
        {/* Header */}
        <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2 text-sm font-medium text-blue-600 dark:text-blue-400">
              <WalletCards size={16} />
              Revenue Recovery
            </div>

            <h1 className="text-3xl font-semibold tracking-tight">
              Recovery Cases
            </h1>

            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Review revenue at risk and see which cases need
              recovery action.
            </p>
          </div>

          <div className="text-sm text-slate-500 dark:text-slate-400">
            {total.toLocaleString("en-IN")} total cases
          </div>
        </div>

        {/* Filters */}
        <div className="mb-5 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
            <div className="relative flex-1">
              <Search
                size={18}
                className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
              />

              <input
                value={search}
                onChange={(event) =>
                  setSearch(event.target.value)
                }
                placeholder="Search case, customer, payment, invoice..."
                className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 pl-11 pr-4 text-sm outline-none transition focus:border-blue-400 focus:ring-2 focus:ring-blue-100 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:border-blue-500 dark:focus:ring-blue-950"
              />
            </div>

            <div className="flex items-center gap-2">
              <Filter
                size={17}
                className="hidden text-slate-400 sm:block"
              />

              <select
                value={status}
                onChange={(event) =>
                  changeStatus(event.target.value)
                }
                className="h-11 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
              >
                {statusOptions.map((option) => (
                  <option
                    key={option.value}
                    value={option.value}
                  >
                    {option.label}
                  </option>
                ))}
              </select>

              <select
                value={revenueObjectType}
                onChange={(event) =>
                  changeRevenueObject(event.target.value)
                }
                className="h-11 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
              >
                {revenueObjectOptions.map((option) => (
                  <option
                    key={option.value}
                    value={option.value}
                  >
                    {option.label}
                  </option>
                ))}
              </select>

              {(status || revenueObjectType || search) && (
                <button
                  type="button"
                  onClick={resetFilters}
                  className="h-11 rounded-xl px-3 text-sm font-medium text-slate-500 transition hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                >
                  Clear
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Error */}
        {isError && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
            Failed to load recovery cases.
            {error instanceof Error && (
              <span className="ml-1">{error.message}</span>
            )}
          </div>
        )}

        {/* Loading */}
        {isLoading && (
          <div className="space-y-3">
            {Array.from({ length: 8 }).map((_, index) => (
              <div
                key={index}
                className="h-20 animate-pulse rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
              />
            ))}
          </div>
        )}

        {/* Table */}
        {!isLoading && !isError && (
          <>
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
              {/* Desktop header */}
              <div className="hidden grid-cols-[minmax(300px,2fr)_140px_130px_130px_130px_100px_130px] gap-4 border-b border-slate-200 bg-slate-50 px-5 py-3 text-[11px] font-semibold uppercase tracking-wide text-slate-400 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-500 lg:grid">
                <div>Case</div>
                <div>Type</div>
                <div>At risk</div>
                <div>Recovered</div>
                <div>Remaining</div>
                <div>Attempt</div>
                <div>Status</div>
              </div>

              {filteredCases.length === 0 && (
                <div className="px-6 py-16 text-center">
                  <WalletCards
                    size={30}
                    className="mx-auto mb-3 text-slate-300 dark:text-slate-700"
                  />

                  <h2 className="font-medium">
                    No recovery cases found
                  </h2>

                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    Try changing your filters or search term.
                  </p>
                </div>
              )}

              <div className="divide-y divide-slate-100 dark:divide-slate-800">
                {filteredCases.map((item, index) => {
                  const statusInfo = statusConfig(item.status)
                  const StatusIcon = statusInfo.icon

                  return (
                    <motion.div
                      key={item.case_id}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{
                        duration: 0.2,
                        delay: Math.min(index * 0.025, 0.3),
                      }}
                      whileHover={{
                        backgroundColor:
                          "rgba(148, 163, 184, 0.06)",
                      }}
                    >
                      <Link
                        to={`/merchant/cases/${item.case_id}`}
                        className="block px-5 py-4 outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500"
                      >
                        {/* Desktop */}
                        <div className="hidden grid-cols-[minmax(300px,2fr)_140px_130px_130px_130px_100px_130px] items-center gap-4 lg:grid">
                          <div className="min-w-0">
                            <div className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
                              {item.case_id}
                            </div>

                            <div className="mt-1 truncate text-xs text-slate-400 dark:text-slate-500">
                              {item.customer_id}
                            </div>

                            <div className="mt-1 text-[11px] text-slate-400 dark:text-slate-600">
                              {formatDateShort(item.created_at)}
                            </div>
                          </div>

                          <div>
                            <span className="inline-flex rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                              {revenueObjectLabel(
                                item.revenue_object_type,
                              )}
                            </span>
                          </div>

                          <div>
                            <div className="text-sm font-semibold">
                              {formatINR(item.amount_at_risk)}
                            </div>

                            <div className="mt-1 text-[11px] text-slate-400">
                              At risk
                            </div>
                          </div>

                          <div>
                            <div className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                              {formatINR(item.amount_recovered)}
                            </div>

                            <div className="mt-1 text-[11px] text-slate-400">
                              Recovered
                            </div>
                          </div>

                          <div>
                            <div className="text-sm font-semibold">
                              {formatINR(item.amount_remaining)}
                            </div>

                            <div className="mt-1 text-[11px] text-slate-400">
                              Remaining
                            </div>
                          </div>

                          <div>
                            <div className="text-sm font-semibold">
                              {item.current_attempt}
                            </div>

                            <div className="mt-1 text-[11px] text-slate-400">
                              Attempt
                            </div>
                          </div>

                          <div>
                            <span
                              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${statusInfo.className}`}
                            >
                              <StatusIcon size={13} />
                              {statusInfo.label}
                            </span>
                          </div>
                        </div>

                        {/* Mobile */}
                        <div className="lg:hidden">
                          <div className="flex items-start justify-between gap-4">
                            <div className="min-w-0">
                              <div className="truncate text-sm font-semibold">
                                {item.case_id}
                              </div>

                              <div className="mt-1 truncate text-xs text-slate-400">
                                {item.customer_id}
                              </div>
                            </div>

                            <span
                              className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-1 text-[11px] font-medium ring-1 ring-inset ${statusInfo.className}`}
                            >
                              <StatusIcon size={12} />
                              {statusInfo.label}
                            </span>
                          </div>

                          <div className="mt-4 grid grid-cols-3 gap-3">
                            <div>
                              <div className="text-[11px] text-slate-400">
                                At risk
                              </div>
                              <div className="mt-1 text-sm font-semibold">
                                {formatINR(
                                  item.amount_at_risk,
                                )}
                              </div>
                            </div>

                            <div>
                              <div className="text-[11px] text-slate-400">
                                Recovered
                              </div>
                              <div className="mt-1 text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                                {formatINR(
                                  item.amount_recovered,
                                )}
                              </div>
                            </div>

                            <div>
                              <div className="text-[11px] text-slate-400">
                                Remaining
                              </div>
                              <div className="mt-1 text-sm font-semibold">
                                {formatINR(
                                  item.amount_remaining,
                                )}
                              </div>
                            </div>
                          </div>

                          <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
                            <span>
                              {revenueObjectLabel(
                                item.revenue_object_type,
                              )}
                            </span>

                            <span>
                              Attempt {item.current_attempt}
                            </span>
                          </div>
                        </div>
                      </Link>
                    </motion.div>
                  )
                })}
              </div>
            </div>

            {/* Pagination */}
            {total > 0 && (
              <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Showing{" "}
                  <span className="font-medium text-slate-700 dark:text-slate-200">
                    {offset + 1}
                  </span>
                  {" – "}
                  <span className="font-medium text-slate-700 dark:text-slate-200">
                    {Math.min(offset + cases.length, total)}
                  </span>{" "}
                  of{" "}
                  <span className="font-medium text-slate-700 dark:text-slate-200">
                    {total}
                  </span>{" "}
                  cases
                </p>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={page === 0}
                    onClick={() =>
                      setPage((current) =>
                        Math.max(0, current - 1),
                      )
                    }
                    className="inline-flex h-9 items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 text-sm font-medium text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                  >
                    <ChevronLeft size={16} />
                    Previous
                  </button>

                  <span className="px-2 text-xs text-slate-500 dark:text-slate-400">
                    Page {page + 1} of {totalPages}
                  </span>

                  <button
                    type="button"
                    disabled={page >= totalPages - 1}
                    onClick={() =>
                      setPage((current) =>
                        Math.min(totalPages - 1, current + 1),
                      )
                    }
                    className="inline-flex h-9 items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 text-sm font-medium text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                  >
                    Next
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}