# AI Content Curator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the AI Article & Video Recommender into an automated content curation system with project scanning, preference learning, and Obsidian integration.

**Architecture:** Multi-page Streamlit app with SQLite database. Cron script for scheduled refreshes. Docker deployment on QNAP NAS with Tailscale for secure remote access. LLM-managed interests with manual override. Per-file Obsidian export for read items.

**Tech Stack:** Python 3.11, Streamlit, SQLite, OpenAI API, feedparser, youtube-search-python, PRAW (Reddit), requests (Stack Overflow API), GitPython, Docker

**Design Doc:** `docs/plans/2025-01-21-content-curator-design.md`

---

## Phase 1: Database Foundation

### Task 1.1: Create Database Schema

**Files:**
- Create: `database.py`
- Create: `tests/test_database.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd /home/andrew/Documents/Python/Git/Medium_youtube/.worktrees/content-curator && source venv/bin/activate && pytest tests/test_database.py -v`
Expected: FAIL with "No module named 'database'"

**Step 3: Write minimal implementation**

```python
# database.py
import sqlite3
from datetime import datetime
from pathlib import Path

class Database:
    def __init__(self, db_path: str = "data/curator.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS interests (
                id INTEGER PRIMARY KEY,
                topic TEXT NOT NULL,
                source TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                skill_level TEXT DEFAULT 'intermediate',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                source_type TEXT NOT NULL,
                source_name TEXT,
                summary TEXT,
                recommendation TEXT,
                relevance_score REAL,
                skill_level TEXT,
                est_read_time INTEGER,
                thumbnail_url TEXT,
                raw_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS saved_items (
                id INTEGER PRIMARY KEY,
                content_id INTEGER NOT NULL REFERENCES content(id),
                status TEXT DEFAULT 'unread',
                notes TEXT,
                synced_to_obsidian BOOLEAN DEFAULT FALSE,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                read_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_actions (
                id INTEGER PRIMARY KEY,
                content_id INTEGER NOT NULL REFERENCES content(id),
                action TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS project_scans (
                id INTEGER PRIMARY KEY,
                source TEXT NOT NULL,
                path TEXT NOT NULL,
                detected_techs TEXT,
                detected_todos TEXT,
                last_scan TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS interest_suggestions (
                id INTEGER PRIMARY KEY,
                topic TEXT NOT NULL,
                reason TEXT,
                source_project_id INTEGER REFERENCES project_scans(id),
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        self.conn.commit()

    def get_tables(self):
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        return [row[0] for row in cursor.fetchall()]

    def close(self):
        self.conn.close()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add database.py tests/test_database.py
git commit -m "feat: add database schema with all tables"
```

---

### Task 1.2: Add Interest CRUD Operations

**Files:**
- Modify: `database.py`
- Modify: `tests/test_database.py`

**Step 1: Write the failing tests**

```python
# Add to tests/test_database.py

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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::test_add_interest -v`
Expected: FAIL with "AttributeError: 'Database' object has no attribute 'add_interest'"

**Step 3: Write minimal implementation**

```python
# Add to database.py Database class

def add_interest(self, topic: str, source: str = "manual", status: str = "active", skill_level: str = "intermediate") -> int:
    cursor = self.conn.execute(
        "INSERT INTO interests (topic, source, status, skill_level) VALUES (?, ?, ?, ?)",
        (topic, source, status, skill_level)
    )
    self.conn.commit()
    return cursor.lastrowid

def get_interests(self, active_only: bool = False) -> list:
    query = "SELECT * FROM interests"
    if active_only:
        query += " WHERE status = 'active'"
    cursor = self.conn.execute(query)
    return [dict(row) for row in cursor.fetchall()]

def update_interest(self, interest_id: int, **kwargs):
    valid_fields = {'topic', 'status', 'skill_level'}
    updates = {k: v for k, v in kwargs.items() if k in valid_fields}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    self.conn.execute(
        f"UPDATE interests SET {set_clause} WHERE id = ?",
        (*updates.values(), interest_id)
    )
    self.conn.commit()

def delete_interest(self, interest_id: int):
    self.conn.execute("DELETE FROM interests WHERE id = ?", (interest_id,))
    self.conn.commit()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add database.py tests/test_database.py
git commit -m "feat: add interest CRUD operations"
```

---

### Task 1.3: Add Content CRUD Operations

**Files:**
- Modify: `database.py`
- Modify: `tests/test_database.py`

**Step 1: Write the failing tests**

```python
# Add to tests/test_database.py

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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::test_add_content -v`
Expected: FAIL with "AttributeError: 'Database' object has no attribute 'add_content'"

**Step 3: Write minimal implementation**

```python
# Add to database.py Database class

def add_content(self, title: str, url: str, source_type: str, source_name: str = None,
                summary: str = None, recommendation: str = None, relevance_score: float = None,
                skill_level: str = None, est_read_time: int = None, thumbnail_url: str = None,
                raw_date: str = None) -> int:
    # Check for existing URL
    existing = self.conn.execute("SELECT id FROM content WHERE url = ?", (url,)).fetchone()
    if existing:
        return existing[0]

    cursor = self.conn.execute('''
        INSERT INTO content (title, url, source_type, source_name, summary, recommendation,
                            relevance_score, skill_level, est_read_time, thumbnail_url, raw_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (title, url, source_type, source_name, summary, recommendation,
          relevance_score, skill_level, est_read_time, thumbnail_url, raw_date))
    self.conn.commit()
    return cursor.lastrowid

def get_content(self, content_id: int) -> dict:
    cursor = self.conn.execute("SELECT * FROM content WHERE id = ?", (content_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

def get_recommended_content(self, source_type: str = None, limit: int = 50) -> list:
    query = "SELECT * FROM content WHERE recommendation = 'RECOMMENDED'"
    params = []
    if source_type:
        query += " AND source_type = ?"
        params.append(source_type)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    cursor = self.conn.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add database.py tests/test_database.py
git commit -m "feat: add content CRUD operations"
```

---

### Task 1.4: Add Saved Items and User Actions

**Files:**
- Modify: `database.py`
- Modify: `tests/test_database.py`

**Step 1: Write the failing tests**

```python
# Add to tests/test_database.py

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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::test_save_item -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# Add to database.py Database class

def save_item(self, content_id: int, notes: str = None) -> int:
    # Check if already saved
    existing = self.conn.execute(
        "SELECT id FROM saved_items WHERE content_id = ?", (content_id,)
    ).fetchone()
    if existing:
        return existing[0]

    cursor = self.conn.execute(
        "INSERT INTO saved_items (content_id, notes) VALUES (?, ?)",
        (content_id, notes)
    )
    self.conn.commit()
    return cursor.lastrowid

def get_saved_items(self, status: str = None) -> list:
    query = '''
        SELECT s.*, c.title, c.url, c.source_type, c.source_name, c.summary, c.thumbnail_url
        FROM saved_items s
        JOIN content c ON s.content_id = c.id
    '''
    params = []
    if status:
        query += " WHERE s.status = ?"
        params.append(status)
    query += " ORDER BY s.saved_at DESC"
    cursor = self.conn.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]

def update_saved_item(self, saved_id: int, **kwargs):
    valid_fields = {'status', 'notes', 'synced_to_obsidian', 'read_at'}
    updates = {k: v for k, v in kwargs.items() if k in valid_fields}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    self.conn.execute(
        f"UPDATE saved_items SET {set_clause} WHERE id = ?",
        (*updates.values(), saved_id)
    )
    self.conn.commit()

def record_action(self, content_id: int, action: str):
    self.conn.execute(
        "INSERT INTO user_actions (content_id, action) VALUES (?, ?)",
        (content_id, action)
    )
    self.conn.commit()

def get_user_actions(self, content_id: int = None) -> list:
    query = "SELECT * FROM user_actions"
    params = []
    if content_id:
        query += " WHERE content_id = ?"
        params.append(content_id)
    query += " ORDER BY timestamp DESC"
    cursor = self.conn.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add database.py tests/test_database.py
git commit -m "feat: add saved items and user actions tracking"
```

