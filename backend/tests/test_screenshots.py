import io
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from httpx import AsyncClient
from PIL import Image

from app.models import Screenshot


def create_test_jpeg() -> bytes:
    """Create a minimal valid JPEG in memory."""
    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf.read()


def create_test_png() -> bytes:
    """Create a PNG image (non-JPEG, should be rejected)."""
    img = Image.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


@pytest.mark.asyncio
async def test_upload_requires_auth(client_no_auth, test_employee):
    """Request without Authorization header returns 401 or 403."""
    jpeg_data = create_test_jpeg()
    response = await client_no_auth.post(
        "/api/v1/screenshots",
        files={"file": ("test.jpg", io.BytesIO(jpeg_data), "image/jpeg")},
        data={
            "employee_id": "11111111-1111-1111-1111-111111111111",
            "machine_id": "test-mac-01",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_upload_with_invalid_token(client_no_auth, test_employee):
    """Request with wrong Bearer token returns 401."""
    jpeg_data = create_test_jpeg()
    response = await client_no_auth.post(
        "/api/v1/screenshots",
        files={"file": ("test.jpg", io.BytesIO(jpeg_data), "image/jpeg")},
        data={
            "employee_id": "11111111-1111-1111-1111-111111111111",
            "machine_id": "test-mac-01",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
        headers={"Authorization": "Bearer wrong-token-xyz"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_rejects_non_jpeg(client, test_device, test_employee):
    """Uploading a PNG file returns 400."""
    device, token = test_device
    png_data = create_test_png()

    response = await client.post(
        "/api/v1/screenshots",
        files={"file": ("test.png", io.BytesIO(png_data), "image/png")},
        data={
            "employee_id": str(test_employee.id),
            "machine_id": device.machine_id,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "app_name": "TestApp",
            "window_title": "Test Window",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "JPEG" in response.json().get("detail", "")


@pytest.mark.asyncio
async def test_upload_with_valid_token(client, test_device, test_employee):
    """A valid token uploads successfully and returns 201."""
    device, token = test_device
    jpeg_data = create_test_jpeg()

    response = await client.post(
        "/api/v1/screenshots",
        files={"file": ("test.jpg", io.BytesIO(jpeg_data), "image/jpeg")},
        data={
            "employee_id": str(test_employee.id),
            "machine_id": device.machine_id,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "app_name": "TestApp",
            "window_title": "Test Window",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "file_path" in data
    assert "received_at" in data


@pytest.mark.asyncio
async def test_upload_invalid_employee(client, test_device):
    """Upload with non-existent employee_id returns 404."""
    device, token = test_device
    jpeg_data = create_test_jpeg()

    response = await client.post(
        "/api/v1/screenshots",
        files={"file": ("test.jpg", io.BytesIO(jpeg_data), "image/jpeg")},
        data={
            "employee_id": "00000000-0000-0000-0000-000000000000",
            "machine_id": device.machine_id,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """GET /api/v1/health returns 200."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ready_endpoint(client):
    """GET /api/v1/ready returns 200 with db status."""
    response = await client.get("/api/v1/ready")
    assert response.status_code == 200
    assert "db" in response.json()
