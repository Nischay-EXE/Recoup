# Revenue Recovery Agent

An event-driven AI system for detecting failed revenue events, understanding why they happened, deciding how to recover them, executing bounded recovery actions, and measuring the outcome.

The project is built around a closed-loop recovery pipeline:

**Detect → Understand → Decide → Guard → Execute → Observe → Correlate → Recover**

---

## What the system does

When a Razorpay payment fails, the system can automatically:

1. Receive the Razorpay webhook through FastAPI.
2. Persist the raw event and normalize it into a canonical event model.
3. Publish the event to a Redis Stream.
4. Build customer/payment recovery context.
5. Associate the event with a `RecoveryCase`.
6. Run an **Analyst Agent** to understand the failure.
7. Run a **Strategist Agent** to propose a recovery action.
8. Validate the proposed action using deterministic policy and capability guardrails.
9. Create a persisted `RecoveryAttempt` for an approved executable action.
10. Run the **Executor Agent** to perform the approved action.
11. Create/use a Razorpay Payment Link for real recovery through supported channels.
12. Receive the resulting Razorpay payment/outcome webhook.
13. Correlate the outcome with the original recovery attempt.
14. Mark the recovery successful and record the recovered amount.

The important distinction is that the system does not stop at:

> "AI decided to send a message."

It follows the recovery through to the actual revenue outcome.

---

# Architecture

```text
                    REVENUE SIGNALS
                           │
          ┌────────────────┼────────────────┐
          │                │                │
   payment.failed   subscription.*    invoice.*
          │                │                │
          └────────────────┼────────────────┘
                           │
                           ▼
                  FASTAPI WEBHOOK GATEWAY
                           │
                           ▼
                       POSTGRESQL
                 Raw + Normalized Events
                           │
                           ▼
                     REDIS STREAM
                           │
                           ▼
                   RECOVERY WORKER
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
          Context Builder       Case Manager
                 │                   │
                 └─────────┬─────────┘
                           ▼
                     ANALYST AGENT
                           │
                           ▼
                   STRATEGIST AGENT
                           │
                           ▼
                POLICY / GUARDRAIL
                           │
                    ┌──────┴──────┐
                    │             │
                 rejected       approved
                    │             │
                    ▼             ▼
                 BLOCKED    RECOVERY ATTEMPT
                                  │
                                  ▼
                           EXECUTOR AGENT
                                  │
                         ┌────────┴────────┐
                         ▼                 ▼
                    RAZORPAY          COMMUNICATION
                       API             Email / SMS
                         │                 │
                         └────────┬────────┘
                                  ▼
                           OUTCOME WEBHOOK
                                  │
                                  ▼
                         CORRELATION ENGINE
                                  │
                                  ▼
                           RECOVERY CASE
                         ┌────────┴────────┐
                         ▼                 ▼
                     RECOVERED         UNRESOLVED
```

---

# Multi-Agent Architecture

The AI layer intentionally separates analysis, strategy, and execution.

## 1. Analyst Agent

The Analyst examines the revenue event and available context.

Its job is to answer questions such as:

- What happened?
- Why did the payment/revenue event fail?
- What customer/payment context is relevant?
- Is this situation potentially recoverable?
- What information should influence the recovery strategy?

The Analyst produces structured output rather than directly executing an action.

---

## 2. Strategist Agent

The Strategist receives the Analyst's structured assessment and determines the most appropriate recovery strategy.

It considers the execution capabilities currently registered by the system.

Possible actions include:

```text
retry_payment
send_payment_link
send_reminder
contact_support
no_action
```

The Strategist proposes an action.

It does **not** get unrestricted authority to execute that action.

---

## 3. Policy / Guardrail

Before an action becomes a real recovery attempt, it passes through deterministic policy validation.

The guardrail verifies things such as:

- Is the action supported?
- Is the requested channel supported for that action?
- Is the action allowed by the current policy?
- Has the recovery case reached its attempt limit?
- Is the underlying payment/revenue state appropriate?
- Would the action create an invalid or duplicate recovery attempt?

For example:

```text
send_payment_link + email
        ↓
      allowed

send_payment_link + sms
        ↓
      allowed

send_payment_link + whatsapp
        ↓
      blocked
```

This prevents the LLM from bypassing execution boundaries.

---

## 4. Executor Agent

The Executor is a real **Groq + Strands Agent**.

Its responsibility is execution of an already-approved action.

The Executor does not independently decide which recovery action should happen.

Instead:

```text
Analyst
   ↓
Strategist
   ↓
Guardrail
   ↓
Approved Action
   ↓
Executor
   ↓
Real Provider Action
```

This separation keeps the AI flexible while keeping execution bounded.

---

# Current Recovery Capabilities

The current action registry contains:

```text
retry_payment
send_payment_link
send_reminder
contact_support
no_action
```

Current real Payment Link delivery channels are:

```text
email
sms
```

WhatsApp is **not** currently treated as an implemented Payment Link execution capability.

Unsupported combinations are rejected by the deterministic capability/guardrail layer before an executable recovery attempt is created.