---

## Phase 2: Content Sources

### Task 2.1: Refactor Existing Sources into Modules

**Files:**
- Create: `sources/__init__.py`
- Create: `sources/base.py`
- Create: `sources/articles.py`
- Create: `sources/youtube.py`
- Create: `tests/test_sources.py`

**Step 1: Write the failing test**

```python
# tests/test_sources.py
import pytest
from sources.articles import ArticleSource
from sources.youtube import YouTubeSource

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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_sources.py -v`
Expected: FAIL with import error

**Step 3: Write minimal implementation**

```python
# sources/__init__.py
from .articles import ArticleSource
from .youtube import YouTubeSource

__all__ = ['ArticleSource', 'YouTubeSource']
```

```python
# sources/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class ContentSource(ABC):
    @abstractmethod
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Search for content. Returns list of dicts with keys:
        title, url, source_type, source_name, raw_date, description, thumbnail_url (optional)
        """
        pass
```

```python
# sources/articles.py
import feedparser
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from .base import ContentSource

ARTICLE_SOURCES = {
    'Medium': 'https://medium.com/feed/tag/{tag}',
    'Dev.to': 'https://dev.to/feed/tag/{tag}',
    'HackerNoon': 'https://hackernoon.com/tagged/{tag}/feed',
    'Towards Data Science': 'https://towardsdatascience.com/feed',
    'freeCodeCamp': 'https://www.freecodecamp.org/news/rss/',
}

class ArticleSource(ContentSource):
    def search(self, query: str, sources: List[str] = None, limit: int = 5, **kwargs) -> List[Dict[str, Any]]:
        if sources is None:
            sources = list(ARTICLE_SOURCES.keys())

        tag = query.split()[0].lower() if query else 'python'
        results = []

        for source_name in sources:
            if source_name not in ARTICLE_SOURCES:
                continue

            rss_url = ARTICLE_SOURCES[source_name].format(tag=tag)
            try:
                feed = feedparser.parse(rss_url)
                for entry in feed.entries[:limit]:
                    description = BeautifulSoup(
                        entry.get('summary', ''), 'html.parser'
                    ).get_text()[:500]

                    results.append({
                        'title': entry.get('title', 'No title'),
                        'url': entry.get('link', ''),
                        'source_type': 'article',
                        'source_name': source_name,
                        'raw_date': entry.get('published') or entry.get('updated') or '',
                        'description': description,
                    })
            except Exception:
                continue

        return results
```

```python
# sources/youtube.py
from youtubesearchpython import VideosSearch
from typing import List, Dict, Any
from .base import ContentSource

class YouTubeSource(ContentSource):
    def search(self, query: str, limit: int = 5, **kwargs) -> List[Dict[str, Any]]:
        results = []
        try:
            videos = VideosSearch(query, limit=limit)
            for vid in videos.result()['result']:
                thumbnails = vid.get('thumbnails') or []
                thumb_url = thumbnails[0].get('url', '') if thumbnails else ''

                desc_snip = vid.get('descriptionSnippet') or []
                description = ' '.join(str(d.get('text', '')) for d in desc_snip) if desc_snip else ''

                results.append({
                    'title': vid.get('title') or 'No title',
                    'url': vid.get('link') or '',
                    'source_type': 'youtube',
                    'source_name': 'YouTube',
                    'raw_date': vid.get('publishedTime') or '',
                    'description': description,
                    'thumbnail_url': thumb_url,
                })
        except Exception:
            pass

        return results
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_sources.py -v`
Expected: PASS (may skip if no network)

**Step 5: Commit**

```bash
mkdir -p sources tests
git add sources/ tests/test_sources.py
git commit -m "refactor: extract article and youtube sources into modules"
```

---

### Task 2.2: Add Reddit Source

**Files:**
- Create: `sources/reddit.py`
- Modify: `sources/__init__.py`
- Modify: `tests/test_sources.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_sources.py
from sources.reddit import RedditSource

def test_reddit_source_search():
    source = RedditSource()
    results = source.search("python", limit=2)
    assert isinstance(results, list)
    if results:
        assert 'title' in results[0]
        assert 'url' in results[0]
        assert results[0]['source_type'] == 'reddit'
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_sources.py::test_reddit_source_search -v`
Expected: FAIL with import error

**Step 3: Write minimal implementation**

```python
# sources/reddit.py
import requests
from typing import List, Dict, Any
from .base import ContentSource

# Map technologies to relevant subreddits
TECH_SUBREDDITS = {
    'python': ['Python', 'learnpython', 'FastAPI', 'django', 'flask'],
    'javascript': ['javascript', 'node', 'reactjs', 'vuejs', 'typescript'],
    'rust': ['rust', 'learnrust'],
    'go': ['golang'],
    'default': ['programming', 'coding', 'learnprogramming'],
}

class RedditSource(ContentSource):
    def __init__(self):
        self.base_url = "https://www.reddit.com"
        self.headers = {'User-Agent': 'ContentCurator/1.0'}

    def _get_subreddits(self, query: str) -> List[str]:
        query_lower = query.lower()
        for tech, subs in TECH_SUBREDDITS.items():
            if tech in query_lower:
                return subs
        return TECH_SUBREDDITS['default']

    def search(self, query: str, limit: int = 5, min_upvotes: int = 10, **kwargs) -> List[Dict[str, Any]]:
        subreddits = self._get_subreddits(query)
        results = []

        for subreddit in subreddits[:3]:  # Limit subreddits to avoid rate limiting
            try:
                url = f"{self.base_url}/r/{subreddit}/search.json"
                params = {
                    'q': query,
                    'restrict_sr': 'true',
                    'sort': 'relevance',
                    't': 'month',
                    'limit': limit
                }
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                for post in data.get('data', {}).get('children', []):
                    post_data = post.get('data', {})
                    if post_data.get('ups', 0) < min_upvotes:
                        continue

                    results.append({
                        'title': post_data.get('title', 'No title'),
                        'url': f"https://reddit.com{post_data.get('permalink', '')}",
                        'source_type': 'reddit',
                        'source_name': f"r/{subreddit}",
                        'raw_date': '',  # Reddit uses timestamps, handle separately
                        'description': post_data.get('selftext', '')[:500],
                        'upvotes': post_data.get('ups', 0),
                        'num_comments': post_data.get('num_comments', 0),
                    })
            except Exception:
                continue

        return results[:limit]
```

