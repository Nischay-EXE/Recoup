export type RecoveryMetrics = {
  total_cases: number
  recovered_cases: number
  escalated_cases: number
  unresolved_cases: number
  amount_at_risk: number
  amount_recovered: number
  total_attempts: number
  recovery_rate: number
}

export type RecoveryBreakdownItem = {
  attempts: number
  recovered_attempts: number
  amount_recovered: number
}

export type RecoveryBreakdowns = {
  by_revenue_object: Record<string, RecoveryBreakdownItem>
  by_action: Record<string, RecoveryBreakdownItem>
  by_channel: Record<string, RecoveryBreakdownItem>
}

export type RecoveryCase = {
  batch_id: string | null
  case_id: string
  customer_id: string | null
  order_id: string | null
  revenue_object_type: string
  subscription_id: string | null
  invoice_id: string | null
  original_payment_id: string | null
  current_payment_id: string | null
  amount_at_risk: number
  amount_recovered: number
  amount_remaining: number
  status: string
  current_attempt: number
  created_at: string
  resolved_at: string | null
}

export type RecoveryCasesResponse = {
  items: RecoveryCase[]
  total: number
  limit: number
  offset: number
}
export type RecoveryTimelineEvent = {
  timestamp: string
  event_type: string
  description: string
  details: Record<string, string | number | boolean | null>
}

export type RecoveryCaseTimeline = {
  case_id: string
  customer_id: string | null
  revenue_object_type: string
  amount_at_risk: number
  amount_recovered: number
  status: string
  timeline: RecoveryTimelineEvent[]
}
export type RecoveryEventNormalized = {
  event_id: string
  customer_id: string | null
  payment_id: string | null
  order_id: string | null
  subscription_id: string | null
  invoice_id: string | null
  amount: number | null
  amount_paid: number | null
  amount_due: number | null
  currency: string | null
  status: string | null
  occurred_at: string | null
  received_at: string | null
}

export type RecoveryEvent = {
  event_id: string
  batch_id: string | null
  source: string
  event_type: string
  received_at: string
  payload_available: boolean
  normalized: RecoveryEventNormalized | null
  recovery_case: {
    case_id: string
    status: string
    revenue_object_type: string
    amount_at_risk: number | null
    amount_recovered: number | null
    current_attempt: number
  } | null
  recovery_case_match: "exact" | "ambiguous" | "none"
}

export type RecoveryEventsResponse = {
  items: RecoveryEvent[]
  total: number
  limit: number
  offset: number
}