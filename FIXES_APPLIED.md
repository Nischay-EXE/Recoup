# Revenue Recovery Agent — Fixes Applied

## Fixed

1. Analyst output parsing
   - Extracts the final assistant text from the Strands `AgentResult.message`
     instead of relying only on `str(result)`.
   - Keeps the provider-facing tolerant wire format while normalizing
     `recovery_factors` and `considerations` into real `list[str]` values.
   - Improved the retry log so it reports parsing/validation failure rather
     than incorrectly claiming every failure is invalid JSON.

2. Razorpay Payment Link notification validation
   - `payment_link_notify` responses are now validated before the recovery
     attempt is marked `sent`.
   - Explicit provider failures (`success=false`, failed/error/rejected
     statuses) now fail the execution instead of being recorded as sent.
   - The official `{"success": true}` response and the MCP `status=notified`
     response are accepted.

3. Permanent execution state handling
   - A provider/configuration `blocked` result is now returned to the state
     layer as `blocked` instead of being converted into retryable
     `execution_failed`.

4. Tests
   - Added Analyst AgentResult parsing coverage.
   - Added notification success/failure validation coverage.
   - Added blocked execution-state coverage.

## Verification

- Python backend compilation passes with `compileall`.
- Full runtime pytest could not be executed in this isolated environment
  because the uploaded environment does not contain the `strands` and
  `psycopg` runtime packages and network installation is unavailable.

## Important implementation observation

The current recovery scheduler is a PostgreSQL polling scheduler. It uses
`RecoveryAttempt.scheduled_at` and polls the database every 30 seconds. Redis
is used by the webhook/recovery-worker stream, but the scheduler itself is
not Redis-backed. Demo narration should therefore call it the
"recovery scheduler" unless the implementation is intentionally changed.

## Razorpay SMS observation

The old Payment Link was not receiving SMS/email even when triggered from the
Razorpay Dashboard, while a newly created link did receive notification.
That points to a Payment-Link/provider-side issue rather than the scheduler.
Razorpay also documents per-link/per-medium notification rate limits.

The code now surfaces the provider notification result instead of blindly
marking every successful MCP envelope as `sent`.
