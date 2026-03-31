import uuid
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
import io

from app.config import Settings


async def save_screenshot(
    file_content: bytes,
    employee_id: str,
    captured_at: datetime,
    app_name: str | None,
    window_title: str | None,
    settings: Settings,
) -> tuple[str, str, int]:
    """
    Save a screenshot JPEG to the filesystem.

    Returns:
        (file_path, thumb_path, file_size_bytes)
        file_path is relative to screenshot_dir, e.g. "emp-uuid/2026-03-31/abc.jpg"
        thumb_path is relative to screenshot_dir, e.g. "emp-uuid/2026-03-31/abc.thumb.jpg"
    """
    screenshot_uuid = uuid.uuid4()
    date_str = captured_at.strftime("%Y-%m-%d")
    date_dir = Path(settings.screenshot_dir) / employee_id / date_str
    date_dir.mkdir(parents=True, exist_ok=True)

    # Save main file
    file_name = f"{screenshot_uuid}.jpg"
    file_path = date_dir / file_name
    await _write_file(file_path, file_content)

    # Generate thumbnail (320px wide)
    thumb_name = f"{screenshot_uuid}.thumb.jpg"
    thumb_path = date_dir / thumb_name
    await _generate_thumbnail(file_content, thumb_path)

    relative_file_path = f"{employee_id}/{date_str}/{file_name}"
    relative_thumb_path = f"{employee_id}/{date_str}/{thumb_name}"

    return relative_file_path, relative_thumb_path, len(file_content)


async def _write_file(path: Path, content: bytes) -> None:
    """Write bytes to a file synchronously."""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _write_file_sync, path, content)


def _write_file_sync(path: Path, content: bytes) -> None:
    with open(path, "wb") as f:
        f.write(content)


async def _generate_thumbnail(content: bytes, thumb_path: Path) -> None:
    """Generate a 320px-wide JPEG thumbnail."""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _generate_thumbnail_sync, content, thumb_path)


def _generate_thumbnail_sync(content: bytes, thumb_path: Path) -> None:
    img = Image.open(io.BytesIO(content))
    img = img.convert("RGB")
    img.thumbnail((320, 320), Image.LANCZOS)
    img.save(thumb_path, "JPEG", quality=85)
