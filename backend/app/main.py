import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

from fastapi import Depends, FastAPI
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database import get_db, async_session_factory
from app.models import Screenshot
from app.routers import screenshots
from app.schemas import HealthResponse, ReadyResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = Settings()


async def cleanup_old_screenshots() -> int:
    """Delete screenshots older than 30 days. Returns count of deleted records."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    async with async_session_factory() as db:
        # Fetch file paths to delete
        result = await db.execute(
            select(Screenshot.file_path, Screenshot.thumb_path)
            .where(Screenshot.captured_at < cutoff)
        )
        rows = result.all()

        if not rows:
            return 0

        # Delete filesystem files
        from pathlib import Path
        for row in rows:
            for path in [row.file_path, row.thumb_path]:
                if path:
                    full = Path(settings.screenshot_dir) / path
                    try:
                        full.unlink(missing_ok=True)
                    except Exception as e:
                        logger.warning(f"Failed to delete file {full}: {e}")

        # Delete DB records
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: run initial cleanup + start background loop
    logger.info("TGmonitor backend starting up")
    try:
        count = await cleanup_old_screenshots()
        logger.info(f"Initial cleanup: removed {count} old screenshots")
    except Exception as e:
        logger.warning(f"Initial cleanup failed (non-fatal): {e}")

    loop = asyncio.create_task(cleanup_loop())
    yield
    loop.cancel()


app = FastAPI(
    title="TGmonitor API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(screenshots.router, prefix="/api/v1")


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
