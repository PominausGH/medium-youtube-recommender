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
