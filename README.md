# Revenue Recovery Agent

An event-driven AI revenue recovery platform that turns payment and receivables events into controlled, auditable recovery actions — and measures the revenue actually recovered.

**Detect → Understand → Decide → Guard → Execute → Observe → Correlate → Recover**

---

## What it does

Revenue recovery does not end when an AI model recommends an action. This project follows the complete loop from a real revenue event to a real provider action and, finally, a correlated payment outcome.

```text
Razorpay Revenue Event
        ↓
FastAPI Webhook Gateway
        ↓
Raw + Normalized Event
        ↓
Redis Stream
        ↓
Recovery Worker
        ↓
Recovery Context + Case
        ↓
Analyst Agent
        ↓
Strategist Agent
        ↓
Deterministic Guardrail
        ↓
Recovery Attempt
        ↓
Executor Agent
        ↓
Razorpay / Customer Communication
        ↓
Outcome Webhook
        ↓
Outcome Correlation
        ↓
Recovered Revenue
```

The platform currently models three revenue objects through a common recovery engine:

- **Payment**
- **Invoice**
- **Subscription**


---

## Core features

### Event-driven processing

- Razorpay webhook ingestion through FastAPI
- Raw webhook persistence
- Canonical event normalization
- Redis Streams + consumer groups for asynchronous processing
- PostgreSQL-backed recovery state
- Event idempotency and duplicate handling

### Multi-agent recovery

The AI layer has three separate responsibilities:

**Analyst Agent** — understands the failure/revenue risk, customer history, risk level, and recovery factors.

**Strategist Agent** — chooses an appropriate recovery action from the available capabilities.

**Executor Agent** — executes an already-approved action; it does not independently decide what should happen.

Supported recovery actions include:

```text
retry_payment
send_payment_link
send_reminder
contact_support
no_action
```

### Deterministic policy guardrails

AI decisions pass through deterministic validation before an executable recovery attempt is created. This protects action capabilities, channels, case state, attempt limits, and policy boundaries.

### Real Razorpay recovery

The live recovery path uses Razorpay Payment Links with supported customer channels:

- Email
- SMS

Recovery attempts carry stable lineage and provider metadata so subsequent payment events can be connected back to the recovery action.

### Razorpay Remote MCP

The project includes a dedicated Razorpay MCP capability boundary with approved tools:

```text
create_payment_link
payment_link_notify
fetch_all_payment_links
fetch_payment_link
fetch_payment
fetch_order
```

The Razorpay Remote MCP connection has been verified against Razorpay Test Mode.

---

# Recovery scenarios

## 1. Failed payment recovery

This is the primary live-tested recovery scenario.

```text
payment.failed
      ↓
Recovery Case
      ↓
Analyst
      ↓
Strategist
      ↓
Guardrail
      ↓
Recovery Attempt
      ↓
Razorpay Payment Link
      ↓
Email / SMS
      ↓
Customer Payment
      ↓
payment.captured
      ↓
Outcome Correlation
      ↓
Recovered Amount
```

The system distinguishes an AI decision, an approved attempt, execution, and the actual payment outcome.

---

## 2. Partial invoice recovery

A partially paid invoice with an outstanding balance becomes a recovery signal.

Example:

```text
Invoice total       ₹3,57,000
Payment 1           ₹1,00,000
Payment 2           ₹1,00,000
--------------------------------
Recovered           ₹2,00,000
Remaining           ₹1,57,000
```

The recovery case correctly remains open:

```text
At risk             ₹3,57,000
Recovered           ₹2,00,000
Remaining           ₹1,57,000
Status              Open
Progress            56%
```

The remaining balance is passed into the recovery pipeline, and the system can create a Payment Link/recovery reminder for the outstanding amount.

Partial-payment accounting is cumulative and idempotent, so repeated webhook deliveries do not double-count recovered revenue.

### Final invoice recovery

When the outstanding amount is subsequently paid:

```text
invoice.paid
      ↓
Recovery Case correlation
      ↓
Recovered = invoice total
Remaining = ₹0
      ↓
Case = Recovered
```

---

## 3. Subscription recovery

Subscription is a first-class revenue object throughout normalization, context building, case management, correlation, policy, and recovery processing.

The recovery engine handles subscription lifecycle signals such as:

```text
subscription.pending
subscription.halted
subscription.charged
```

Subscription recovery paths are covered by the automated end-to-end test suite and use the same recovery engine as payment and invoice recovery.

---

# Scheduled recovery

Recovery decisions can be scheduled for later execution.

```text
AI Decision
    ↓
Guardrail Approved
    ↓
RecoveryAttempt
    ↓
scheduled_at
    ↓
Recovery Scheduler
    ↓
Executor
    ↓
Razorpay
```

The scheduler executes due attempts through the same bounded Executor path. This separates the decisions of **what to do**, **when to do it**, and **how to execute it**.

---

# Recovery state machine

Recovery state is persisted rather than held only in agent memory.

Important recovery-attempt states include:

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

