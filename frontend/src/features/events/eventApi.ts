import { apiGet } from "../../lib/api"
import type { RecoveryEventsResponse } from "../../types/recovery"

export type EventExplorerParams = {
  search?: string
  eventType?: string
  revenueObjectType?: string
  batchId?: string
  limit?: number
  offset?: number
}

export async function getRecoveryEvents(
  params: EventExplorerParams = {},
): Promise<RecoveryEventsResponse> {
  const searchParams = new URLSearchParams()

  if (params.search) {
    searchParams.set("search", params.search)
  }

  if (params.eventType) {
    searchParams.set("event_type", params.eventType)
  }

  if (params.revenueObjectType) {
    searchParams.set(
      "revenue_object_type",
      params.revenueObjectType,
    )
  }

  if (params.batchId) {
    searchParams.set("batch_id", params.batchId)
  }

  searchParams.set(
    "limit",
    String(params.limit ?? 25),
  )

  searchParams.set(
    "offset",
    String(params.offset ?? 0),
  )

  return apiGet<RecoveryEventsResponse>(
    `/recovery/events?${searchParams.toString()}`,
  )
}
