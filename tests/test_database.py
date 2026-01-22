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
