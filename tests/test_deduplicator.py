# tests/test_deduplicator.py
import pytest
from deduplicator import Deduplicator


def test_exact_url_match():
    dedup = Deduplicator()
    items = [
        {'title': 'Learn Python Programming Basics', 'url': 'https://example.com/a'},
        {'title': 'A Completely Different Article About JavaScript', 'url': 'https://example.com/a'},  # Duplicate URL
        {'title': 'Master Machine Learning Fundamentals', 'url': 'https://example.com/c'},
    ]
    result = dedup.deduplicate(items)
    assert len(result) == 2


def test_similar_title_match():
    dedup = Deduplicator()
    items = [
        {'title': 'Complete Guide to FastAPI Framework', 'url': 'https://a.com'},
        {'title': 'Complete Guide to FastAPI Framework Tutorial', 'url': 'https://b.com'},  # Similar title (88.6% similar)
        {'title': 'Understanding React Hooks and State Management', 'url': 'https://c.com'},
    ]
    result = dedup.deduplicate(items)
    assert len(result) == 2


def test_keeps_highest_score():
    dedup = Deduplicator()
    items = [
        {'title': 'FastAPI Guide', 'url': 'https://a.com', 'score': 10},
        {'title': 'FastAPI Guide', 'url': 'https://b.com', 'score': 50},
    ]
    result = dedup.deduplicate(items)
    assert len(result) == 1
    assert result[0]['score'] == 50


def test_empty_list():
    dedup = Deduplicator()
    result = dedup.deduplicate([])
    assert result == []


def test_single_item():
    dedup = Deduplicator()
    items = [{'title': 'Only Item', 'url': 'https://example.com/only'}]
    result = dedup.deduplicate(items)
    assert len(result) == 1
    assert result[0]['title'] == 'Only Item'


def test_custom_threshold():
    # Lower threshold should match more titles as duplicates
    dedup = Deduplicator(title_threshold=0.5)
    items = [
        {'title': 'Python Tutorial', 'url': 'https://a.com'},
        {'title': 'Python Guide', 'url': 'https://b.com'},
    ]
    result = dedup.deduplicate(items)
    # With 0.5 threshold, these should be considered duplicates
    assert len(result) == 1


def test_uses_upvotes_for_ranking():
    dedup = Deduplicator()
    items = [
        {'title': 'Same Title', 'url': 'https://a.com', 'upvotes': 5},
        {'title': 'Same Title', 'url': 'https://b.com', 'upvotes': 100},
    ]
    result = dedup.deduplicate(items)
    assert len(result) == 1
    assert result[0]['upvotes'] == 100


def test_uses_relevance_score():
    dedup = Deduplicator()
    items = [
        {'title': 'Same Title', 'url': 'https://a.com', 'relevance_score': 0.5},
        {'title': 'Same Title', 'url': 'https://b.com', 'relevance_score': 0.9},
    ]
    result = dedup.deduplicate(items)
    assert len(result) == 1
    assert result[0]['relevance_score'] == 0.9


def test_handles_none_values():
    dedup = Deduplicator()
    items = [
        {'title': 'Learn Python Programming from Scratch', 'url': 'https://a.com', 'score': None},
        {'title': 'Building Web Applications with Django', 'url': 'https://b.com', 'upvotes': None},
    ]
    result = dedup.deduplicate(items)
    assert len(result) == 2


def test_handles_missing_fields():
    dedup = Deduplicator()
    items = [
        {'title': 'Learn Python Programming from Scratch'},  # Missing url
        {'url': 'https://b.com'},  # Missing title
        {'title': 'Building REST APIs with FastAPI', 'url': 'https://c.com'},
    ]
    result = dedup.deduplicate(items)
    assert len(result) == 3