```python
# Update sources/__init__.py
from .articles import ArticleSource
from .youtube import YouTubeSource
from .reddit import RedditSource

__all__ = ['ArticleSource', 'YouTubeSource', 'RedditSource']
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_sources.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add sources/reddit.py sources/__init__.py tests/test_sources.py
git commit -m "feat: add Reddit content source"
```

---

### Task 2.3: Add Stack Overflow Source

**Files:**
- Create: `sources/stackoverflow.py`
- Modify: `sources/__init__.py`
- Modify: `tests/test_sources.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_sources.py
from sources.stackoverflow import StackOverflowSource

def test_stackoverflow_source_search():
    source = StackOverflowSource()
    results = source.search("python async", limit=2)
    assert isinstance(results, list)
    if results:
        assert 'title' in results[0]
        assert 'url' in results[0]
        assert results[0]['source_type'] == 'stackoverflow'
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_sources.py::test_stackoverflow_source_search -v`
Expected: FAIL with import error

**Step 3: Write minimal implementation**

```python
# sources/stackoverflow.py
import requests
from typing import List, Dict, Any
from .base import ContentSource

class StackOverflowSource(ContentSource):
    def __init__(self):
        self.base_url = "https://api.stackexchange.com/2.3"

    def search(self, query: str, limit: int = 5, **kwargs) -> List[Dict[str, Any]]:
        results = []
        try:
            url = f"{self.base_url}/search/advanced"
            params = {
                'order': 'desc',
                'sort': 'relevance',
                'q': query,
                'site': 'stackoverflow',
                'pagesize': limit,
                'filter': 'withbody',
                'accepted': 'True',  # Only questions with accepted answers
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            for item in data.get('items', []):
                results.append({
                    'title': item.get('title', 'No title'),
                    'url': item.get('link', ''),
                    'source_type': 'stackoverflow',
                    'source_name': 'Stack Overflow',
                    'raw_date': '',  # Uses timestamp
                    'description': item.get('body', '')[:500],
                    'score': item.get('score', 0),
                    'answer_count': item.get('answer_count', 0),
                    'tags': item.get('tags', []),
                })
        except Exception:
            pass

        return results
```

```python
# Update sources/__init__.py
from .articles import ArticleSource
from .youtube import YouTubeSource
from .reddit import RedditSource
from .stackoverflow import StackOverflowSource

__all__ = ['ArticleSource', 'YouTubeSource', 'RedditSource', 'StackOverflowSource']
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_sources.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add sources/stackoverflow.py sources/__init__.py tests/test_sources.py
git commit -m "feat: add Stack Overflow content source"
```

---

## Phase 3: AI Enhancements

### Task 3.1: Create Enhanced AI Summarizer

**Files:**
- Create: `ai_summarizer.py`
- Create: `tests/test_ai_summarizer.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ai_summarizer.py -v`
Expected: FAIL with import error

**Step 3: Write minimal implementation**

```python
# ai_summarizer.py
import re
import os
from openai import OpenAI
from typing import Dict, Any, List

class AISummarizer:
    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))

    def summarize(self, title: str, content: str, interests: List[str],
                  content_type: str = "article") -> Dict[str, Any]:
        prompt = f"""Analyze this {content_type} for someone interested in: {', '.join(interests)}

Title: {title}
Content: {content[:1000]}

Provide analysis in this exact format:
Skill level: [Beginner/Intermediate/Advanced]
Est. time: [X min read/watch]
Relevance: [High/Medium/Low] (matches: [which interests])

Summary: [2-3 sentence summary of what this covers]

Verdict: [RECOMMENDED/SKIP] - [one sentence reason]
"""

        try:
            response = self.client.chat.completions.create(
                model='gpt-4',
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.5
            )
            return self._parse_response(response.choices[0].message.content)
        except Exception as e:
            return {
                'skill_level': 'Unknown',
                'est_read_time': None,
                'relevance': 'Unknown',
                'summary': f'Error: {e}',
                'recommendation': 'SKIP',
                'raw_response': str(e)
            }

    def _parse_response(self, text: str) -> Dict[str, Any]:
        result = {
            'skill_level': 'Intermediate',
            'est_read_time': None,
            'relevance': 'Medium',
            'summary': '',
            'recommendation': 'SKIP',
            'raw_response': text
        }

        # Parse skill level
        match = re.search(r'Skill level:\s*(Beginner|Intermediate|Advanced)', text, re.I)
        if match:
            result['skill_level'] = match.group(1)

        # Parse time
        match = re.search(r'Est\. time:\s*(\d+)\s*min', text, re.I)
        if match:
            result['est_read_time'] = int(match.group(1))

        # Parse relevance
        match = re.search(r'Relevance:\s*(High|Medium|Low)', text, re.I)
        if match:
            result['relevance'] = match.group(1)

        # Parse summary
        match = re.search(r'Summary:\s*(.+?)(?=Verdict:|$)', text, re.S)
        if match:
            result['summary'] = match.group(1).strip()

        # Parse recommendation
        if 'RECOMMENDED' in text.upper():
            result['recommendation'] = 'RECOMMENDED'
        else:
            result['recommendation'] = 'SKIP'

        return result
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ai_summarizer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ai_summarizer.py tests/test_ai_summarizer.py
git commit -m "feat: add enhanced AI summarizer with structured output"
```

---

### Task 3.2: Add Deduplication Logic

**Files:**
- Create: `deduplicator.py`
- Create: `tests/test_deduplicator.py`

**Step 1: Write the failing test**

```python
# tests/test_deduplicator.py
import pytest
from deduplicator import Deduplicator

def test_exact_url_match():
    dedup = Deduplicator()
    items = [
        {'title': 'Title A', 'url': 'https://example.com/a'},
        {'title': 'Title B', 'url': 'https://example.com/a'},  # Duplicate
        {'title': 'Title C', 'url': 'https://example.com/c'},
    ]
    result = dedup.deduplicate(items)
    assert len(result) == 2

def test_similar_title_match():
    dedup = Deduplicator()
    items = [
        {'title': 'Introduction to FastAPI', 'url': 'https://a.com'},
        {'title': 'Introduction to FastAPI Tutorial', 'url': 'https://b.com'},
        {'title': 'Something Completely Different', 'url': 'https://c.com'},
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_deduplicator.py -v`
Expected: FAIL with import error

**Step 3: Write minimal implementation**

```python
# deduplicator.py
from difflib import SequenceMatcher
from typing import List, Dict, Any

class Deduplicator:
    def __init__(self, title_threshold: float = 0.85):
        self.title_threshold = title_threshold

    def _normalize_title(self, title: str) -> str:
        return title.lower().strip()

    def _title_similarity(self, title1: str, title2: str) -> float:
        t1 = self._normalize_title(title1)
        t2 = self._normalize_title(title2)
        return SequenceMatcher(None, t1, t2).ratio()

    def _get_score(self, item: Dict[str, Any]) -> float:
        """Get a score for ranking duplicates. Higher is better."""
        score = item.get('score', 0) or 0
        score += item.get('upvotes', 0) or 0
        score += (item.get('relevance_score', 0) or 0) * 10
        return score

    def deduplicate(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not items:
            return []

        seen_urls = set()
        unique_items = []

        # Sort by score descending so we keep the best version
        sorted_items = sorted(items, key=self._get_score, reverse=True)

        for item in sorted_items:
            url = item.get('url', '')
            title = item.get('title', '')

            # Check URL duplicate
            if url in seen_urls:
                continue

            # Check title similarity
            is_duplicate = False
            for existing in unique_items:
                if self._title_similarity(title, existing.get('title', '')) >= self.title_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                seen_urls.add(url)
                unique_items.append(item)

        return unique_items
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_deduplicator.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add deduplicator.py tests/test_deduplicator.py
git commit -m "feat: add content deduplication by URL and title similarity"
```

