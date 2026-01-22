# tests/test_integration.py
"""
Integration tests for the full content curation flow.
"""
import os
import tempfile

import pytest

from database import Database
from project_scanner import ProjectScanner
from obsidian_exporter import ObsidianExporter


def test_full_flow_add_interest_to_content(temp_db):
    """Test: Add interest -> Search -> Summarize -> Save -> Display"""
    db = Database(temp_db)

    # 1. Add interest
    interest_id = db.add_interest("Python testing", source="manual")
    assert interest_id is not None, "add_interest should return a valid ID"

    # 2. Verify interest is active
    interests = db.get_interests(active_only=True)
    assert len(interests) == 1, "Should have exactly one active interest"
    assert interests[0]['topic'] == "Python testing", "Interest topic should match"

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
    assert len(content) == 1, "Should have exactly one recommended content item"
    assert content[0]['title'] == "Python Testing Best Practices", "Content title should match"

    # 5. Save to reading list
    saved_id = db.save_item(content_id)
    assert saved_id is not None, "save_item should return a valid ID"

    # 6. Verify in reading list
    saved = db.get_saved_items(status='unread')
    assert len(saved) == 1, "Should have exactly one unread saved item"

    # 7. Mark as read
    db.update_saved_item(saved_id, status='read')
    saved_read = db.get_saved_items(status='read')
    assert len(saved_read) == 1, "Should have exactly one read item"

    # 8. Verify no unread items remain
    assert len(db.get_saved_items(status='unread')) == 0, "No items should remain unread"

    db.close()


def test_project_scan_to_suggestions():
    """Test: Scan project -> Get suggestions"""
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

        assert 'Python' in result['technologies'], "Should detect Python as a technology"
        assert any('authentication' in t['text'].lower() for t in result['todos']), \
            "Should find authentication TODO"


def test_obsidian_export():
    """Test: Save item -> Export to Obsidian"""
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

        assert os.path.exists(filepath), "Exported file should exist"

        with open(filepath) as f:
            content = f.read()

        assert 'Test Article' in content, "Content should include article title"
        assert 'My notes here' in content, "Content should include user notes"
        assert 'example.com/test' in content, "Content should include article URL"
