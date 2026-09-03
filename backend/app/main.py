from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import history_models
from app.api.webhooks import router as webhook_router
from app.db import models  # noqa: F401
from app.db import recovery_models
from app.db import normalized_models  # noqa: F401
from app.db.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Revenue Recovery Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(webhook_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}