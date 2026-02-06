"""
Pytest fixtures for use-case tests.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def temp_db(monkeypatch):
    """Use a temporary database for each test."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    path = Path(tmp.name)

    import db

    monkeypatch.setattr(db, "DB_PATH", path)
    db.init_db()
    yield path
    path.unlink(missing_ok=True)


@pytest.fixture
def sample_session(temp_db):
    """Create a sample email session for tests."""
    import db

    session_id = db.create_session(
        customer_email="alice@example.com",
        first_name="Alice",
        last_name="Smith",
        shopify_customer_id="gid://shopify/Customer/123",
    )
    return session_id
