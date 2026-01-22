import pytest
from sources.articles import ArticleSource
from sources.youtube import YouTubeSource
from sources.reddit import RedditSource
from sources.stackoverflow import StackOverflowSource


def test_article_source_search():
    source = ArticleSource()
    results = source.search("python", sources=["Dev.to"], limit=2)
    assert isinstance(results, list)
    # Results may be empty if network fails, but structure should be correct
    if results:
        assert 'title' in results[0]
        assert 'url' in results[0]
        assert 'source_type' in results[0]


def test_youtube_source_search():
    source = YouTubeSource()
    results = source.search("python tutorial", limit=2)
    assert isinstance(results, list)
    if results:
        assert 'title' in results[0]
        assert 'url' in results[0]
        assert 'source_type' in results[0]


def test_reddit_source_search():
    source = RedditSource()
    results = source.search("python", limit=2)
    assert isinstance(results, list)
    if results:
        assert 'title' in results[0]
        assert 'url' in results[0]
        assert results[0]['source_type'] == 'reddit'


def test_stackoverflow_source_search():
    source = StackOverflowSource()
    results = source.search("python async", limit=2)
    assert isinstance(results, list)
    if results:
        assert 'title' in results[0]
        assert 'url' in results[0]
        assert results[0]['source_type'] == 'stackoverflow'
