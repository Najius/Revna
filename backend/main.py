"""Revna — FastAPI application entry point."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import health, users, webhooks
from backend.database import engine
from backend.services.scheduler import setup_scheduler

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    logger.info("revna.startup", version="0.1.0")
    sched = setup_scheduler()
    sched.start()
    logger.info("revna.scheduler_started", jobs=len(sched.get_jobs()))
    yield
    sched.shutdown(wait=False)
    await engine.dispose()
    logger.info("revna.shutdown")


app = FastAPI(
    title="Revna",
    description="AI health coach that texts you at the right moment.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ───────────────────────────────────────────────
app.include_router(health.router)
app.include_router(webhooks.router, prefix="/webhooks")
app.include_router(users.router, prefix="/api/users")
