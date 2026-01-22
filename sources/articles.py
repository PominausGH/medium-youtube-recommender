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
