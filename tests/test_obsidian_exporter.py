# tests/test_obsidian_exporter.py
import pytest
import tempfile
import os
from obsidian_exporter import ObsidianExporter


@pytest.fixture
def temp_vault():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_exports_single_item(temp_vault):
    exporter = ObsidianExporter(vault_path=temp_vault)
    item = {
        'title': 'FastAPI Async Patterns',
        'url': 'https://dev.to/fastapi-async',
        'source_name': 'Dev.to',
        'summary': 'Great article about async patterns.',
        'skill_level': 'Intermediate',
    }

    filepath = exporter.export_item(item)

    assert os.path.exists(filepath)
    with open(filepath) as f:
        content = f.read()
    assert 'FastAPI Async Patterns' in content
    assert 'dev.to/fastapi-async' in content


def test_creates_date_folder(temp_vault):
    exporter = ObsidianExporter(vault_path=temp_vault)
    item = {
        'title': 'Test Article',
        'url': 'https://example.com/test',
        'source_name': 'Test',
    }

    filepath = exporter.export_item(item)

    # Should be in AI-Curated/YYYY-MM-DD/ folder
    assert 'AI-Curated' in filepath
    assert os.path.dirname(filepath) != temp_vault


def test_slugifies_filename(temp_vault):
    exporter = ObsidianExporter(vault_path=temp_vault)
    item = {
        'title': 'What is FastAPI? A Complete Guide!!!',
        'url': 'https://example.com/test',
        'source_name': 'Dev.to',
    }

    filepath = exporter.export_item(item)
    filename = os.path.basename(filepath)

    assert '?' not in filename
    assert '!' not in filename
    assert filename.endswith('.md')


def test_includes_frontmatter(temp_vault):
    exporter = ObsidianExporter(vault_path=temp_vault)
    item = {
        'title': 'Test Article',
        'url': 'https://example.com/test',
        'source_name': 'Dev.to',
        'skill_level': 'Beginner',
    }

    filepath = exporter.export_item(item)

    with open(filepath) as f:
        content = f.read()
    assert content.startswith('---')
    assert 'title: "Test Article"' in content
    assert 'source: Dev.to' in content
    assert 'skill_level: Beginner' in content


def test_includes_notes_when_provided(temp_vault):
    exporter = ObsidianExporter(vault_path=temp_vault)
    item = {
        'title': 'Test Article',
        'url': 'https://example.com/test',
        'source_name': 'Test',
    }
    notes = "This looks relevant to my current project."

    filepath = exporter.export_item(item, notes=notes)

    with open(filepath) as f:
        content = f.read()
    assert 'Why I saved this' in content
    assert notes in content
