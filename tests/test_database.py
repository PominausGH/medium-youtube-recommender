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


# Content CRUD tests
def test_add_content(db):
    content_id = db.add_content(
        title="FastAPI Tutorial",
        url="https://example.com/fastapi",
        source_type="article",
        source_name="Dev.to"
    )
    assert content_id is not None


def test_add_duplicate_url_returns_existing(db):
    id1 = db.add_content(title="Title 1", url="https://example.com/1", source_type="article")
    id2 = db.add_content(title="Title 2", url="https://example.com/1", source_type="article")
    assert id1 == id2


def test_get_content_by_id(db):
    content_id = db.add_content(
        title="FastAPI Tutorial",
        url="https://example.com/fastapi",
        source_type="article",
        summary="A great tutorial",
        recommendation="RECOMMENDED"
    )
    content = db.get_content(content_id)
    assert content['title'] == "FastAPI Tutorial"
    assert content['recommendation'] == "RECOMMENDED"


def test_get_recommended_content(db):
    db.add_content(title="Good", url="https://a.com", source_type="article", recommendation="RECOMMENDED")
    db.add_content(title="Bad", url="https://b.com", source_type="article", recommendation="SKIP")
    recommended = db.get_recommended_content()
    assert len(recommended) == 1
    assert recommended[0]['title'] == "Good"


# Saved items tests
def test_save_item(db):
    content_id = db.add_content(title="Test", url="https://test.com", source_type="article")
    saved_id = db.save_item(content_id)
    assert saved_id is not None
    saved = db.get_saved_items()
    assert len(saved) == 1


def test_update_saved_item_status(db):
    content_id = db.add_content(title="Test", url="https://test.com", source_type="article")
    saved_id = db.save_item(content_id)
    db.update_saved_item(saved_id, status="read")
    saved = db.get_saved_items(status="read")
    assert len(saved) == 1


def test_record_user_action(db):
    content_id = db.add_content(title="Test", url="https://test.com", source_type="article")
    db.record_action(content_id, "clicked")
    actions = db.get_user_actions(content_id)
    assert len(actions) == 1
    assert actions[0]['action'] == "clicked"
