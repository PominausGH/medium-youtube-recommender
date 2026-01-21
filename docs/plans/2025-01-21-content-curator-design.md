# AI Content Curator - Design Document

## Overview

Expand the existing AI Article & Video Recommender into an automated content curation system that learns your interests, scans your projects, and builds a personalized reading/watch list.

## Goals

- Automate content discovery based on interests and current work
- Learn preferences over time to improve recommendations
- Provide mobile access to curated content
- Sync valuable content to Obsidian for knowledge management

## Architecture

### Infrastructure

```
QNAP NAS (Docker)
├── streamlit-app container
│   ├── Streamlit app (port 8501)
│   ├── SQLite database (mounted volume)
│   └── Cron job (inside container)
├── tailscale container
│
├── /share/Obsidian/       ← Vault folder (mounted)
└── /share/Projects/       ← Local projects (mounted)

Access:
  Phone  ──┐
           ├── Tailscale ──→ NAS:8501
  Laptop ──┘
```

### Key Decisions

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Hosting | QNAP NAS + Docker | Always-on, local data, direct Obsidian access |
| Remote Access | Tailscale | Secure, no public exposure, works on phone |
| Database | SQLite | Simple, no setup, sufficient for single-user |
| Scheduling | Cron (6am/6pm) | Bi-daily refresh, content ready in morning |
| Project Scanning | GitHub URL + local folders | Flexible, works remotely and locally |
| Obsidian | Per-file export on "Read" | Clean vault, only confirmed valuable content |

## Database Schema

```sql
-- Topics the user is interested in
CREATE TABLE interests (
    id INTEGER PRIMARY KEY,
    topic TEXT NOT NULL,
    source TEXT NOT NULL,           -- 'manual' | 'llm'
    status TEXT DEFAULT 'active',   -- 'active' | 'paused'
    skill_level TEXT DEFAULT 'intermediate',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- All discovered content
CREATE TABLE content (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    source_type TEXT NOT NULL,      -- 'medium' | 'devto' | 'youtube' | 'reddit' | 'stackoverflow'
    source_name TEXT,               -- e.g., 'r/Python', 'Dev.to'
    summary TEXT,
    recommendation TEXT,            -- 'RECOMMENDED' | 'SKIP'
    relevance_score REAL,
    skill_level TEXT,
    est_read_time INTEGER,          -- minutes
    thumbnail_url TEXT,
    raw_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User's saved reading list
CREATE TABLE saved_items (
    id INTEGER PRIMARY KEY,
    content_id INTEGER NOT NULL REFERENCES content(id),
    status TEXT DEFAULT 'unread',   -- 'unread' | 'reading' | 'read' | 'archived'
    notes TEXT,
    synced_to_obsidian BOOLEAN DEFAULT FALSE,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP
);

-- Track user behavior for preference learning
CREATE TABLE user_actions (
    id INTEGER PRIMARY KEY,
    content_id INTEGER NOT NULL REFERENCES content(id),
    action TEXT NOT NULL,           -- 'clicked' | 'saved' | 'skipped' | 'read'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scanned projects for context
CREATE TABLE project_scans (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,           -- 'github' | 'local'
    path TEXT NOT NULL,             -- URL or folder path
    detected_techs TEXT,            -- JSON array
    detected_todos TEXT,            -- JSON array
    last_scan TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Suggested interests pending approval
CREATE TABLE interest_suggestions (
    id INTEGER PRIMARY KEY,
    topic TEXT NOT NULL,
    reason TEXT,                    -- Why LLM suggested this
    source_project_id INTEGER REFERENCES project_scans(id),
    status TEXT DEFAULT 'pending',  -- 'pending' | 'approved' | 'dismissed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Content Sources

### Existing (keep as-is)
- Medium (RSS)
- Dev.to (RSS)
- HackerNoon (RSS)
- Towards Data Science (RSS)
- freeCodeCamp (RSS)
- YouTube (youtube-search-python)

### New Sources

**Reddit**
- Auto-map tech stack to subreddits:
  - Python → r/Python, r/learnpython, r/FastAPI
  - JavaScript → r/javascript, r/node, r/reactjs
  - General → r/programming, r/coding
- Use Reddit JSON API (append `.json` to URL, no auth needed)
- Filter: upvotes > threshold (configurable)

**Stack Overflow**
- Tag-based search: Match interests as tags
- Error-matching: Search for detected TODOs/errors
- Use Stack Exchange API (300 requests/day free)

### Deferred
- Podcasts (ListenNotes API) - add in future version

## AI Features

### Enhanced Summaries

Current format:
```
2-line summary. RECOMMENDED/SKIP
```

New format:
```
Skill level: Intermediate
Est. time: 8 min read
Relevance: High (matches: FastAPI, async Python)

Summary: Covers async database connections in FastAPI using
SQLAlchemy 2.0. Explains connection pooling and session management.

