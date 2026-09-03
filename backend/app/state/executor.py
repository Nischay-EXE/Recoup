from app.utils.time import utc_now
from datetime import datetime

from sqlalchemy.orm import Session

from app.agent.executor_agent import (
    ExecutionResult,
    SUPPORTED_REAL_PAYMENT_LINK_CHANNELS,
    execute_strategy,
)
from app.db.recovery_models import (
    RecoveryAttempt,
    RecoveryDecisionRecord,
)
from app.state.context_service import build_recovery_context

SUPPORTED_ACTIONS = {
    "retry_payment",
    "send_payment_link",
    "send_reminder",
    "contact_support",
    "no_action",
}

SUPPORTED_CHANNELS = {
    "whatsapp",
    "email",
    "sms",
    "none",
}

TERMINAL_STATUSES = {
    "succeeded",
    "failed",
    "stopped",
    "escalated",
    "blocked",
    "execution_exhausted",
}


def _get_persisted_decision(
    attempt: RecoveryAttempt,
    db: Session,
) -> RecoveryDecisionRecord:
    decision = (
        db.query(RecoveryDecisionRecord)
        .filter(
            RecoveryDecisionRecord.event_id == attempt.event_id
        )
        .first()
    )

    if decision is None:
        raise ValueError(
            "Approved recovery decision not found for "
            f"event_id={attempt.event_id}"
        )

    return decision


def _apply_result(
    attempt: RecoveryAttempt,
    result: ExecutionResult,
    db: Session,
) -> RecoveryAttempt:
    now = utc_now()

    attempt.status = result.status
    attempt.execution_provider = result.provider
    attempt.external_execution_id = result.external_id
    attempt.external_execution_url = result.external_url
    attempt.execution_error = result.error

    # `executed_at` means an execution actually happened. Do not set it for
    # blocked or failed attempts.
    if result.status in {
        "sent",
        "escalated",
        "stopped",
        "succeeded",
    }:
        attempt.executed_at = now
    else:
        attempt.executed_at = None

    if result.status in {
        "stopped",
        "escalated",
        "blocked",
        "succeeded",
        "failed",
        "execution_failed",
    }:
        attempt.resolved_at = now
    else:
        attempt.resolved_at = None

    db.commit()
    db.refresh(attempt)

    return attempt


def execute_recovery_attempt(
    attempt: RecoveryAttempt,
    db: Session,
) -> RecoveryAttempt:
    """
    Execute one guardrail-approved recovery attempt.

    Lifecycle:
        proposed -> approved -> sent/escalated/stopped
                   approved -> execution_failed (retryable)
                   approved -> blocked (terminal)

    Retryable execution failures are persisted as `execution_failed` and
    propagated so the Redis worker can redeliver the same attempt.
    Permanent capability/configuration blocks are persisted as `blocked`
    and returned without poisoning the Redis stream.
    """

    if attempt.action not in SUPPORTED_ACTIONS:
        raise ValueError(
            f"Unsupported recovery action: {attempt.action}"
        )

    if attempt.channel not in SUPPORTED_CHANNELS:
        raise ValueError(
            f"Unsupported recovery channel: {attempt.channel}"
        )

    # --------------------------------------------------
    # 1. Idempotent terminal checks
    # --------------------------------------------------

    if attempt.status in TERMINAL_STATUSES:
        print(
            f"[EXECUTOR] Attempt already terminal "
            f"attempt_id={attempt.id} "
            f"status={attempt.status}"
        )
        return attempt

    if attempt.status == "sent":
        print(
            f"[EXECUTOR] Attempt already executed "
            f"attempt_id={attempt.id}"
        )
        return attempt

    if attempt.status not in {
        "proposed",
        "approved",
        "execution_failed",
    }:
        raise ValueError(
            f"Attempt is not executable: "
            f"attempt_id={attempt.id} "
            f"status={attempt.status}"
        )

    # --------------------------------------------------
    # 2. Load the exact persisted Strategist decision
    # --------------------------------------------------

    decision = _get_persisted_decision(
        attempt=attempt,
        db=db,
    )

    if (
        decision.action != attempt.action
        or decision.channel != attempt.channel
    ):
        raise ValueError(
            "Recovery attempt does not match its persisted decision. "
            f"attempt_id={attempt.id}"
        )

    # --------------------------------------------------
    # 3. Reject known unsupported real execution capabilities early.
    # --------------------------------------------------
    # This is a capability/configuration block, not a transient provider
    # failure. Do not send the Redis message into a retry loop for something
    # that cannot succeed until the provider is implemented/configured.
    if (
        attempt.action in {
            "send_payment_link",
            "retry_payment",
            "send_reminder",
        }
        and attempt.channel not in SUPPORTED_REAL_PAYMENT_LINK_CHANNELS
    ):
        result = ExecutionResult(
            success=False,
            status="blocked",
            action=attempt.action,
            channel=attempt.channel,
            provider="executor_capability",
            message=(
                "Execution blocked because the current real provider "
                "does not support the approved action/channel combination."
            ),
            error=(
                "Real Payment Link execution currently supports "
                "email and sms only. "
                f"Received channel={attempt.channel}."
            ),
        )

        attempt = _apply_result(
            attempt=attempt,
            result=result,
            db=db,
        )

        print(
            f"[EXECUTOR] Execution blocked "
            f"attempt_id={attempt.id} "
            f"action={attempt.action} "
            f"channel={attempt.channel} "
            f"reason={result.error}"
        )

        return attempt

    # --------------------------------------------------
    # 4. Build verified context
    # --------------------------------------------------

    context = build_recovery_context(
        event_id=attempt.event_id,
        db=db,
    )

    # --------------------------------------------------
    # 5. Proposed/retry -> approved BEFORE external execution
    # --------------------------------------------------

    if attempt.status in {"proposed", "execution_failed"}:
        attempt.status = "approved"
        attempt.resolved_at = None
        db.commit()
        db.refresh(attempt)

    if attempt.action == "no_action":
        attempt.status = "stopped"
        attempt.executed_at = utc_now()

        db.commit()
        db.refresh(attempt)

        print(
            f"[EXECUTOR] No action required "
            f"attempt_id={attempt.id}"
        )

        return attempt
    # --------------------------------------------------
    # 6. Execute through the Groq-backed Executor Agent
    # --------------------------------------------------

    try:
        result = execute_strategy(
            context=context,
            decision=decision,
            attempt=attempt,
            db=db,
        )

    except Exception as exc:
        error = str(exc)

        # Important invariant:
        # External execution failure != customer payment failure.
        # Persist the failure explicitly while leaving the attempt retryable.
        attempt.status = "execution_failed"
        attempt.resolved_at = None
        attempt.execution_provider = "executor_agent"
        attempt.execution_error = error

        db.commit()
        db.refresh(attempt)

        print(
            f"[EXECUTOR] Execution failed "
            f"attempt_id={attempt.id} "
            f"error={error} "
            f"status={attempt.status}"
        )

        raise

    # --------------------------------------------------
    # 7. Persist real execution result
    # --------------------------------------------------

    attempt = _apply_result(
        attempt=attempt,
        result=result,
        db=db,
    )

    print(
        f"[EXECUTOR] Execution complete "
        f"attempt_id={attempt.id} "
        f"status={attempt.status} "
        f"provider={result.provider} "
        f"external_id={result.external_id} "
        f"external_url={result.external_url}"
    )

    return attempt