---

# Real Razorpay Recovery

The currently demonstrated recovery flow uses Razorpay Payment Links.

A recovery attempt receives a stable reference:

```text
rr-attempt-{attempt_id}
```

The Payment Link also stores recovery lineage metadata such as:

```text
recovery_attempt_id
recovery_case_id
event_id
```

This allows a later successful payment to be correlated with the recovery action that caused it.

Example:

```text
Payment failed
      │
      ▼
RecoveryAttempt #68
      │
      ▼
Payment Link created
      │
      ▼
Customer pays ₹1300
      │
      ▼
Razorpay payment.captured
      │
      ▼
Correlation
      │
      ▼
RecoveryAttempt #68 = succeeded
      │
      ▼
₹1300 recovered
```

---

# Recovery State Machine

Recovery is represented as persistent state rather than a transient LLM response.

Important states include:

```text
proposed
approved
sent
succeeded
failed
execution_failed
execution_exhausted
blocked
stopped
```

The system distinguishes between:

- a decision being proposed,
- an action being approved,
- an action actually being executed,
- an execution failure,
- a policy block,
- a stopped/no-action decision,
- and a successful revenue outcome.

This prevents "attempted recovery" from being incorrectly counted as "successful recovery."

---

# Reliability and Idempotency

The worker uses Redis Streams and consumer groups for asynchronous processing.

The implementation handles:

### Duplicate events

Duplicate webhook events are detected and safely handled.

### Retryable execution failures

A transient Executor failure can become:

```text
execution_failed
```

and the same `RecoveryAttempt` can be retried.

### Execution exhaustion

After the configured Redis message retry limit:

```text
execution_failed
        ↓
execution_exhausted
```

The message can then be acknowledged without endlessly retrying.

### Unsupported capabilities

Known unsupported execution paths become terminal:

```text
blocked
```

rather than entering a retry loop.

### Guardrail rejection

A policy rejection is persisted as a blocked recovery decision.

Importantly, a guardrail rejection does **not** consume recovery-attempt capacity.

### Duplicate successful outcomes

Once an attempt has transitioned to:

```text
succeeded
```

a duplicate payment outcome does not transition it again.

---

# Outcome Correlation

A key part of the system is connecting a successful revenue event back to the recovery action.

Correlation priority includes:

```text
1. recovery_attempt_id
2. recovery_case_id
3. payment_id
4. order_id
5. customer_id
```

For Payment Links, the recovery attempt can also be recovered from the Payment Link reference:

```text
rr-attempt-68
```

This allows the system to answer:

> Which recovery action actually resulted in this payment?

rather than simply recording that a payment happened.

---

# Data Model

The system separates event history, customer/payment history, and recovery state.

Conceptually:

```text
Revenue Event
     │
     ├── Customer
     ├── Order
     └── Payment
            │
            ▼
      Recovery Case
            │
            ├── Decision
            │
            └── Recovery Attempts
                    │
                    ▼
                 Outcome
                    │
                    ▼
             Amount Recovered
```

Historical records are preserved for auditability.

---

# Technology Stack

| Component | Technology |
|---|---|
| Language | Python |
| API | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Queue | Redis Streams |
| Payment Platform | Razorpay |
| LLM Provider | Groq |
| Agent Framework | Strands |
| Infrastructure | Docker Compose |
| Database Migrations | Alembic |

---

# Project Structure

```text
revenue-recovery-agent/
├── backend/
│   ├── alembic/
│   ├── app/
│   │   ├── agent/
│   │   ├── api/
│   │   ├── clients/
│   │   ├── db/
│   │   ├── normalization/
│   │   ├── queue/
│   │   ├── state/
│   │   └── worker/
│   ├── tests/
│   └── requirements.txt
├── docker-compose.yml
└── README.md
```

---

# Running Locally

## 1. Start infrastructure

```powershell
docker compose up -d
```

The project uses PostgreSQL and Redis.

## 2. Configure environment

From the backend directory:

```powershell
cd backend
copy .env.example .env
```

Configure the required credentials and settings inside `.env`.

Do not commit `.env` or API credentials.

## 3. Start FastAPI

```powershell
uvicorn app.main:app --reload --port 8000
```

## 4. Start the Recovery Worker

Open another terminal:

```powershell
cd backend
python -m app.worker.recovery_worker
```

## 5. Run tests

From `backend`:

```powershell
pytest -q
```

---

# Webhook Flow

The Razorpay webhook enters through:

```text
POST /webhooks/razorpay
```

The webhook layer:

1. Validates the Razorpay signature.
2. Checks for duplicate events.
3. Stores the raw event.
4. Normalizes the event.
5. Synchronizes relevant history.
6. Stores the normalized event.
7. Commits the database transaction.
8. Publishes the event to Redis.

The worker then processes the event asynchronously.

---

# Supported Payment Event Flow

The currently strongest end-to-end scenario is:

