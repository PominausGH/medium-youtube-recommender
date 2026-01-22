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

    def close(self):
        self.conn.close()
