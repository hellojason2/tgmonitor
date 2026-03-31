"""
Unit tests for alerts and journals API endpoints.
"""

import uuid
from datetime import datetime, timezone, date

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models import Employee, Alert, DailyJournal


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db(test_engine):
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def test_employee(test_db):
    emp = Employee(id=uuid.UUID("11111111-1111-1111-1111-111111111111"), name="Test Employee")
    test_db.add(emp)
    await test_db.commit()
    return emp


@pytest_asyncio.fixture
async def test_alert(test_db, test_employee):
    alert = Alert(
        id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        employee_id=test_employee.id,
        screenshot_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        alert_type="file_transfer",
        caption="Employee uploading files to Google Drive",
        risk_score="high",
        acknowledged=False,
    )
    test_db.add(alert)
    await test_db.commit()
    return alert


@pytest_asyncio.fixture
async def test_journal(test_db, test_employee):
    journal = DailyJournal(
        id=uuid.UUID("55555555-5555-5555-5555-555555555555"),
        employee_id=test_employee.id,
        journal_date=date.today(),
        narrative="Employee worked on documents in the morning and attended meetings in the afternoon.",
        screenshot_count=50,
        high_risk_count=2,
    )
    test_db.add(journal)
    await test_db.commit()
    return journal


@pytest_asyncio.fixture
async def client(test_db):
    async def _override():
        yield test_db
    app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestAlertsAPI:
    @pytest.mark.asyncio
    async def test_list_alerts_empty(self, client):
        response = await client.get("/api/v1/alerts")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_alerts_with_data(self, client, test_alert):
        response = await client.get("/api/v1/alerts")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["alert_type"] == "file_transfer"
        assert data[0]["risk_score"] == "high"

    @pytest.mark.asyncio
    async def test_list_alerts_filter_by_employee(self, client, test_alert, test_employee):
        response = await client.get(f"/api/v1/alerts?employee_id={test_employee.id}")
        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.asyncio
    async def test_list_alerts_filter_by_acknowledged(self, client, test_alert):
        response = await client.get("/api/v1/alerts?acknowledged=false")
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = await client.get("/api/v1/alerts?acknowledged=true")
        assert response.status_code == 200
        assert len(response.json()) == 0

    @pytest.mark.asyncio
    async def test_get_alert_by_id(self, client, test_alert):
        response = await client.get(f"/api/v1/alerts/{test_alert.id}")
        assert response.status_code == 200
        assert response.json()["alert_type"] == "file_transfer"

    @pytest.mark.asyncio
    async def test_get_alert_not_found(self, client):
        fake_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
        response = await client.get(f"/api/v1/alerts/{fake_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, client, test_alert):
        response = await client.post(f"/api/v1/alerts/{test_alert.id}/acknowledge")
        assert response.status_code == 200
        assert response.json()["status"] == "acknowledged"

        # Verify acknowledged
        get_response = await client.get(f"/api/v1/alerts/{test_alert.id}")
        assert get_response.json()["acknowledged"] is True


class TestJournalsAPI:
    @pytest.mark.asyncio
    async def test_list_journals_empty(self, client):
        response = await client.get("/api/v1/journals")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_journals_with_data(self, client, test_journal):
        response = await client.get("/api/v1/journals")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["narrative"] != ""

    @pytest.mark.asyncio
    async def test_list_journals_filter_by_employee(self, client, test_journal, test_employee):
        response = await client.get(f"/api/v1/journals?employee_id={test_employee.id}")
        assert response.status_code == 200
        assert len(response.json()) == 1

    @pytest.mark.asyncio
    async def test_get_latest_journal(self, client, test_journal, test_employee):
        response = await client.get(f"/api/v1/journals/latest/{test_employee.id}")
        assert response.status_code == 200
        assert response.json()["employee_id"] == str(test_employee.id)

    @pytest.mark.asyncio
    async def test_get_latest_journal_not_found(self, client):
        fake_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
        response = await client.get(f"/api/v1/journals/latest/{fake_id}")
        assert response.status_code == 404
