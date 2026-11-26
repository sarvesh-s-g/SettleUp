"""Shared pytest fixtures.

The tests run against a REAL PostgreSQL database (TEST_DATABASE_URL), because the
project relies on PostgreSQL features such as CHECK constraints, ON DELETE CASCADE
and SELECT ... FOR UPDATE. The test database is rebuilt with the Alembic migrations
once per test run, and every table is emptied after each test.
"""
import os

import pytest
from pydantic_settings import BaseSettings, SettingsConfigDict


class _TestSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    TEST_DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/settleup_test"


TEST_DATABASE_URL = _TestSettings().TEST_DATABASE_URL
# Must happen BEFORE app.config is imported, so the app talks to the test database.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402
from app.main import app  # noqa: E402

TABLES = "expense_splits, expenses, settlements, group_members, groups, users"


@pytest.fixture(scope="session")
def migrated_db():
    """Drop everything and run 'alembic upgrade head' on the test database."""
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")
    yield


@pytest.fixture
def client(migrated_db):
    with TestClient(app) as test_client:
        yield test_client
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))


@pytest.fixture
def make_user(client):
    """Register + log in a user. Returns a dict with id, name, email and auth headers."""

    def _make(name: str, email: str | None = None, password: str = "Password@123") -> dict:
        email = email or f"{name.lower()}@example.com"
        response = client.post("/api/v1/auth/register", json={"name": name, "email": email, "password": password})
        assert response.status_code == 201, response.text
        login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        return {**response.json(), "headers": {"Authorization": f"Bearer {token}"}}

    return _make


@pytest.fixture
def roommates(client, make_user):
    """The four roommates of 'Room 204' used throughout the docs.
    Sarvesh creates the group (admin) and adds the other three."""
    users = {name: make_user(name) for name in ("Sarvesh", "Rahul", "Kiran", "Aman")}
    response = client.post("/api/v1/groups", json={"name": "Room 204"}, headers=users["Sarvesh"]["headers"])
    assert response.status_code == 201, response.text
    group_id = response.json()["id"]
    for name in ("Rahul", "Kiran", "Aman"):
        added = client.post(
            f"/api/v1/groups/{group_id}/members", json={"email": users[name]["email"]},
            headers=users["Sarvesh"]["headers"],
        )
        assert added.status_code == 201, added.text
    return {"group_id": group_id, **users}


def add_expense(client, group_id, headers, **overrides):
    """Helper used by several test modules to create an expense quickly."""
    body = {
        "description": "Groceries", "amount_paise": 120000, "category": "groceries",
        "expense_date": "2026-11-01", "split_type": "equal",
    }
    body.update(overrides)
    return client.post(f"/api/v1/groups/{group_id}/expenses", json=body, headers=headers)


def balances_by_name(client, group_id, headers) -> dict[str, int]:
    response = client.get(f"/api/v1/groups/{group_id}/balances", headers=headers)
    assert response.status_code == 200, response.text
    return {b["name"]: b["net_balance_paise"] for b in response.json()["balances"]}
