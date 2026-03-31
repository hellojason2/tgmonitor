"""
Daily journal API endpoints.
"""

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import DailyJournal
from app.schemas import DailyJournal as JournalSchema

router = APIRouter(prefix="/api/v1", tags=["journals"])


@router.get("/journals", response_model=list[JournalSchema])
async def list_journals(
    employee_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=30, le=180),
    db: AsyncSession = Depends(get_db),
):
    """List daily journals, optionally filtered by employee and date range."""
    query = select(DailyJournal).order_by(desc(DailyJournal.journal_date)).limit(limit)

    if employee_id is not None:
        query = query.where(DailyJournal.employee_id == employee_id)
    if start_date is not None:
        query = query.where(DailyJournal.journal_date >= start_date)
    if end_date is not None:
        query = query.where(DailyJournal.journal_date <= end_date)

    result = await db.execute(query)
    journals = result.scalars().all()
    return journals


@router.get("/journals/{journal_id}", response_model=JournalSchema)
async def get_journal(journal_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a single journal by ID."""
    result = await db.execute(select(DailyJournal).where(DailyJournal.id == journal_id))
    journal = result.scalar_one_or_none()
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    return journal


@router.get("/journals/latest/{employee_id}", response_model=JournalSchema)
async def get_latest_journal(employee_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get the most recent journal for an employee."""
    result = await db.execute(
        select(DailyJournal)
        .where(DailyJournal.employee_id == employee_id)
        .order_by(desc(DailyJournal.journal_date))
        .limit(1)
    )
    journal = result.scalar_one_or_none()
    if not journal:
        raise HTTPException(status_code=404, detail="No journal found for this employee")
    return journal
