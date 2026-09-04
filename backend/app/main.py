from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db import history_models
from app.api.webhooks import router as webhook_router
from app.api.recovery import router as recovery_router
from app.api.batches import router as batch_router
from app.db import models  # noqa: F401
from app.db import recovery_models
from app.db import normalized_models  # noqa: F401
from app.db import batch_models  # noqa: F401

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database schema is managed exclusively by Alembic migrations.
    yield


app = FastAPI(
    title="Revenue Recovery Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)
app.include_router(recovery_router)
app.include_router(batch_router)

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}