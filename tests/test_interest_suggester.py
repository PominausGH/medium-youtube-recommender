# tests/test_interest_suggester.py
"""Tests for LLM-powered interest suggester."""

import pytest
from unittest.mock import Mock, patch
from interest_suggester import InterestSuggester


@pytest.fixture
def mock_openai():
    with patch('interest_suggester.OpenAI') as mock:
        client = Mock()
        mock.return_value = client

        response = Mock()
        response.choices = [Mock()]
        response.choices[0].message.content = '''LEARNING:
- FastAPI best practices (commonly used patterns)
- SQLAlchemy async patterns (performance optimization)
- Python type hints (code quality)

PROBLEM_SOLVING:
- Database connection pooling (TODO: fix N+1 query)
- Authentication implementation (security improvement)'''

        client.chat.completions.create.return_value = response
        yield client


def test_suggests_learning_topics(mock_openai):
    """Test that suggester returns learning topics from scan result."""
    suggester = InterestSuggester(api_key="test")
    scan_result = {
        'technologies': ['Python', 'FastAPI', 'SQLAlchemy'],
        'todos': [{'file': 'main.py', 'text': 'fix N+1 query'}]
    }

    suggestions = suggester.suggest(scan_result)

    assert 'learning' in suggestions
    assert 'problem_solving' in suggestions
    assert len(suggestions['learning']) > 0


def test_handles_empty_scan(mock_openai):
    """Test that suggester handles empty scan results gracefully."""
    suggester = InterestSuggester(api_key="test")
    scan_result = {'technologies': [], 'todos': []}

    suggestions = suggester.suggest(scan_result)

    assert 'learning' in suggestions
    assert 'problem_solving' in suggestions


def test_parses_topic_with_reason(mock_openai):
    """Test that suggester parses topics and reasons correctly."""
    suggester = InterestSuggester(api_key="test")
    scan_result = {
        'technologies': ['Python', 'FastAPI'],
        'todos': []
    }

    suggestions = suggester.suggest(scan_result)

    # Check that at least one learning topic has both topic and reason
    assert len(suggestions['learning']) > 0
    first_topic = suggestions['learning'][0]
    assert 'topic' in first_topic
    assert 'reason' in first_topic


def test_calls_openai_with_correct_model(mock_openai):
    """Test that suggester uses the correct OpenAI model."""
    suggester = InterestSuggester(api_key="test")
    scan_result = {
        'technologies': ['Python'],
        'todos': []
    }

    suggester.suggest(scan_result)

    mock_openai.chat.completions.create.assert_called_once()
    call_kwargs = mock_openai.chat.completions.create.call_args[1]
    assert call_kwargs['model'] == 'gpt-4'


def test_handles_api_error():
    """Test that suggester handles API errors gracefully."""
    with patch('interest_suggester.OpenAI') as mock:
        client = Mock()
        mock.return_value = client
        client.chat.completions.create.side_effect = Exception("API Error")

        suggester = InterestSuggester(api_key="test")
        scan_result = {
            'technologies': ['Python'],
            'todos': []
        }

        suggestions = suggester.suggest(scan_result)

        assert 'learning' in suggestions
        assert 'problem_solving' in suggestions
        assert 'error' in suggestions


def test_formats_todos_correctly(mock_openai):
    """Test that TODOs are formatted correctly in the prompt."""
    suggester = InterestSuggester(api_key="test")
    todos = [
        {'file': 'main.py', 'text': 'fix N+1 query'},
        {'file': 'auth.py', 'text': 'implement OAuth'}
    ]

    formatted = suggester._format_todos(todos)

    assert 'fix N+1 query' in formatted
    assert 'main.py' in formatted
    assert 'implement OAuth' in formatted
    assert 'auth.py' in formatted


def test_format_todos_empty():
    """Test that empty TODOs return 'None'."""
    with patch('interest_suggester.OpenAI'):
        suggester = InterestSuggester(api_key="test")
        formatted = suggester._format_todos([])
        assert formatted == "None"


def test_parse_suggestions_extracts_sections():
    """Test that parse_suggestions correctly extracts learning and problem_solving."""
    with patch('interest_suggester.OpenAI'):
        suggester = InterestSuggester(api_key="test")
        text = '''LEARNING:
- Topic one (reason one)
- Topic two (reason two)

PROBLEM_SOLVING:
- Problem topic (problem reason)'''

        result = suggester._parse_suggestions(text)

        assert len(result['learning']) == 2
        assert len(result['problem_solving']) == 1
        assert result['learning'][0]['topic'] == 'Topic one'
        assert result['learning'][0]['reason'] == 'reason one'