```text
Razorpay
   │
   │ payment.failed
   ▼
FastAPI
   │
   ▼
PostgreSQL
   │
   ▼
Redis Stream
   │
   ▼
Recovery Worker
   │
   ▼
Recovery Context
   │
   ▼
Analyst Agent
   │
   ▼
Strategist Agent
   │
   ▼
Policy Guardrail
   │
   ▼
RecoveryAttempt
   │
   ▼
Executor Agent
   │
   ▼
Razorpay Payment Link
   │
   ▼
Email / SMS
   │
   ▼
Customer Payment
   │
   ▼
Razorpay payment.captured
   │
   ▼
Outcome Correlation
   │
   ▼
RecoveryAttempt = succeeded
   │
   ▼
Amount Recovered
```

---

# Product Direction

The recovery engine is being generalized around three revenue objects:

```text
Payment
Subscription
Invoice
```

The goal is to use the same underlying recovery engine rather than building three unrelated systems.

## Scenario 1 — Payment Degradation → Recovery

**Current hero scenario.**

```text
payment.failed
      ↓
failure analysis
      ↓
recovery strategy
      ↓
guardrail
      ↓
Payment Link / recovery action
      ↓
customer pays
      ↓
recovered amount
```

## Scenario 2 — Failed Subscription Recovery

The next major scenario is subscription recovery.

The architecture will use subscription lifecycle events to identify situations such as failed recurring charges and subscriptions entering pending/halted states.

```text
Subscription Event
       ↓
Context
       ↓
Analysis
       ↓
Strategy
       ↓
Guardrail
       ↓
Recovery Action
       ↓
Outcome
```

Subscription recovery is a target product scenario and should not be interpreted as fully implemented merely because it appears in the architecture.

## Scenario 3 — Invoice / B2B Receivables Recovery

The third core scenario is invoice and B2B receivables recovery.

The engine can eventually handle:

```text
Invoice issued
      ↓
Invoice overdue / partially paid
      ↓
Receivables context
      ↓
Recovery strategy
      ↓
Reminder / payment link / escalation
      ↓
Payment
      ↓
Recovered amount
```

Promise-to-pay is intended to be a capability inside this receivables workflow rather than a separate recovery engine.

---

# Planned Extensions

The architecture is designed to evolve toward:

- Generalized Payment / Subscription / Invoice events
- Subscription recovery
- Invoice / B2B receivables recovery
- Promise-to-pay workflows
- Scheduled and delayed recovery actions
- Explicit stopping rules
- Escalation workflows
- Batch recovery metrics
- Audit timelines
- Broader MCP capability integration
- Product frontend and recovery dashboards

These features should be considered **planned unless supported by the current implementation**.

---

# MCP Direction

MCP is intended to provide a clean capability boundary around external tools and services.

The architecture should not duplicate existing Razorpay functionality unnecessarily.

The intended direction is:

```text
Recovery Engine
      │
      ▼
Capability Boundary
      │
 ┌────┴─────────────┐
 ▼                  ▼
Razorpay MCP     Recovery Tools
supported        subscription/
operations       invoice/case/
                 policy/scheduling
```

The MCP layer is an extension point, not a replacement for the current recovery services.

---

# Design Principles

## 1. AI proposes; deterministic systems constrain

LLMs handle reasoning-intensive tasks such as analysis and strategy.

Deterministic code controls what can actually happen.

## 2. Execution is bounded

An approved strategy must correspond to a registered execution capability.

The Executor cannot arbitrarily invent an unsupported tool or channel.

## 3. Recovery is a state machine

A recovery action has a persistent lifecycle.

This makes retries, failures, stopping, and successful outcomes explicit.

## 4. Outcomes matter

Sending a payment link is not the same as recovering revenue.

The system therefore tracks:

```text
Action
  ↓
Execution
  ↓
Payment Outcome
  ↓
Amount Recovered
```

## 5. Auditability matters

The system preserves the recovery journey:

```text
Event
  ↓
Context
  ↓
Analysis
  ↓
Strategy
  ↓
Guardrail
  ↓
Attempt
  ↓
Execution
  ↓
Outcome
  ↓
Recovered Amount
```

This allows an individual recovery case to be inspected end-to-end.

---

# Demo Goal

The eventual batch-level product demonstration should answer:

```text
100 revenue-risk cases

₹X total revenue at risk

₹Y actually recovered

Recovery rate: XX%

Automatically recovered: XX
Escalated: XX
Stopped by policy: XX
Still outstanding: XX
```

An individual case should be drillable:

```text
Recovery Case
     ↓
Revenue Event
     ↓
Customer / Payment Context
     ↓
Analyst
     ↓
Strategist
     ↓
Capabilities
     ↓
Guardrail
     ↓
Recovery Attempt
     ↓
Executor
     ↓
Razorpay
     ↓
Outcome
     ↓
Amount Recovered
     ↓
Final Case State
```

The key product metric is therefore not simply:

> "How many AI decisions were generated?"

It is:

> **How much revenue was actually recovered?**

---

# Repository

GitHub:

https://github.com/Nischay-EXE/revenue-recovery-agent
