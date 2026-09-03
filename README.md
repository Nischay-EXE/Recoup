# revenue-recovery-agent
=======
# Executor state handling update

Replace these files in the current project:

- backend/app/state/executor.py
- backend/app/worker/recovery_worker.py
- backend/app/state/attempts.py
- backend/app/state/outcomes.py

What changed:

1. Retryable Executor failures are persisted as `execution_failed` and can be retried using the same RecoveryAttempt.
2. After MAX_MESSAGE_RETRIES, the worker changes the attempt to terminal `execution_exhausted` before ACKing the Redis message.
3. Known unsupported payment-link channels are persisted as terminal `blocked` instead of entering a Redis retry loop.
4. Guardrail rejections are persisted as `blocked` with `policy_result=rejected` and `policy_reason` before the Redis message is ACKed.
5. Approved `no_action` decisions now go through the Executor state path and become `stopped` instead of remaining proposed/approved.
6. `executed_at` is not set for blocked/failed execution states.

No database migration is required because `status` and the existing execution metadata are string fields already present in `recovery_attempts`.
>>>>>>> b93d4c5 (Initial revenue recovery agent)