---

## Phase 4: Project Scanning

### Task 4.1: Create GitHub Project Scanner

**Files:**
- Create: `project_scanner.py`
- Create: `tests/test_project_scanner.py`

**Step 1: Write the failing test**

```python
# tests/test_project_scanner.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from project_scanner import ProjectScanner

def test_detect_python_project():
    scanner = ProjectScanner()
    files = {
        'requirements.txt': 'fastapi==0.100.0\nsqlalchemy==2.0.0',
        'main.py': '# TODO: add authentication\nimport fastapi',
    }

    with patch.object(scanner, '_read_file', side_effect=lambda f: files.get(f, '')):
        with patch.object(scanner, '_list_files', return_value=list(files.keys())):
            result = scanner.scan_local('/fake/path')

    assert 'fastapi' in [t.lower() for t in result['technologies']]
    assert len(result['todos']) >= 1

def test_detect_technologies_from_package_json():
    scanner = ProjectScanner()
    files = {
        'package.json': '{"dependencies": {"react": "^18.0.0", "express": "^4.0.0"}}',
    }

    with patch.object(scanner, '_read_file', side_effect=lambda f: files.get(f, '')):
        with patch.object(scanner, '_list_files', return_value=list(files.keys())):
            result = scanner.scan_local('/fake/path')

    techs_lower = [t.lower() for t in result['technologies']]
    assert 'react' in techs_lower or 'javascript' in techs_lower
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_project_scanner.py -v`
Expected: FAIL with import error

**Step 3: Write minimal implementation**

```python
# project_scanner.py
import os
import re
import json
import tempfile
import subprocess
from typing import Dict, List, Any
from pathlib import Path

class ProjectScanner:
    TODO_PATTERNS = [
        r'#\s*TODO[:\s](.+)',
        r'#\s*FIXME[:\s](.+)',
        r'#\s*HACK[:\s](.+)',
        r'//\s*TODO[:\s](.+)',
        r'//\s*FIXME[:\s](.+)',
    ]

    def __init__(self):
        self.temp_dir = None

    def _read_file(self, filepath: str) -> str:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return ''

    def _list_files(self, directory: str) -> List[str]:
        files = []
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                files.append(os.path.join(root, filename))
        return files

    def scan_github(self, repo_url: str) -> Dict[str, Any]:
        """Clone a GitHub repo and scan it."""
        self.temp_dir = tempfile.mkdtemp()
        try:
            subprocess.run(
                ['git', 'clone', '--depth', '1', repo_url, self.temp_dir],
                check=True, capture_output=True
            )
            return self.scan_local(self.temp_dir)
        except subprocess.CalledProcessError:
            return {'technologies': [], 'todos': [], 'error': 'Failed to clone repository'}
        finally:
            # Cleanup handled by caller or garbage collection
            pass

    def scan_local(self, directory: str) -> Dict[str, Any]:
        """Scan a local directory for technologies and TODOs."""
        technologies = set()
        todos = []

        files = self._list_files(directory)

        # Check for Python
        for f in files:
            if f.endswith('requirements.txt'):
                content = self._read_file(f)
                technologies.add('Python')
                for line in content.split('\n'):
                    if '==' in line:
                        pkg = line.split('==')[0].strip().lower()
                        if pkg in ['fastapi', 'django', 'flask', 'sqlalchemy', 'pytest']:
                            technologies.add(pkg.capitalize())

            if f.endswith('pyproject.toml'):
                technologies.add('Python')

            # Check for JavaScript/Node
            if f.endswith('package.json'):
                content = self._read_file(f)
                technologies.add('JavaScript')
                try:
                    pkg = json.loads(content)
                    deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                    for dep in deps:
                        if dep in ['react', 'vue', 'angular', 'express', 'next', 'typescript']:
                            technologies.add(dep.capitalize())
                except json.JSONDecodeError:
                    pass

            # Check for Rust
            if f.endswith('Cargo.toml'):
                technologies.add('Rust')

            # Check for Go
            if f.endswith('go.mod'):
                technologies.add('Go')

        # Find TODOs
        for f in files:
            if any(f.endswith(ext) for ext in ['.py', '.js', '.ts', '.rs', '.go', '.java']):
                content = self._read_file(f)
                for pattern in self.TODO_PATTERNS:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        todos.append({
                            'file': os.path.basename(f),
                            'text': match.strip()
                        })

        return {
            'technologies': list(technologies),
            'todos': todos[:20],  # Limit to 20 TODOs
        }

    def cleanup(self):
        """Clean up temporary directories."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_project_scanner.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add project_scanner.py tests/test_project_scanner.py
git commit -m "feat: add project scanner for GitHub and local directories"
```

---

### Task 4.2: Add LLM Interest Suggestion

**Files:**
- Create: `interest_suggester.py`
- Create: `tests/test_interest_suggester.py`

**Step 1: Write the failing test**

```python
# tests/test_interest_suggester.py
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
- FastAPI best practices
- SQLAlchemy async patterns
- Python type hints

PROBLEM_SOLVING:
- Database connection pooling (TODO: fix N+1 query)
- Authentication implementation'''

        client.chat.completions.create.return_value = response
        yield client

def test_suggests_learning_topics(mock_openai):
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
    suggester = InterestSuggester(api_key="test")
    scan_result = {'technologies': [], 'todos': []}

    suggestions = suggester.suggest(scan_result)

    assert 'learning' in suggestions
    assert 'problem_solving' in suggestions
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_interest_suggester.py -v`
Expected: FAIL with import error

**Step 3: Write minimal implementation**

```python
# interest_suggester.py
import os
import re
from openai import OpenAI
from typing import Dict, List, Any

class InterestSuggester:
    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))

    def suggest(self, scan_result: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
        technologies = scan_result.get('technologies', [])
        todos = scan_result.get('todos', [])

        if not technologies and not todos:
            return {'learning': [], 'problem_solving': []}

        prompt = f"""Based on this project analysis, suggest content topics:

Technologies detected: {', '.join(technologies) if technologies else 'None'}

TODOs/Problems found:
{self._format_todos(todos)}

Suggest topics in two categories:

LEARNING:
- Topics to learn more about the technologies used (3-5 suggestions)

PROBLEM_SOLVING:
- Topics that would help solve the TODOs (1-3 suggestions based on TODOs)

Format each as a bullet point with a brief reason in parentheses."""

        try:
            response = self.client.chat.completions.create(
                model='gpt-4',
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.7
            )
            return self._parse_suggestions(response.choices[0].message.content)
        except Exception as e:
            return {'learning': [], 'problem_solving': [], 'error': str(e)}

    def _format_todos(self, todos: List[Dict[str, str]]) -> str:
        if not todos:
            return "None"
        return '\n'.join(f"- {t['text']} ({t['file']})" for t in todos[:10])

    def _parse_suggestions(self, text: str) -> Dict[str, List[Dict[str, str]]]:
        result = {'learning': [], 'problem_solving': []}

        current_section = None
        for line in text.split('\n'):
            line = line.strip()

            if 'LEARNING' in line.upper():
                current_section = 'learning'
            elif 'PROBLEM' in line.upper() or 'SOLVING' in line.upper():
                current_section = 'problem_solving'
            elif line.startswith('-') and current_section:
                # Parse "- Topic (reason)" format
                match = re.match(r'-\s*(.+?)(?:\s*\((.+)\))?$', line)
                if match:
                    topic = match.group(1).strip()
                    reason = match.group(2).strip() if match.group(2) else ''
                    result[current_section].append({
                        'topic': topic,
                        'reason': reason
                    })

        return result
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_interest_suggester.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add interest_suggester.py tests/test_interest_suggester.py
git commit -m "feat: add LLM-powered interest suggester from project scans"
```

