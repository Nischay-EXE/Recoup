# Revenue Recovery Frontend

React + TypeScript frontend for the Revenue Recovery Engine.

## Local development

From `frontend/`:

```powershell
npm install
npm run dev
```

The frontend expects the FastAPI backend at `http://localhost:8000` by default.
Set `VITE_API_BASE_URL` if the backend runs elsewhere.

## Validation

```powershell
npm run build
npm run lint
```

## Main views

- Merchant Overview
- Recovery Cases
- Case Detail / Audit Timeline
- Escalations
- Recovery Batches
- Batch Event Drill-down
- Developer Overview
- Event Explorer
- AI Decisions / Decision Trace
- Execution Monitor
- System Health
