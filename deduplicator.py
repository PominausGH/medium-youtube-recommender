# deduplicator.py
"""Content deduplication by URL and title similarity."""

from difflib import SequenceMatcher
from typing import List, Dict, Any


class Deduplicator:
    """Removes duplicate content items based on URL and title similarity."""

    def __init__(self, title_threshold: float = 0.85):
        """
        Initialize the deduplicator.

        Args:
            title_threshold: Minimum similarity ratio (0-1) for titles to be
                           considered duplicates. Default is 0.85.
        """
        self.title_threshold = title_threshold

    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison."""
        return title.lower().strip()

    def _title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate similarity ratio between two titles.

        Args:
            title1: First title
            title2: Second title

        Returns:
            Similarity ratio between 0 and 1
        """
        t1 = self._normalize_title(title1)
        t2 = self._normalize_title(title2)
        return SequenceMatcher(None, t1, t2).ratio()

    def _get_score(self, item: Dict[str, Any]) -> float:
        """
        Get a score for ranking duplicates. Higher is better.

        Combines multiple score fields to determine which duplicate to keep.

        Args:
            item: Content item dictionary

        Returns:
            Combined score value
        """
        score = item.get('score', 0) or 0
        score += item.get('upvotes', 0) or 0
        score += (item.get('relevance_score', 0) or 0) * 10
        return score

    def deduplicate(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate items from a list.

        Deduplication is based on:
        1. Exact URL matches
        2. Similar titles (above threshold)

        When duplicates are found, the item with the highest score is kept.

        Args:
            items: List of content item dictionaries

        Returns:
            List of unique content items
        """
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
            if url and url in seen_urls:
                continue

            # Check title similarity
            is_duplicate = False
            for existing in unique_items:
                existing_title = existing.get('title', '')
                if title and existing_title:
                    if self._title_similarity(title, existing_title) >= self.title_threshold:
                        is_duplicate = True
                        break

            if not is_duplicate:
                if url:
                    seen_urls.add(url)
                unique_items.append(item)

        return unique_items
