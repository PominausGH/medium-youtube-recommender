# obsidian_exporter.py
"""Export curated content items to Obsidian vault as markdown notes."""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class ObsidianExporter:
    """Exports curated content items to an Obsidian vault."""

    def __init__(self, vault_path: str):
        """
        Initialize the Obsidian exporter.

        Args:
            vault_path: Path to the Obsidian vault root directory.
        """
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

    def export_item(self, item: Dict[str, Any], notes: Optional[str] = None) -> str:
        """
        Export a saved item to Obsidian as a markdown file.

        Args:
            item: Dictionary containing item metadata (title, url, source_name, etc.)
            notes: Optional personal notes about why the item was saved.

        Returns:
            The filepath of the created markdown file.
        """
        folder = self._get_date_folder()

        source_slug = self._slugify(item.get('source_name', 'unknown'))
        title_slug = self._slugify(item.get('title', 'untitled'))
        filename = f"{source_slug}-{title_slug}.md"
        filepath = folder / filename

        content = self._format_content(item, notes)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return str(filepath)

    def _format_content(self, item: Dict[str, Any], notes: Optional[str] = None) -> str:
        """Format item as Obsidian markdown with YAML frontmatter."""
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