This supports reliable handling of retries, policy blocks, scheduled work, escalation, duplicate outcomes, and successful recovery.

---

# Outcome correlation

The system connects revenue outcomes to the recovery action that caused them.

Correlation uses recovery lineage and revenue identifiers including:

```text
recovery_attempt_id
recovery_case_id
payment_id
subscription_id
invoice_id
order_id
customer_id
```

Payment Link reference IDs also carry recovery lineage, for example:

```text
rr-attempt-883
```

This allows the platform to answer **which recovery action resulted in the payment**, rather than only recording that a payment occurred.

---

# Invoice accounting

Invoice recovery tracks the financial state explicitly:

```text
amount_at_risk
amount_recovered
amount_remaining
```

For partial payments, the recovered amount is cumulative and the remaining amount represents the outstanding receivable. A case stays open while money remains due and becomes recovered only when the outstanding amount reaches zero.

---

# Reliability

The platform includes:

- Webhook idempotency
- Redis consumer groups
- Pending-message reclamation
- Retryable execution failures
- Terminal execution exhaustion
- Deterministic stopping rules
- Deterministic escalation rules
- Guardrail rejection before attempt creation
- Duplicate successful-outcome protection
- Persistent recovery attempts and decisions
- Historical audit records

---

# Recovery batches

Recovery events and cases can be grouped into explicit batches.

A batch provides an operational boundary for:

- Events
- Recovery cases
- Recovery attempts
- AI decisions
- Escalations
- Revenue at risk
- Recovered revenue

Batch lifecycle:

```text
Create → Active → Close / Disable → Historical
```

The frontend provides batch-scoped operational views and drilldowns while preserving the underlying audit records.

---

# Merchant and developer portal

The React frontend provides two complementary views of the platform.

### Merchant

- Merchant Overview
- Recovery Cases
- Case Detail
- Escalations
- Recovery Batches
- Batch Detail

### Developer

- Developer Overview
- Event Explorer
- AI Decisions
- AI Decision Detail
- Execution Monitor
- System Health

### Case detail

A recovery case can be inspected through:

- At-risk revenue
- Recovered revenue
- Remaining revenue
- Recovery progress
- AI strategy
- Guardrail decision
- Execution result
- Recovery attempts
- Audit timeline

### Batch detail

Batch drilldown includes event and case exploration, normalized event data, recovery lineage, pagination/search, and batch-level recovery metrics.

---

# Architecture

```text
                         REVENUE SIGNALS
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
       payment.failed    subscription.*     invoice.*
              │                 │                 │
              └─────────────────┼─────────────────┘
                                │
                                ▼
                     FASTAPI WEBHOOK GATEWAY
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
                PostgreSQL              Redis Stream
             Raw + Normalized               │
                 Events                     ▼
                                      Recovery Worker
                                             │
                              ┌──────────────┴──────────────┐
                              ▼                             ▼
                       Context Builder                Case Manager
                              │                             │
                              └──────────────┬──────────────┘
                                             ▼
                                       Analyst Agent
                                             │
                                             ▼
                                      Strategist Agent
                                             │
                                             ▼
                                    Policy / Guardrail
                                             │
                                    ┌────────┴────────┐
                                    ▼                 ▼
                                 Blocked           Approved
                                                        │
                                                        ▼
                                                  Recovery Attempt
                                                        │
                                                        ▼
                                                 Executor Agent
                                                        │
                                      ┌─────────────────┴─────────────────┐
                                      ▼                                   ▼
                                Razorpay MCP                         Scheduler
                                      │                                   │
                                      └─────────────────┬─────────────────┘
                                                        ▼
                                               Customer Payment /
                                               Communication
                                                        │
                                                        ▼
                                                Outcome Webhook
                                                        │
                                                        ▼
                                               Correlation Engine
                                                        │
                                                        ▼
                                                 Recovery Case
                                                        │
                                      ┌─────────────────┴─────────────────┐
                                      ▼                                   ▼
                                  Recovered                       Open / Escalated
```

---

# Technology stack

| Layer | Technology |
|---|---|
| Backend | Python |
| API | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Queue | Redis Streams |
| AI Provider | Groq |
| Agent Framework | Strands |
| Payment Platform | Razorpay |
| External Tool Boundary | Razorpay Remote MCP |
| Frontend | React + TypeScript |
| Build Tool | Vite |
| Data Fetching | React Query |
| Charts | Recharts |
| UI | Tailwind CSS + Lucide |
| Infrastructure | Docker Compose |

---

# Project structure

```text
revenue-recovery-agent/
├── backend/
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── analyst_agent.py
│   │   │   ├── strategist_agent.py
│   │   │   └── executor_agent.py
│   │   ├── api/
│   │   ├── db/
│   │   ├── mcp/
│   │   ├── normalization/
│   │   ├── queue/
│   │   ├── state/
│   │   └── worker/
│   │       ├── recovery_worker.py
│   │       └── recovery_scheduler.py
│   ├── scripts/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/
│       ├── features/
│       ├── layouts/
│       └── types/
├── docker-compose.yml
└── README.md
```