Verdict: RECOMMENDED - directly relevant to your current project
```

### Preference Learning

Track signals:
| Action | Signal Strength |
|--------|-----------------|
| Clicked | Mild positive |
| Saved | Strong positive |
| Marked as read | Confirmed valuable |
| Skipped/dismissed | Negative |

Learn over time:
- Preferred sources (you click Dev.to more than Medium)
- Preferred content length
- Preferred authors/channels
- Per-topic skill level adjustment

### Deduplication

Before displaying content:
1. URL matching (exact duplicates)
2. Title similarity (fuzzy match > 85%)
3. LLM semantic check for same-topic content

Group duplicates, show best one (highest engagement or preferred source).

## Project Scanning

### Flow

1. User enters GitHub repo URL or selects local folder
2. App clones/accesses the project
3. LLM analyzes key files:
   - `requirements.txt`, `package.json`, `Cargo.toml` → dependencies
   - File extensions → languages
   - `README.md` → project purpose
   - Comments with `TODO`, `FIXME`, `HACK` → problems
   - Recent git commits → active work areas
4. Generates two types of suggestions:
   - **Learning**: "You're using FastAPI - want content on this?"
   - **Problem-solving**: "Found TODO about N+1 queries - want optimization articles?"
5. Suggestions appear in Interests page for approval

### Triggers
- Manual "Scan project" button
- Re-scan when repo has new commits (check periodically)

## Streamlit UI

### Page 1: Search (existing, minor updates)
- Keep current manual search
- Add "Save to reading list" button
- Add source icons

### Page 2: My Feed

```
┌─────────────────────────────────────────────────────┐
│ My Feed                    [Refresh Now] [Settings] │
│ Last updated: 2 hours ago                           │
├─────────────────────────────────────────────────────┤
│ Based on: FastAPI, SQLAlchemy, async Python         │
│ From project: github.com/you/your-api               │
├─────────────────────────────────────────────────────┤
│ [All] [Articles] [Videos] [Reddit] [Stack Overflow] │
├─────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────┐ │
│ │ HIGH MATCH                                      │ │
│ │ FastAPI Async Patterns - Dev.to                 │ │
│ │ 8 min | Intermediate                            │ │
│ │ Summary here...                                 │ │
│ │ [Save] [Skip] [Open]                            │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Page 3: Interests

- LLM suggestions with approve/dismiss buttons
- Manual "Add topic" input
- Active interests list with pause/delete
- "Scan project" button
- GitHub URL input / local folder selector

### Page 4: Reading List

- Tabs: Unread | Reading | Read | Archived
- Filter by source, date, topic
- Bulk actions: Mark read, sync to Obsidian
- Obsidian vault path setting

### Page 5: Settings

- GitHub token (for private repos)
- Obsidian vault path
- Subreddit preferences
- Notification preferences
- API usage stats
- Export/import interests as JSON

## Obsidian Integration

### Sync Trigger
Items sync to Obsidian when marked as "Read" (confirmed valuable).

### File Structure
```
Vault/
  AI-Curated/
    2025-01-21/
      devto-fastapi-async-patterns.md
      youtube-sqlalchemy-tutorial.md
    2025-01-22/
      ...
```

### File Format
```markdown
---
title: "FastAPI Async Database Patterns"
source: Dev.to
url: https://dev.to/...
saved: 2025-01-21
tags: [fastapi, sqlalchemy, async]
skill_level: intermediate
---

## AI Summary
Covers async database connections in FastAPI using SQLAlchemy 2.0...

## Why I saved this
(User's notes - optional)

## Key takeaways
(User can add after reading)
```

## Scheduling

### Cron Configuration
```bash
# Runs at 6am and 6pm daily
0 6,18 * * * cd /app && python cron_refresh.py >> /var/log/cron.log 2>&1
```

### Refresh Script (`cron_refresh.py`)
```
1. Load active interests from database
2. For each interest:
   a. Search all sources
   b. AI summarize & score
   c. Deduplicate against existing content
   d. Save new RECOMMENDED items
3. Check scanned projects for new commits
4. Re-scan if changes detected
5. Update preference model scores
6. Log results
```

### Rate Limiting
- Stagger API calls (avoid bursts)
- Cache results for 6 hours
- Track usage per source in database

## Docker Deployment

### docker-compose.yml
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data                    # SQLite database
      - /share/Obsidian:/obsidian           # Obsidian vault
      - /share/Projects:/projects           # Local projects
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
    restart: unless-stopped

  tailscale:
    image: tailscale/tailscale:latest
    hostname: content-curator
    environment:
      - TS_AUTHKEY=${TS_AUTHKEY}
      - TS_STATE_DIR=/var/lib/tailscale
    volumes:
      - tailscale-state:/var/lib/tailscale
    cap_add:
      - NET_ADMIN
    restart: unless-stopped

volumes:
  tailscale-state:
```

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Install cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# Add cron job
COPY crontab /etc/cron.d/refresh-cron
RUN chmod 0644 /etc/cron.d/refresh-cron && crontab /etc/cron.d/refresh-cron

# Start cron and streamlit
CMD cron && streamlit run app.py --server.address=0.0.0.0
```

## Error Handling

| Error | Handling |
|-------|----------|
| API rate limit | Queue and retry, show partial results |
| GitHub URL invalid | Clear error message, suggest format |
| LLM failure | Fall back to basic keyword matching |
| Database locked | Retry with exponential backoff |
| Network timeout | Retry 3x, then skip source for this run |

## Security

- Tailscale: No public exposure, authenticated mesh network
- GitHub token: Stored in environment variable, not in code
- OpenAI API key: Stored in environment variable
- No sensitive data logged

## Future Enhancements (out of scope for v1)

- Podcasts via ListenNotes API
- Desktop/mobile notifications for high-match content
- Browser extension to save external content
- Team sharing / multi-user support
- Postgres option for larger scale
- Full-text search across saved content

## Success Criteria

- [ ] Can add interests manually and via LLM suggestions
- [ ] Can scan GitHub repos and get relevant suggestions
- [ ] Content refreshes automatically twice daily
- [ ] Can access feed from phone via Tailscale
- [ ] Saved "Read" items appear in Obsidian vault
- [ ] Recommendations improve over time based on usage
