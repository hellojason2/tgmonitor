"""
Alert and journal API endpoints.
"""

from datetime import datetime, date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Alert, Screenshot, Employee
from app.schemas import Alert as AlertSchema

router = APIRouter(prefix="/api/v1", tags=["alerts"])


@router.get("/alerts", response_model=list[AlertSchema])
async def list_alerts(
    employee_id: UUID | None = None,
    acknowledged: bool | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List alerts, optionally filtered by employee and acknowledged status."""
    query = select(Alert).order_by(desc(Alert.created_at)).limit(limit)

    if employee_id is not None:
        query = query.where(Alert.employee_id == employee_id)
    if acknowledged is not None:
        query = query.where(Alert.acknowledged == acknowledged)

    result = await db.execute(query)
    alerts = result.scalars().all()
    return alerts


@router.get("/alerts/{alert_id}", response_model=AlertSchema)
async def get_alert(alert_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a single alert by ID."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: UUID, db: AsyncSession = Depends(get_db)):
    """Acknowledge an alert."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await db.execute(
        update(Alert).where(Alert.id == alert_id).values(acknowledged=True)
    )
    await db.commit()
    return {"status": "acknowledged"}


@router.post("/alerts/acknowledge-all")
async def acknowledge_all_alerts(
    employee_id: UUID | None = None, db: AsyncSession = Depends(get_db)
):
    """Acknowledge all alerts, optionally for a specific employee."""
    query = update(Alert).where(Alert.acknowledged == False)
    if employee_id is not None:
        query = query.where(Alert.employee_id == employee_id)
    await db.execute(query.values(acknowledged=True))
    await db.commit()
    return {"status": "all_acknowledged"}
