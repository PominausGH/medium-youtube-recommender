# tests/test_integration.py
"""
Integration tests for the full content curation flow.
"""
import pytest
import tempfile
import os
from unittest.mock import patch, Mock


@pytest.fixture
def temp_db():
    import tempfile
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    os.unlink(path)


def test_full_flow_add_interest_to_content(temp_db):
    """Test: Add interest -> Search -> Summarize -> Save -> Display"""
    from database import Database

    db = Database(temp_db)

    # 1. Add interest
    interest_id = db.add_interest("Python testing", source="manual")
    assert interest_id is not None

    # 2. Verify interest is active
    interests = db.get_interests(active_only=True)
    assert len(interests) == 1
    assert interests[0]['topic'] == "Python testing"

    # 3. Add mock content
    content_id = db.add_content(
        title="Python Testing Best Practices",
        url="https://example.com/python-testing",
        source_type="article",
        source_name="Dev.to",
        summary="A guide to testing in Python",
        recommendation="RECOMMENDED",
        relevance_score=0.9
    )

    # 4. Get recommended content
    content = db.get_recommended_content()
    assert len(content) == 1
    assert content[0]['title'] == "Python Testing Best Practices"

    # 5. Save to reading list
    saved_id = db.save_item(content_id)
    assert saved_id is not None

    # 6. Verify in reading list
    saved = db.get_saved_items(status='unread')
    assert len(saved) == 1

    # 7. Mark as read
    db.update_saved_item(saved_id, status='read')
    saved_read = db.get_saved_items(status='read')
    assert len(saved_read) == 1

    db.close()


def test_project_scan_to_suggestions():
    """Test: Scan project -> Get suggestions"""
    from project_scanner import ProjectScanner

    scanner = ProjectScanner()

    # Mock a project structure
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create mock requirements.txt
        with open(os.path.join(tmpdir, 'requirements.txt'), 'w') as f:
            f.write('fastapi==0.100.0\npytest==7.0.0\n')

        # Create mock Python file with TODO
        with open(os.path.join(tmpdir, 'main.py'), 'w') as f:
            f.write('# TODO: add authentication\nimport fastapi\n')

        result = scanner.scan_local(tmpdir)

        assert 'Python' in result['technologies']
        assert any('authentication' in t['text'].lower() for t in result['todos'])


def test_obsidian_export():
    """Test: Save item -> Export to Obsidian"""
    from obsidian_exporter import ObsidianExporter

    with tempfile.TemporaryDirectory() as vault:
        exporter = ObsidianExporter(vault)

        item = {
            'title': 'Test Article',
            'url': 'https://example.com/test',
            'source_name': 'Dev.to',
            'summary': 'A test summary',
            'skill_level': 'Intermediate',
        }

        filepath = exporter.export_item(item, notes="My notes here")

        assert os.path.exists(filepath)

        with open(filepath) as f:
            content = f.read()

        assert 'Test Article' in content
        assert 'My notes here' in content
        assert 'example.com/test' in content
