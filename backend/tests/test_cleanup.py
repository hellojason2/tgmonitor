import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.models import Screenshot
from app.main import cleanup_old_screenshots


@pytest.mark.asyncio
async def test_cleanup_deletes_old_screenshots(test_db, test_employee, tmp_path):
    """Screenshots older than 30 days are deleted."""
    from app.config import Settings

    # Create a settings with a temp screenshot dir
    settings = Settings()
    old_dir = tmp_path / "screenshots"
    old_dir.mkdir()

    # Patch settings for this test
    import app.main
    original_settings = app.main.settings
    app.main.settings = settings

    # Insert an old screenshot (31 days ago)
    old_screenshot = Screenshot(
        id=uuid4(),
        device_id=uuid4(),
        employee_id=test_employee.id,
        captured_at=datetime.now(timezone.utc) - timedelta(days=31),
        received_at=datetime.now(timezone.utc) - timedelta(days=31),
        file_path="old/2026-01-01/test.jpg",
        analysis_status="done",
    )
    test_db.add(old_screenshot)

    # Insert a recent screenshot (1 day ago)
    recent_screenshot = Screenshot(
        id=uuid4(),
        device_id=uuid4(),
        employee_id=test_employee.id,
        captured_at=datetime.now(timezone.utc) - timedelta(days=1),
        received_at=datetime.now(timezone.utc) - timedelta(days=1),
        file_path="recent/2026-03-30/test.jpg",
        analysis_status="pending",
    )
    test_db.add(recent_screenshot)
    await test_db.commit()

    # Run cleanup
    deleted = await cleanup_old_screenshots()

    assert deleted == 1

    # Verify old one is gone, recent one remains
    result = await test_db.execute(
        select(Screenshot).where(Screenshot.id == old_screenshot.id)
    )
    assert result.scalar_one_or_none() is None

    result2 = await test_db.execute(
        select(Screenshot).where(Screenshot.id == recent_screenshot.id)
    )
    assert result2.scalar_one_or_none() is not None

    app.main.settings = original_settings
