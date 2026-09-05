import { Layers3 } from "lucide-react"
import { useQuery } from "@tanstack/react-query"

import { apiGet } from "../../lib/api"
import type { RecoveryBatchesResponse } from "../../types/batches"

type BatchSelectorProps = {
  value: string
  onChange: (batchId: string) => void
  className?: string
}

export default function BatchSelector({ value, onChange, className = "" }: BatchSelectorProps) {
  const query = useQuery({
    queryKey: ["recovery-batches", "selector"],
    queryFn: () => apiGet<RecoveryBatchesResponse>("/recovery/batches?limit=100&offset=0"),
    staleTime: 10_000,
  })

  const batches = query.data?.items ?? []

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <Layers3 className="h-4 w-4 shrink-0 text-slate-400" />
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={query.isLoading}
        aria-label="Filter by recovery batch"
        className="h-10 min-w-52 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200"
      >
        <option value="">All batches</option>
        {batches.map((batch) => (
          <option key={batch.batch_id} value={batch.batch_id}>
            {batch.name}{batch.status === "active" ? " · Active" : " · Disabled"}
          </option>
        ))}
      </select>
    </div>
  )
}
