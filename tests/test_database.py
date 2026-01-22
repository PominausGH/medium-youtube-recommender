# tests/test_database.py
import pytest
import os
import tempfile
from database import Database

@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    database = Database(path)
    yield database
    database.close()
    os.unlink(path)

def test_database_creates_tables(db):
    tables = db.get_tables()
    expected = {'interests', 'content', 'saved_items', 'user_actions', 'project_scans', 'interest_suggestions'}
    assert expected.issubset(set(tables))

def test_add_interest(db):
    interest_id = db.add_interest("FastAPI", source="manual")
    assert interest_id is not None
    interests = db.get_interests()
    assert len(interests) == 1
    assert interests[0]['topic'] == "FastAPI"

def test_get_active_interests(db):
    db.add_interest("FastAPI", source="manual")
    db.add_interest("Django", source="llm", status="paused")
    active = db.get_interests(active_only=True)
    assert len(active) == 1
    assert active[0]['topic'] == "FastAPI"

def test_update_interest_status(db):
    interest_id = db.add_interest("FastAPI", source="manual")
    db.update_interest(interest_id, status="paused")
    interests = db.get_interests()
    assert interests[0]['status'] == "paused"

def test_delete_interest(db):
    interest_id = db.add_interest("FastAPI", source="manual")
    db.delete_interest(interest_id)
    interests = db.get_interests()
    assert len(interests) == 0
