import asyncio
import os

# Set env vars BEFORE importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("GEMINI_API_KEY", "test-key-for-unit-tests-only")
os.environ.setdefault("API_SECRET_KEY", "test-secret-for-unit-tests-only")
os.environ.setdefault("SCREENSHOT_DIR", "/tmp/test-screenshots")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models import Employee, Device
import bcrypt


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
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
    emp = Employee(id="11111111-1111-1111-1111-111111111111", name="Test Employee")
    test_db.add(emp)
    await test_db.commit()
    return emp


@pytest_asyncio.fixture
async def test_device(test_db, test_employee):
    # Hash of 'test-token-abc123'
    token = "test-token-abc123"
    token_hash = bcrypt.hashpw(token.encode(), bcrypt.gensalt()).decode()
    device = Device(
        id="22222222-2222-2222-2222-222222222222",
        machine_id="test-mac-01",
        token_hash=token_hash,
        employee_id=test_employee.id,
    )
    test_db.add(device)
    await test_db.commit()
    return device, token


@pytest_asyncio.fixture
async def client(test_db):
    async def _override():
        yield test_db

    app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_no_auth(test_db):
    async def _override():
        yield test_db

    app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
