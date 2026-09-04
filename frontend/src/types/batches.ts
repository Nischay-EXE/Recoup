export type RecoveryBatch = {
  batch_id: string
  name: string
  description: string | null
  status: "active" | "completed" | string
  started_at: string
  ended_at: string | null
  created_at: string
  event_count: number
  normalized_event_count: number
  payment_count: number
  case_count: number
  attempt_count: number
  escalated_count: number
  amount_at_risk: number
  amount_recovered: number
  recovery_rate: number
}

export type RecoveryBatchesResponse = {
  items: RecoveryBatch[]
  total: number
  limit: number
  offset: number
  active_batch_id: string | null
}
