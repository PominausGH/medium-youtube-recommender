# tests/test_ai_summarizer.py
import pytest
from unittest.mock import Mock, patch
from ai_summarizer import AISummarizer


@pytest.fixture
def mock_openai():
    with patch('ai_summarizer.OpenAI') as mock:
        client = Mock()
        mock.return_value = client

        response = Mock()
        response.choices = [Mock()]
        response.choices[0].message.content = '''Skill level: Intermediate
Est. time: 8 min read
Relevance: High

Summary: This article covers FastAPI async patterns.

Verdict: RECOMMENDED - directly relevant'''

        client.chat.completions.create.return_value = response
        yield client


def test_summarizer_returns_enhanced_format(mock_openai):
    summarizer = AISummarizer(api_key="test")
    result = summarizer.summarize(
        title="FastAPI Async Patterns",
        content="Article about async...",
        interests=["FastAPI", "Python"]
    )
    assert 'skill_level' in result
    assert 'est_read_time' in result
    assert 'summary' in result
    assert 'recommendation' in result


def test_summarizer_parses_recommendation(mock_openai):
    summarizer = AISummarizer(api_key="test")
    result = summarizer.summarize(
        title="Test",
        content="Test content",
        interests=["Python"]
    )
    assert result['recommendation'] in ['RECOMMENDED', 'SKIP']


def test_summarizer_parses_skill_level(mock_openai):
    summarizer = AISummarizer(api_key="test")
    result = summarizer.summarize(
        title="Test",
        content="Test content",
        interests=["Python"]
    )
    assert result['skill_level'] == 'Intermediate'


def test_summarizer_parses_read_time(mock_openai):
    summarizer = AISummarizer(api_key="test")
    result = summarizer.summarize(
        title="Test",
        content="Test content",
        interests=["Python"]
    )
    assert result['est_read_time'] == 8


def test_summarizer_parses_relevance(mock_openai):
    summarizer = AISummarizer(api_key="test")
    result = summarizer.summarize(
        title="Test",
        content="Test content",
        interests=["Python"]
    )
    assert result['relevance'] == 'High'


def test_summarizer_parses_summary_text(mock_openai):
    summarizer = AISummarizer(api_key="test")
    result = summarizer.summarize(
        title="Test",
        content="Test content",
        interests=["Python"]
    )
    assert 'FastAPI async patterns' in result['summary']


def test_summarizer_handles_skip_verdict():
    with patch('ai_summarizer.OpenAI') as mock:
        client = Mock()
        mock.return_value = client

        response = Mock()
        response.choices = [Mock()]
        response.choices[0].message.content = '''Skill level: Beginner
Est. time: 5 min read
Relevance: Low

Summary: Basic introduction to programming.

Verdict: SKIP - not relevant to interests'''

        client.chat.completions.create.return_value = response

        summarizer = AISummarizer(api_key="test")
        result = summarizer.summarize(
            title="Intro to Programming",
            content="Basic content...",
            interests=["Advanced Python"]
        )
        assert result['recommendation'] == 'SKIP'
        assert result['relevance'] == 'Low'


def test_summarizer_handles_api_error():
    with patch('ai_summarizer.OpenAI') as mock:
        client = Mock()
        mock.return_value = client
        client.chat.completions.create.side_effect = Exception("API Error")

        summarizer = AISummarizer(api_key="test")
        result = summarizer.summarize(
            title="Test",
            content="Test content",
            interests=["Python"]
        )
        assert result['recommendation'] == 'SKIP'
        assert 'Error' in result['summary']


def test_summarizer_uses_correct_prompt(mock_openai):
    summarizer = AISummarizer(api_key="test")
    summarizer.summarize(
        title="Test Title",
        content="Test content here",
        interests=["Python", "FastAPI"],
        content_type="video"
    )

    # Verify the call was made with expected prompt elements
    call_args = mock_openai.chat.completions.create.call_args
    messages = call_args.kwargs['messages']
    prompt = messages[0]['content']

    assert 'video' in prompt
    assert 'Python' in prompt
    assert 'FastAPI' in prompt
    assert 'Test Title' in prompt