---

# API surface

### Webhooks

```text
POST /webhooks/razorpay
```

### Recovery

```text
GET /recovery/metrics
GET /recovery/metrics/breakdowns
GET /recovery/cases
GET /recovery/cases/{case_id}/timeline
GET /recovery/cases/{case_id}/escalation
PATCH /recovery/cases/{case_id}/escalation/assignment
POST /recovery/cases/{case_id}/escalation/notes
POST /recovery/cases/{case_id}/escalation/resolve
GET /recovery/events
GET /recovery/events/{event_id}
```

### Batches

```text
GET /recovery/batches
POST /recovery/batches
GET /recovery/batches/{batch_id}
POST /recovery/batches/{batch_id}/close
POST /recovery/batches/{batch_id}/open
DELETE /recovery/batches/{batch_id}
```

---

# Testing and validation

The repository contains automated coverage for the major platform components and recovery paths, including:

- Event normalization
- Webhook idempotency
- Recovery case creation
- Recovery state machine
- Payment recovery
- Invoice recovery
- Invoice partial-payment recovery
- Subscription recovery
- Analyst Agent
- Analyst output validation
- Strategist Agent
- Deterministic guardrails
- Stopping rules
- Escalation rules
- Recovery scheduling
- Worker scheduling
- Redis retry and exhaustion behavior
- Executor behavior and retry handling
- Razorpay MCP
- Recovery APIs
- Audit history
- Metrics and metric breakdowns
- CORS

## Live-validated scenarios

The current implementation has been exercised against a real Razorpay **Test Mode** account for:

### Payment recovery

```text
payment.failed
→ Analyst
→ Strategist
→ Guardrail approval
→ Razorpay Payment Link
→ Email/SMS
→ Customer payment
→ Successful recovery
```

### Scheduled recovery

```text
Recovery decision
→ scheduled RecoveryAttempt
→ Recovery Scheduler
→ Razorpay MCP
→ customer SMS / payment link
```

### Invoice partial-payment recovery

```text
Invoice
→ partial payment
→ invoice.partially_paid
→ RecoveryCase
→ cumulative recovered amount
→ remaining balance
→ AI recovery strategy
→ guardrail
→ Razorpay Payment Link
```

### Invoice final recovery

```text
Partial invoice recovery
→ remaining amount paid
→ invoice.paid
→ outcome correlation
→ full recovered amount
→ RecoveryCase = recovered
```

### Razorpay MCP

The Razorpay Remote MCP connection has been verified and the approved capabilities are discoverable from the project.

---

# Local development

## Prerequisites

- Docker / Docker Compose
- Python / Conda environment
- Node.js and npm
- Razorpay Test Mode credentials
- Groq API key

## 1. Clone

```powershell
git clone https://github.com/Nischay-EXE/revenue-recovery-agent.git
cd revenue-recovery-agent
```

## 2. Start infrastructure

```powershell
docker compose up -d
```

## 3. Configure backend

```powershell
cd backend
copy .env.example .env
```

Configure the required environment variables in `.env`.

## 4. Start FastAPI

```powershell
conda activate revenue-recovery
uvicorn app.main:app --reload
```

## 5. Start the Recovery Worker

In another terminal:

```powershell
cd backend
conda activate revenue-recovery
python -m app.worker.recovery_worker
```

## 6. Start the Recovery Scheduler

In another terminal:

```powershell
cd backend
conda activate revenue-recovery
python -m app.worker.recovery_scheduler
```

## 7. Start the frontend

```powershell
cd frontend
npm install
npm run dev
```

---

# Environment configuration

Use `backend/.env.example` as the configuration template.

Typical configuration includes:

```text
DATABASE_URL
GROQ_API_KEY
RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET
RAZORPAY_WEBHOOK_SECRET
RAZORPAY_MCP_URL
REDIS_URL
```

Keep `.env` local. API keys, webhook secrets, and other credentials must never be committed to the repository.

---


# Design principles

### AI proposes; deterministic systems control

LLMs handle reasoning-intensive analysis and strategy. Policy, capabilities, state transitions, and execution boundaries remain deterministic.

### Execution is bounded

Agents execute only through registered capabilities that have passed policy validation.

### Revenue outcomes are first-class

A generated decision or sent payment link is not counted as recovered revenue until the corresponding outcome is observed and correlated.

### Recovery is persistent

Cases, decisions, attempts, executions, outcomes, and financial amounts are persisted in PostgreSQL.

### Auditability by default

The system preserves the journey from event to decision to execution to outcome.

### One engine, multiple revenue objects

Payment, subscription, and invoice recovery reuse the same event, context, case, policy, execution, scheduling, correlation, and outcome architecture.

---

# Product direction

The current implementation establishes the core revenue recovery engine. The architecture is designed to expand the same engine with additional recovery capabilities and revenue workflows rather than creating isolated systems.

The central product metric is:

> **How much revenue was actually recovered?**

---

# Repository

GitHub: https://github.com/Nischay-EXE/revenue-recovery-agent