---

## Phase 5: Obsidian Integration

### Task 5.1: Create Obsidian Exporter

**Files:**
- Create: `obsidian_exporter.py`
- Create: `tests/test_obsidian_exporter.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_obsidian_exporter.py -v`
Expected: FAIL with import error

**Step 3: Write minimal implementation**

```python
# obsidian_exporter.py
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

class ObsidianExporter:
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.curated_folder = self.vault_path / "AI-Curated"

    def _slugify(self, text: str) -> str:
        """Convert text to a safe filename."""
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text[:50].strip('-')

    def _get_date_folder(self) -> Path:
        """Get or create today's folder."""
        date_str = datetime.now().strftime('%Y-%m-%d')
        folder = self.curated_folder / date_str
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def export_item(self, item: Dict[str, Any], notes: str = None) -> str:
        """Export a saved item to Obsidian as a markdown file."""
        folder = self._get_date_folder()

        source_slug = self._slugify(item.get('source_name', 'unknown'))
        title_slug = self._slugify(item.get('title', 'untitled'))
        filename = f"{source_slug}-{title_slug}.md"
        filepath = folder / filename

        content = self._format_content(item, notes)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return str(filepath)

    def _format_content(self, item: Dict[str, Any], notes: str = None) -> str:
        """Format item as Obsidian markdown."""
        title = item.get('title', 'Untitled')
        source = item.get('source_name', 'Unknown')
        url = item.get('url', '')
        summary = item.get('summary', '')
        skill_level = item.get('skill_level', '')
        tags = self._generate_tags(item)

        frontmatter = f"""---
title: "{title}"
source: {source}
url: {url}
saved: {datetime.now().strftime('%Y-%m-%d')}
tags: [{', '.join(tags)}]
skill_level: {skill_level}
---

"""

        body = f"""## AI Summary
{summary}

"""

        if notes:
            body += f"""## Why I saved this
{notes}

"""

        body += """## Key takeaways
(Add your notes after reading)
"""

        return frontmatter + body

    def _generate_tags(self, item: Dict[str, Any]) -> list:
        """Generate tags from item metadata."""
        tags = []

        source_type = item.get('source_type', '')
        if source_type:
            tags.append(source_type)

        # Add source name as tag
        source_name = item.get('source_name', '')
        if source_name:
            tags.append(self._slugify(source_name))

        return tags
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_obsidian_exporter.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add obsidian_exporter.py tests/test_obsidian_exporter.py
git commit -m "feat: add Obsidian markdown exporter"
```

---

## Phase 6: Streamlit UI

### Task 6.1: Convert to Multi-Page App Structure

**Files:**
- Rename: `ai_recommendations_app.py` → `pages/1_Search.py`
- Create: `app.py` (main entry point)
- Create: `pages/__init__.py`

**Step 1: Create main app entry point**

```python
# app.py
import streamlit as st

st.set_page_config(
    page_title='AI Content Curator',
    page_icon='📚',
    layout='wide',
    initial_sidebar_state='expanded'
)

st.title('AI Content Curator')
st.caption('Automated content curation based on your interests and projects.')

st.markdown('''
## Welcome!

Use the sidebar to navigate:

- **Search** - Manual search across all sources
- **My Feed** - AI-curated content based on your interests
- **Interests** - Manage topics and scan projects
- **Reading List** - Saved content and Obsidian sync
- **Settings** - Configure the app
''')

# Initialize database connection in session state
if 'db' not in st.session_state:
    from database import Database
    st.session_state.db = Database()
```

**Step 2: Create pages directory**

```bash
mkdir -p pages
touch pages/__init__.py
```

**Step 3: Move and adapt existing search page**

Copy `ai_recommendations_app.py` to `pages/1_Search.py` and modify the header:

```python
# pages/1_Search.py
# (Keep existing imports and functions)
# Remove st.set_page_config (only in main app.py)

st.header('Search')
st.caption('Search multiple platforms for articles and videos.')

# ... rest of existing code, but use st.session_state.db where needed
```

**Step 4: Verify app runs**

Run: `cd /home/andrew/Documents/Python/Git/Medium_youtube/.worktrees/content-curator && source venv/bin/activate && streamlit run app.py`
Expected: App opens with sidebar navigation

**Step 5: Commit**

```bash
git add app.py pages/
git commit -m "refactor: convert to multi-page Streamlit app structure"
```

---

### Task 6.2: Create My Feed Page

**Files:**
- Create: `pages/2_My_Feed.py`

**Step 1: Write the page**

```python
# pages/2_My_Feed.py
import streamlit as st
from datetime import datetime

st.header('My Feed')

# Ensure database is initialized
if 'db' not in st.session_state:
    from database import Database
    st.session_state.db = Database()

db = st.session_state.db

# Header with refresh button
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    interests = db.get_interests(active_only=True)
    if interests:
        topics = [i['topic'] for i in interests[:5]]
        st.caption(f"Based on: {', '.join(topics)}")
    else:
        st.caption("No interests configured yet")

with col2:
    if st.button('Refresh Now'):
        st.info('Refresh functionality coming soon')

with col3:
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M')}")

# Filter tabs
tab_all, tab_articles, tab_videos, tab_reddit, tab_so = st.tabs([
    'All', 'Articles', 'Videos', 'Reddit', 'Stack Overflow'
])

# Get recommended content
def display_content(source_type=None):
    content = db.get_recommended_content(source_type=source_type, limit=20)

    if not content:
        st.info('No content yet. Add interests and refresh to get recommendations.')
        return

    for item in content:
        with st.container():
            # Relevance badge
            relevance = item.get('relevance_score', 0)
            if relevance and relevance > 0.7:
                st.markdown('**🎯 HIGH MATCH**')

            # Title and source
            st.markdown(f"**{item['title']}** - {item.get('source_name', 'Unknown')}")

            # Metadata
            meta_parts = []
            if item.get('est_read_time'):
                meta_parts.append(f"⏱️ {item['est_read_time']} min")
            if item.get('skill_level'):
                meta_parts.append(item['skill_level'])
            if meta_parts:
                st.caption(' | '.join(meta_parts))

            # Summary
            if item.get('summary'):
                st.write(item['summary'][:200] + '...' if len(item.get('summary', '')) > 200 else item.get('summary', ''))

            # Action buttons
            col_save, col_skip, col_open = st.columns(3)
            with col_save:
                if st.button('Save', key=f"save_{item['id']}"):
                    db.save_item(item['id'])
                    db.record_action(item['id'], 'saved')
                    st.success('Saved!')
            with col_skip:
                if st.button('Skip', key=f"skip_{item['id']}"):
                    db.record_action(item['id'], 'skipped')
                    st.rerun()
            with col_open:
                st.link_button('Open', item['url'])

            st.divider()

with tab_all:
    display_content()

with tab_articles:
    display_content('article')

with tab_videos:
    display_content('youtube')

with tab_reddit:
    display_content('reddit')

with tab_so:
    display_content('stackoverflow')
```

