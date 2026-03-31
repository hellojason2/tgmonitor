"""
Employee management endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Employee

router = APIRouter(prefix="/api/v1/employees", tags=["employees"])


@router.get("")
async def list_employees(db: AsyncSession = Depends(get_db)):
    """List all employees."""
    result = await db.execute(select(Employee).order_by(Employee.name))
    employees = result.scalars().all()
    return [
        {
            "id": str(emp.id),
            "name": emp.name,
            "location": emp.location,
            "created_at": emp.created_at.isoformat() if emp.created_at else None,
        }
        for emp in employees
    ]


@router.get("/{employee_id}")
async def get_employee(employee_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a single employee by ID."""
    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {
        "id": str(emp.id),
        "name": emp.name,
        "location": emp.location,
        "created_at": emp.created_at.isoformat() if emp.created_at else None,
    }
