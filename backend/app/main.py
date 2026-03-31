import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database import get_db, async_session_factory
from app.models import Screenshot
from app.routers import screenshots, alerts, journals
from app.schemas import HealthResponse, ReadyResponse
from app.services.analysis_worker import (
    analysis_loop,
    run_daily_journal_job,
    JOURNAL_PROMPT,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = Settings()


async def cleanup_old_screenshots() -> int:
    """Delete screenshots older than 30 days. Returns count of deleted records."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    async with async_session_factory() as db:
        result = await db.execute(
            select(Screenshot.file_path, Screenshot.thumb_path)
            .where(Screenshot.captured_at < cutoff)
        )
        rows = result.all()

        if not rows:
            return 0

        from pathlib import Path
        for row in rows:
            for path in [row.file_path, row.thumb_path]:
                if path:
                    full = Path(settings.screenshot_dir) / path
                    try:
                        full.unlink(missing_ok=True)
                    except Exception as e:
                        logger.warning(f"Failed to delete file {full}: {e}")

        await db.execute(
            delete(Screenshot).where(Screenshot.captured_at < cutoff)
        )
        await db.commit()

        logger.info(f"Cleanup: deleted {len(rows)} screenshot records older than {cutoff}")
        return len(rows)


async def cleanup_loop() -> None:
    """Run cleanup every 24 hours."""
    while True:
        await asyncio.sleep(86400)
        try:
            count = await cleanup_old_screenshots()
            logger.info(f"Scheduled cleanup completed: {count} old screenshots removed")
        except Exception as e:
            logger.error(f"Cleanup job failed: {e}")


def calculate_seconds_until(target_hour: int, target_minute: int) -> float:
    """Calculate seconds until the next occurrence of target_hour:target_minute UTC."""
    now = datetime.now(timezone.utc)
    target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


async def journal_cron_loop() -> None:
    """Run daily journal generation at 23:59 UTC each day."""
    while True:
        seconds = calculate_seconds_until(23, 59)
        logger.info(f"Journal cron: next run in {seconds:.0f} seconds")
        await asyncio.sleep(seconds)
        try:
            await run_daily_journal_job(settings)
            logger.info("Daily journal cron completed")
        except Exception as e:
            logger.error(f"Daily journal cron failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: run initial cleanup + start background loops
    logger.info("TGmonitor backend starting up")
    try:
        count = await cleanup_old_screenshots()
        logger.info(f"Initial cleanup: removed {count} old screenshots")
    except Exception as e:
        logger.warning(f"Initial cleanup failed (non-fatal): {e}")

    # Start analysis worker loop
    analysis_task = asyncio.create_task(analysis_loop(settings))
    logger.info("Analysis worker loop started")

    # Start daily journal cron
    journal_task = asyncio.create_task(journal_cron_loop())
    logger.info("Daily journal cron loop started")

    yield

    # Shutdown
    analysis_task.cancel()
    journal_task.cancel()
    try:
        await analysis_task
        await journal_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="TGmonitor API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(screenshots.router)
app.include_router(alerts.router)
app.include_router(journals.router)


@app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
async def health():
    return HealthResponse(status="ok")


@app.get("/api/v1/ready", response_model=ReadyResponse, tags=["health"])
async def ready(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(select(1))
        return ReadyResponse(db="ok")
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return ReadyResponse(db="error")