**Step 2: Verify page works**

Run: `streamlit run app.py`
Navigate to "My Feed" page
Expected: Page loads with empty state message

**Step 3: Commit**

```bash
git add pages/2_My_Feed.py
git commit -m "feat: add My Feed page with content display"
```

---

### Task 6.3: Create Interests Page

**Files:**
- Create: `pages/3_Interests.py`

**Step 1: Write the page**

```python
# pages/3_Interests.py
import streamlit as st
from project_scanner import ProjectScanner
from interest_suggester import InterestSuggester
import os

st.header('Interests')

# Ensure database is initialized
if 'db' not in st.session_state:
    from database import Database
    st.session_state.db = Database()

db = st.session_state.db

# Manual interest input
st.subheader('Add Interest')
col_input, col_add = st.columns([3, 1])
with col_input:
    new_topic = st.text_input('Topic', placeholder='e.g., FastAPI, machine learning')
with col_add:
    if st.button('Add', type='primary'):
        if new_topic.strip():
            db.add_interest(new_topic.strip(), source='manual')
            st.success(f'Added: {new_topic}')
            st.rerun()

st.divider()

# Project scanning
st.subheader('Scan Project')
st.caption('Scan a GitHub repo or local folder to get interest suggestions.')

scan_tab_github, scan_tab_local = st.tabs(['GitHub URL', 'Local Folder'])

with scan_tab_github:
    github_url = st.text_input('GitHub Repository URL', placeholder='https://github.com/user/repo')
    if st.button('Scan GitHub'):
        if github_url:
            with st.spinner('Cloning and scanning...'):
                scanner = ProjectScanner()
                try:
                    scan_result = scanner.scan_github(github_url)
                    st.session_state.scan_result = scan_result
                    st.session_state.scan_source = github_url

                    # Get LLM suggestions
                    if os.getenv('OPENAI_API_KEY') or st.secrets.get('OPENAI_API_KEY'):
                        suggester = InterestSuggester()
                        suggestions = suggester.suggest(scan_result)
                        st.session_state.suggestions = suggestions
                finally:
                    scanner.cleanup()

with scan_tab_local:
    local_path = st.text_input('Folder Path', placeholder='/path/to/project')
    if st.button('Scan Local'):
        if local_path and os.path.isdir(local_path):
            with st.spinner('Scanning...'):
                scanner = ProjectScanner()
                scan_result = scanner.scan_local(local_path)
                st.session_state.scan_result = scan_result
                st.session_state.scan_source = local_path

                if os.getenv('OPENAI_API_KEY') or st.secrets.get('OPENAI_API_KEY'):
                    suggester = InterestSuggester()
                    suggestions = suggester.suggest(scan_result)
                    st.session_state.suggestions = suggestions

# Display scan results
if 'scan_result' in st.session_state:
    result = st.session_state.scan_result
    st.success(f"Scanned: {st.session_state.get('scan_source', 'Unknown')}")

    col_tech, col_todos = st.columns(2)
    with col_tech:
        st.markdown('**Technologies detected:**')
        for tech in result.get('technologies', []):
            st.markdown(f"- {tech}")

    with col_todos:
        st.markdown('**TODOs found:**')
        for todo in result.get('todos', [])[:5]:
            st.markdown(f"- {todo['text'][:50]}...")

# Display suggestions
if 'suggestions' in st.session_state:
    suggestions = st.session_state.suggestions

    st.subheader('Suggested Interests')

    if suggestions.get('learning'):
        st.markdown('**Learning Topics:**')
        for item in suggestions['learning']:
            col_topic, col_action = st.columns([3, 1])
            with col_topic:
                st.markdown(f"- {item['topic']}")
                if item.get('reason'):
                    st.caption(item['reason'])
            with col_action:
                if st.button('Add', key=f"add_learn_{item['topic']}"):
                    db.add_interest(item['topic'], source='llm')
                    st.success(f"Added: {item['topic']}")

    if suggestions.get('problem_solving'):
        st.markdown('**Problem-Solving Topics:**')
        for item in suggestions['problem_solving']:
            col_topic, col_action = st.columns([3, 1])
            with col_topic:
                st.markdown(f"- {item['topic']}")
                if item.get('reason'):
                    st.caption(item['reason'])
            with col_action:
                if st.button('Add', key=f"add_prob_{item['topic']}"):
                    db.add_interest(item['topic'], source='llm')
                    st.success(f"Added: {item['topic']}")

st.divider()

# Current interests
st.subheader('Your Interests')
interests = db.get_interests()

if not interests:
    st.info('No interests yet. Add some above!')
else:
    for interest in interests:
        col_name, col_status, col_actions = st.columns([2, 1, 1])
        with col_name:
            badge = '🤖' if interest['source'] == 'llm' else '✏️'
            st.markdown(f"{badge} **{interest['topic']}**")
        with col_status:
            status = interest['status']
            if status == 'active':
                st.success('Active')
            else:
                st.warning('Paused')
        with col_actions:
            if interest['status'] == 'active':
                if st.button('Pause', key=f"pause_{interest['id']}"):
                    db.update_interest(interest['id'], status='paused')
                    st.rerun()
            else:
                if st.button('Activate', key=f"activate_{interest['id']}"):
                    db.update_interest(interest['id'], status='active')
                    st.rerun()
            if st.button('Delete', key=f"delete_{interest['id']}"):
                db.delete_interest(interest['id'])
                st.rerun()
```

**Step 2: Verify page works**

Run: `streamlit run app.py`
Navigate to "Interests" page
Expected: Page loads with interest management UI

**Step 3: Commit**

```bash
git add pages/3_Interests.py
git commit -m "feat: add Interests page with project scanning"
```

---

### Task 6.4: Create Reading List Page

**Files:**
- Create: `pages/4_Reading_List.py`

**Step 1: Write the page**

