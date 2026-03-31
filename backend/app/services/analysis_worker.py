"""
Background analysis worker for AI screenshot processing.

Polls for pending screenshots and processes them through Gemini.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models import Screenshot, AnalysisResult, Alert, Employee
from app.config import Settings
from app.services.ai_analysis import (
    analyze_screenshot,
    calculate_risk_score,
    determine_alert_type,
)

logger = logging.getLogger(__name__)

PROCESSING_BATCH_SIZE = 10
POLL_INTERVAL_SECONDS = 30


async def process_pending_screenshots(settings: Settings) -> int:
    """
    Find pending screenshots, analyze them, store results.
    Returns count of screenshots processed.
    """
    async with async_session_factory() as db:
        # Find pending screenshots
        result = await db.execute(
            select(Screenshot)
            .where(Screenshot.analysis_status == "pending")
            .limit(PROCESSING_BATCH_SIZE)
        )
        pending = result.scalars().all()

        if not pending:
            return 0

        processed = 0

        for screenshot in pending:
            try:
                # Mark as processing
                await db.execute(
                    update(Screenshot)
                    .where(Screenshot.id == screenshot.id)
                    .values(analysis_status="processing")
                )
                await db.commit()

                # Check for blank/idle screen (skip if app_name and window_title are both empty)
                if not screenshot.app_name and not screenshot.window_title:
                    await db.execute(
                        update(Screenshot)
                        .where(Screenshot.id == screenshot.id)
                        .values(analysis_status="skipped", analyzed_at=datetime.now(timezone.utc))
                    )
                    await db.commit()
                    logger.info(f"Screenshot {screenshot.id}: skipped (blank/idle)")
                    continue

                # Build file path
                file_path = Path(settings.screenshot_dir) / screenshot.file_path
                if not file_path.exists():
                    logger.warning(f"Screenshot file not found: {file_path}")
                    await db.execute(
                        update(Screenshot)
                        .where(Screenshot.id == screenshot.id)
                        .values(analysis_status="error")
                    )
                    await db.commit()
                    continue

                # Analyze with Gemini
                caption, risk_score, tokens_used, api_cost = analyze_screenshot(
                    file_path, screenshot.app_name, screenshot.window_title, settings
                )

                # Store analysis result
                analysis = AnalysisResult(
                    screenshot_id=screenshot.id,
                    caption=caption,
                    risk_score=risk_score,
                    model_used="gemini-2.5-flash-lite",
                    tokens_used=tokens_used,
                    api_cost_usd=api_cost,
                )
                db.add(analysis)

                # Create alert if high risk
                if risk_score == "high":
                    alert_type = determine_alert_type(caption, risk_score) or "suspicious_activity"
                    alert = Alert(
                        employee_id=screenshot.employee_id,
                        screenshot_id=screenshot.id,
                        alert_type=alert_type,
                        caption=caption,
                        risk_score=risk_score,
                    )
                    db.add(alert)

                # Update screenshot status
                await db.execute(
                    update(Screenshot)
                    .where(Screenshot.id == screenshot.id)
                    .values(
                        analysis_status="done",
                        analyzed_at=datetime.now(timezone.utc),
                    )
                )
                await db.commit()
                processed += 1
                logger.info(f"Screenshot {screenshot.id}: analyzed, risk={risk_score}")

            except Exception as e:
                logger.error(f"Failed to analyze screenshot {screenshot.id}: {e}")
                await db.execute(
                    update(Screenshot)
                    .where(Screenshot.id == screenshot.id)
                    .values(analysis_status="error")
                )
                await db.commit()

        return processed


async def analysis_loop(settings: Settings) -> None:
    """Run the analysis worker poll loop."""
    logger.info("Analysis worker loop started")
    while True:
        try:
            count = await process_pending_screenshots(settings)
            if count > 0:
                logger.info(f"Analysis loop: processed {count} screenshots")
        except Exception as e:
            logger.error(f"Analysis loop error: {e}")

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


# ─── Daily Journal Generation ────────────────────────────────────────────────

JOURNAL_PROMPT = """You are an employee activity monitor. Based on the following screenshot captions from an employee's workday, write a brief narrative summary (3-5 sentences) describing their overall activity patterns. Focus on notable activities, applications used, and any concerning behavior.

Screenshots:
{captions}

Write a professional, factual narrative summary.
"""


async def generate_daily_journal(employee_id: str, journal_date: date, settings: Settings) -> tuple[str, int, int]:
    """
    Generate a daily journal for an employee.
    Returns (narrative, screenshot_count, high_risk_count).
    """
    async with async_session_factory() as db:
        # Get all analyzed screenshots for this employee on this date
        start_of_day = datetime.combine(journal_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_of_day = datetime.combine(journal_date, datetime.max.time()).replace(tzinfo=timezone.utc)

        result = await db.execute(
            select(Screenshot, AnalysisResult)
            .join(AnalysisResult, Screenshot.id == AnalysisResult.screenshot_id)
            .where(
                Screenshot.employee_id == employee_id,
                Screenshot.captured_at >= start_of_day,
                Screenshot.captured_at <= end_of_day,
                Screenshot.analysis_status == "done",
            )
            .order_by(Screenshot.captured_at)
        )
        rows = result.all()

        if not rows:
            return ("No activity recorded for this day.", 0, 0)

        screenshots = [row[0] for row in rows]
        high_risk_count = sum(1 for r in rows if r[1].risk_score == "high")

        # Build captions list
        captions = []
        for screenshot, analysis in rows:
            ts = screenshot.captured_at.strftime("%H:%M")
            app = screenshot.app_name or "Unknown"
            cap = analysis.caption
            captions.append(f"[{ts}] {app}: {cap}")

        captions_text = "\n".join(captions[:50])  # Limit to first 50 for cost

        # Call Gemini for journal generation
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)

        model = genai.GenerativeModel("gemini-2.5-flash-lite")
        response = model.generate_content(
            JOURNAL_PROMPT.format(captions=captions_text),
            generation_config={"max_output_tokens": 500, "temperature": 0.4},
        )

        narrative = response.text.strip()

        return narrative, len(screenshots), high_risk_count


async def run_daily_journal_job(settings: Settings) -> None:
    """
    Run daily journal generation for all employees.
    Called at end of day by the cron-like scheduler in main.py.
    """
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1))
    logger.info(f"Running daily journal job for {yesterday}")

    async with async_session_factory() as db:
        result = await db.execute(select(Employee))
        employees = result.scalars().all()

        for employee in employees:
            try:
                narrative, screenshot_count, high_risk_count = await generate_daily_journal(
                    str(employee.id), yesterday, settings
                )

                # Upsert daily journal
                from sqlalchemy.dialects.postgresql import insert
                stmt = insert(DailyJournal).values(
                    employee_id=employee.id,
                    journal_date=yesterday,
                    narrative=narrative,
                    screenshot_count=screenshot_count,
                    high_risk_count=high_risk_count,
                )
                stmt = stmt.on_conflict_do_update(
                    constraint="daily_journals_employee_id_journal_date_key",
                    set_={
                        "narrative": stmt.excluded.narrative,
                        "screenshot_count": stmt.excluded.screenshot_count,
                        "high_risk_count": stmt.excluded.high_risk_count,
                        "generated_at": datetime.now(timezone.utc),
                    }
                )
                await db.execute(stmt)
                await db.commit()
                logger.info(f"Journal generated for employee {employee.id}: {screenshot_count} screenshots, {high_risk_count} high-risk")

            except Exception as e:
                logger.error(f"Failed to generate journal for employee {employee.id}: {e}")
