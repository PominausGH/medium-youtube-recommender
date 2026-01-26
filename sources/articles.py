# sources/articles.py
"""Article source for RSS feed content from various tech blogs."""

import logging
from typing import Any

import feedparser
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base import ContentSource

logger = logging.getLogger(__name__)

ARTICLE_SOURCES = {
    'Medium': 'https://medium.com/feed/tag/{tag}',
    'Dev.to': 'https://dev.to/feed/tag/{tag}',
    'HackerNoon': 'https://hackernoon.com/tagged/{tag}/feed',
    'Towards Data Science': 'https://towardsdatascience.com/feed',
    'freeCodeCamp': 'https://www.freecodecamp.org/news/rss/',
}


class ArticleSource(ContentSource):
    """Content source for RSS-based article feeds."""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True
    )
    def _fetch_feed(self, url: str) -> feedparser.FeedParserDict:
        """Fetch and parse RSS feed with retry logic."""
        return feedparser.parse(url)

    def search(
        self,
        query: str,
        sources: list[str] | None = None,
        limit: int = 5,
        **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Search articles from RSS feeds.
        
        Args:
            query: Search query (first word used as tag).
            sources: List of source names to search. Defaults to all.
            limit: Maximum results per source.
            
        Returns:
            List of article metadata dictionaries.
        """
        if sources is None:
            sources = list(ARTICLE_SOURCES.keys())

        tag = query.split()[0].lower() if query else 'python'
        results = []

        for source_name in sources:
            if source_name not in ARTICLE_SOURCES:
                logger.warning(f'Unknown article source: {source_name}')
                continue

            rss_url = ARTICLE_SOURCES[source_name].format(tag=tag)
            try:
                feed = self._fetch_feed(rss_url)
                for entry in feed.entries[:limit]:
                    summary = entry.get('summary', '')
                    description = BeautifulSoup(summary, 'html.parser').get_text()[:500]

                    results.append({
                        'title': entry.get('title', 'No title'),
                        'url': entry.get('link', ''),
                        'source_type': 'article',
                        'source_name': source_name,
                        'raw_date': entry.get('published') or entry.get('updated') or '',
                        'description': description,
                    })
                logger.debug(f'Fetched {len(feed.entries[:limit])} articles from {source_name}')
            except ConnectionError as e:
                logger.warning(f'Connection error fetching {source_name}: {e}')
            except TimeoutError as e:
                logger.warning(f'Timeout fetching {source_name}: {e}')
            except Exception as e:
                logger.error(f'Unexpected error fetching {source_name}: {e}', exc_info=True)

        logger.info(f'Article search for "{query}" returned {len(results)} results')
        return results