```python
# pages/4_Reading_List.py
import streamlit as st
from obsidian_exporter import ObsidianExporter
from datetime import datetime

st.header('Reading List')

# Ensure database is initialized
if 'db' not in st.session_state:
    from database import Database
    st.session_state.db = Database()

db = st.session_state.db

# Status tabs
tab_unread, tab_reading, tab_read, tab_archived = st.tabs([
    'Unread', 'Reading', 'Read', 'Archived'
])

def display_saved_items(status):
    items = db.get_saved_items(status=status)

    if not items:
        st.info(f'No {status} items.')
        return

    for item in items:
        with st.container():
            # Thumbnail if available
            col_thumb, col_content = st.columns([1, 3])

            with col_thumb:
                if item.get('thumbnail_url'):
                    st.image(item['thumbnail_url'], width=120)

            with col_content:
                st.markdown(f"**{item['title']}**")
                st.caption(f"{item.get('source_name', 'Unknown')} | Saved: {item['saved_at'][:10]}")

                if item.get('summary'):
                    st.write(item['summary'][:150] + '...')

                # Action buttons based on status
                cols = st.columns(4)

                with cols[0]:
                    st.link_button('Open', item['url'])

                with cols[1]:
                    if status == 'unread':
                        if st.button('Start Reading', key=f"start_{item['id']}"):
                            db.update_saved_item(item['id'], status='reading')
                            st.rerun()
                    elif status == 'reading':
                        if st.button('Mark Read', key=f"read_{item['id']}"):
                            db.update_saved_item(item['id'], status='read', read_at=datetime.now().isoformat())
                            st.rerun()
                    elif status == 'read':
                        if not item.get('synced_to_obsidian'):
                            if st.button('Sync to Obsidian', key=f"sync_{item['id']}"):
                                vault_path = st.session_state.get('obsidian_vault', '/obsidian')
                                exporter = ObsidianExporter(vault_path)
                                filepath = exporter.export_item(item, item.get('notes'))
                                db.update_saved_item(item['id'], synced_to_obsidian=True)
                                st.success(f'Exported to: {filepath}')
                        else:
                            st.caption('✅ Synced')

                with cols[2]:
                    if status != 'archived':
                        if st.button('Archive', key=f"archive_{item['id']}"):
                            db.update_saved_item(item['id'], status='archived')
                            st.rerun()

                with cols[3]:
                    if status == 'archived':
                        if st.button('Restore', key=f"restore_{item['id']}"):
                            db.update_saved_item(item['id'], status='unread')
                            st.rerun()

            st.divider()

with tab_unread:
    display_saved_items('unread')

with tab_reading:
    display_saved_items('reading')

with tab_read:
    # Bulk sync option
    read_items = db.get_saved_items(status='read')
    unsynced = [i for i in read_items if not i.get('synced_to_obsidian')]
    if unsynced:
        if st.button(f'Sync All to Obsidian ({len(unsynced)} items)'):
            vault_path = st.session_state.get('obsidian_vault', '/obsidian')
            exporter = ObsidianExporter(vault_path)
            for item in unsynced:
                exporter.export_item(item, item.get('notes'))
                db.update_saved_item(item['id'], synced_to_obsidian=True)
            st.success(f'Exported {len(unsynced)} items!')
            st.rerun()

    display_saved_items('read')

with tab_archived:
    display_saved_items('archived')
```

**Step 2: Verify page works**

Run: `streamlit run app.py`
Navigate to "Reading List" page
Expected: Page loads with reading list UI

**Step 3: Commit**

```bash
git add pages/4_Reading_List.py
git commit -m "feat: add Reading List page with Obsidian sync"
```

---

### Task 6.5: Create Settings Page

**Files:**
- Create: `pages/5_Settings.py`

**Step 1: Write the page**

```python
# pages/5_Settings.py
import streamlit as st
import os

st.header('Settings')

# Obsidian settings
st.subheader('Obsidian Integration')
vault_path = st.text_input(
    'Obsidian Vault Path',
    value=st.session_state.get('obsidian_vault', '/obsidian'),
    help='Path to your Obsidian vault folder'
)
if st.button('Save Vault Path'):
    st.session_state.obsidian_vault = vault_path
    st.success('Saved!')

st.divider()

# API Keys status
st.subheader('API Configuration')
openai_key = os.getenv('OPENAI_API_KEY') or st.secrets.get('OPENAI_API_KEY', '')
github_token = os.getenv('GITHUB_TOKEN') or st.secrets.get('GITHUB_TOKEN', '')

col1, col2 = st.columns(2)
with col1:
    if openai_key:
        st.success('OpenAI API Key: Configured ✓')
    else:
        st.warning('OpenAI API Key: Not set')
        st.caption('Set OPENAI_API_KEY environment variable')

with col2:
    if github_token:
        st.success('GitHub Token: Configured ✓')
    else:
        st.info('GitHub Token: Not set (optional)')
        st.caption('Needed for private repos')

st.divider()

# Export/Import
st.subheader('Data Management')

if 'db' not in st.session_state:
    from database import Database
    st.session_state.db = Database()

db = st.session_state.db

col_export, col_import = st.columns(2)

with col_export:
    st.markdown('**Export Interests**')
    interests = db.get_interests()
    if interests:
        import json
        export_data = json.dumps([{'topic': i['topic'], 'source': i['source']} for i in interests], indent=2)
        st.download_button(
            'Download JSON',
            export_data,
            file_name='interests.json',
            mime='application/json'
        )

with col_import:
    st.markdown('**Import Interests**')
    uploaded = st.file_uploader('Upload JSON', type='json')
    if uploaded:
        import json
        try:
            data = json.load(uploaded)
            for item in data:
                db.add_interest(item['topic'], source=item.get('source', 'manual'))
            st.success(f'Imported {len(data)} interests!')
        except Exception as e:
            st.error(f'Error: {e}')

st.divider()

# Stats
st.subheader('Statistics')
interests = db.get_interests()
content = db.get_recommended_content(limit=1000)
saved = db.get_saved_items()

col_stat1, col_stat2, col_stat3 = st.columns(3)
with col_stat1:
    st.metric('Active Interests', len([i for i in interests if i['status'] == 'active']))
with col_stat2:
    st.metric('Content Found', len(content))
with col_stat3:
    st.metric('Saved Items', len(saved))
```

**Step 2: Verify page works**

Run: `streamlit run app.py`
Navigate to "Settings" page
Expected: Page loads with settings UI

**Step 3: Commit**

```bash
git add pages/5_Settings.py
git commit -m "feat: add Settings page"
```

---

## Phase 7: Cron Refresh Script

### Task 7.1: Create Cron Refresh Script

**Files:**
- Create: `cron_refresh.py`

**Step 1: Write the script**

```python
#!/usr/bin/env python3
# cron_refresh.py
"""
Automated content refresh script.
Run via cron: 0 6,18 * * * cd /app && python cron_refresh.py >> /var/log/cron.log 2>&1
"""

import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting content refresh...")

    # Import here to avoid loading everything at module level
    from database import Database
    from sources import ArticleSource, YouTubeSource, RedditSource, StackOverflowSource
    from ai_summarizer import AISummarizer
    from deduplicator import Deduplicator

    db = Database()
    summarizer = AISummarizer()
    deduplicator = Deduplicator()

    # Get active interests
    interests = db.get_interests(active_only=True)
    if not interests:
        logger.info("No active interests. Skipping refresh.")
        return

    topics = [i['topic'] for i in interests]
    logger.info(f"Refreshing content for {len(topics)} interests: {', '.join(topics)}")

    # Initialize sources
    sources = [
        ('articles', ArticleSource()),
        ('youtube', YouTubeSource()),
        ('reddit', RedditSource()),
        ('stackoverflow', StackOverflowSource()),
    ]

    all_content = []

    # Search each interest
    for topic in topics:
        logger.info(f"Searching for: {topic}")

        for source_name, source in sources:
            try:
                results = source.search(topic, limit=5)
                logger.info(f"  {source_name}: {len(results)} results")

                for item in results:
                    # Get AI summary
                    summary_result = summarizer.summarize(
                        title=item.get('title', ''),
                        content=item.get('description', ''),
                        interests=topics,
                        content_type=item.get('source_type', 'article')
                    )

                    item['summary'] = summary_result.get('summary', '')
                    item['recommendation'] = summary_result.get('recommendation', 'SKIP')
                    item['skill_level'] = summary_result.get('skill_level')
                    item['est_read_time'] = summary_result.get('est_read_time')
                    item['relevance_score'] = 1.0 if summary_result.get('relevance') == 'High' else 0.5

                    all_content.append(item)

            except Exception as e:
                logger.error(f"  {source_name} error: {e}")

    # Deduplicate
    logger.info(f"Total content before dedup: {len(all_content)}")
    unique_content = deduplicator.deduplicate(all_content)
    logger.info(f"Total content after dedup: {len(unique_content)}")

    # Save recommended content
    saved_count = 0
    for item in unique_content:
        if item.get('recommendation') == 'RECOMMENDED':
            try:
                db.add_content(
                    title=item.get('title', 'Untitled'),
                    url=item.get('url', ''),
                    source_type=item.get('source_type', 'article'),
                    source_name=item.get('source_name'),
                    summary=item.get('summary'),
                    recommendation=item.get('recommendation'),
                    relevance_score=item.get('relevance_score'),
                    skill_level=item.get('skill_level'),
                    est_read_time=item.get('est_read_time'),
                    thumbnail_url=item.get('thumbnail_url'),
                    raw_date=item.get('raw_date')
                )
                saved_count += 1
            except Exception as e:
                logger.error(f"Error saving content: {e}")

    logger.info(f"Saved {saved_count} recommended items to database")
    logger.info("Content refresh complete!")

    db.close()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"Refresh failed: {e}")
        sys.exit(1)
```

**Step 2: Test the script**

Run: `cd /home/andrew/Documents/Python/Git/Medium_youtube/.worktrees/content-curator && source venv/bin/activate && python cron_refresh.py`
Expected: Script runs and logs output (may error if no interests set)

**Step 3: Commit**

```bash
chmod +x cron_refresh.py
git add cron_refresh.py
git commit -m "feat: add cron refresh script for automated content updates"
```

---

## Phase 8: Docker Deployment

### Task 8.1: Create Docker Configuration

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `crontab`
- Update: `requirements.txt`

**Step 1: Update requirements.txt**

```txt
# requirements.txt
streamlit>=1.28.0
feedparser>=6.0.0
beautifulsoup4>=4.12.0
youtube-search-python>=1.6.0
openai>=1.0.0
requests>=2.31.0
gitpython>=3.1.0
```

**Step 2: Create Dockerfile**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Setup cron
COPY crontab /etc/cron.d/refresh-cron
RUN chmod 0644 /etc/cron.d/refresh-cron && \
    crontab /etc/cron.d/refresh-cron && \
    touch /var/log/cron.log

# Expose Streamlit port
EXPOSE 8501

# Start script
COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
```

**Step 3: Create start.sh**

```bash
#!/bin/bash
# start.sh

# Start cron in background
cron

# Start Streamlit
exec streamlit run app.py \
    --server.address=0.0.0.0 \
    --server.port=8501 \
    --server.headless=true
```

**Step 4: Create crontab**

```
# crontab
# Run content refresh at 6am and 6pm
0 6,18 * * * cd /app && /usr/local/bin/python cron_refresh.py >> /var/log/cron.log 2>&1
# Empty line required
```

**Step 5: Create docker-compose.yml**

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    container_name: content-curator
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
      - ${OBSIDIAN_VAULT:-/share/Obsidian}:/obsidian
      - ${PROJECTS_PATH:-/share/Projects}:/projects
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GITHUB_TOKEN=${GITHUB_TOKEN:-}
    restart: unless-stopped

  # Optional: Tailscale sidecar
  # tailscale:
  #   image: tailscale/tailscale:latest
  #   hostname: content-curator
  #   environment:
  #     - TS_AUTHKEY=${TS_AUTHKEY}
  #     - TS_STATE_DIR=/var/lib/tailscale
  #   volumes:
  #     - tailscale-state:/var/lib/tailscale
  #   cap_add:
  #     - NET_ADMIN
  #   restart: unless-stopped

# volumes:
#   tailscale-state:
```

**Step 6: Commit**

```bash
git add Dockerfile docker-compose.yml crontab start.sh requirements.txt
git commit -m "feat: add Docker deployment configuration"
```

---

## Phase 9: Final Integration

### Task 9.1: Integration Testing

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write integration test**

```python
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
    """Test: Add interest → Search → Summarize → Save → Display"""
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
    """Test: Scan project → Get suggestions"""
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
    """Test: Save item → Export to Obsidian"""
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
```

**Step 2: Run integration tests**

Run: `pytest tests/test_integration.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for full content curation flow"
```

---

### Task 9.2: Final Documentation Update

**Files:**
- Update: `README.md`

**Step 1: Update README**

```markdown
# AI Content Curator

Automated content curation based on your interests and projects. Searches articles, YouTube, Reddit, and Stack Overflow, uses AI to summarize and recommend, and syncs to Obsidian.

## Features

- **Multi-source search**: Medium, Dev.to, HackerNoon, YouTube, Reddit, Stack Overflow
- **Project scanning**: Analyze GitHub repos to suggest relevant topics
- **AI summaries**: GPT-4 powered summaries with skill level and time estimates
- **Preference learning**: Improves recommendations based on your actions
- **Obsidian sync**: Export read items to your knowledge base
- **Automated refresh**: Cron-based content updates

## Quick Start

### Local Development

```bash
# Clone and setup
git clone <repo>
cd content-curator
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="sk-..."

# Run
streamlit run app.py
```

### Docker (QNAP NAS)

```bash
# Create .env file
echo "OPENAI_API_KEY=sk-..." > .env
echo "OBSIDIAN_VAULT=/share/Obsidian" >> .env

# Build and run
docker-compose up -d
```

Access at `http://your-nas-ip:8501`

### Tailscale Setup

1. Install Tailscale on NAS and phone
2. Access via Tailscale IP: `http://100.x.x.x:8501`

## Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 | Yes |
| `GITHUB_TOKEN` | GitHub token for private repos | No |
| `OBSIDIAN_VAULT` | Path to Obsidian vault | No |

## Architecture

See `docs/plans/2025-01-21-content-curator-design.md` for full design document.

## Development

```bash
# Run tests
pytest -v

# Run specific test
pytest tests/test_database.py -v
```
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README with full setup instructions"
```

---

## Summary

**Total Tasks: 19**

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | 4 | Database foundation |
| 2 | 3 | Content sources (refactor + Reddit + SO) |
| 3 | 2 | AI enhancements (summarizer + dedup) |
| 4 | 2 | Project scanning |
| 5 | 1 | Obsidian integration |
| 6 | 5 | Streamlit UI pages |
| 7 | 1 | Cron refresh script |
| 8 | 1 | Docker deployment |
| 9 | 2 | Integration testing + docs |

**Estimated commits: ~19 atomic commits**

---

Plan complete and saved to `docs/plans/2025-01-21-content-curator-implementation.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new Claude Code session in the worktree, batch execution with checkpoints

Which approach?
