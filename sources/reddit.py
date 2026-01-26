# sources/reddit.py
"""Reddit content source for tech discussions and posts."""

import logging
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base import ContentSource

logger = logging.getLogger(__name__)

# Map technologies to relevant subreddits
TECH_SUBREDDITS = {
    'python': ['Python', 'learnpython', 'FastAPI', 'django', 'flask'],
    'javascript': ['javascript', 'node', 'reactjs', 'vuejs', 'typescript'],
    'rust': ['rust', 'learnrust'],
    'go': ['golang'],
    'default': ['programming', 'coding', 'learnprogramming'],
}


class RedditSource(ContentSource):
    """Content source for Reddit posts and discussions."""

    def __init__(self):
        self.base_url = 'https://www.reddit.com'
        self.headers = {'User-Agent': 'ContentCurator/1.0 (educational project)'}
        self.timeout = 10

    def _get_subreddits(self, query: str) -> list[str]:
        """Get relevant subreddits for the search query."""
        query_lower = query.lower()
        for tech, subs in TECH_SUBREDDITS.items():
            if tech in query_lower:
                return subs
        return TECH_SUBREDDITS['default']

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
        reraise=True
    )
    def _fetch_subreddit(self, subreddit: str, query: str, limit: int) -> dict[str, Any]:
        """Fetch posts from a subreddit with retry logic."""
        url = f'{self.base_url}/r/{subreddit}/search.json'
        params = {
            'q': query,
            'restrict_sr': 'true',
            'sort': 'relevance',
            't': 'month',
            'limit': limit
        }
        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def search(
        self,
        query: str,
        limit: int = 5,
        min_upvotes: int = 10,
        **kwargs: Any
    ) -> list[dict[str, Any]]:
        """Search Reddit for posts matching the query.
        
        Args:
            query: Search query string.
            limit: Maximum results per subreddit.
            min_upvotes: Minimum upvotes to include a post.
            
        Returns:
            List of post metadata dictionaries.
        """
        subreddits = self._get_subreddits(query)
        results = []

        for subreddit in subreddits[:3]:  # Limit subreddits to avoid rate limiting
            try:
                data = self._fetch_subreddit(subreddit, query, limit)

                for post in data.get('data', {}).get('children', []):
                    post_data = post.get('data', {})
                    if post_data.get('ups', 0) < min_upvotes:
                        continue

                    results.append({
                        'title': post_data.get('title', 'No title'),
                        'url': f"https://reddit.com{post_data.get('permalink', '')}",
                        'source_type': 'reddit',
                        'source_name': f'r/{subreddit}',
                        'raw_date': '',  # Reddit uses timestamps
                        'description': post_data.get('selftext', '')[:500],
                        'upvotes': post_data.get('ups', 0),
                        'num_comments': post_data.get('num_comments', 0),
                    })
                logger.debug(f'Fetched posts from r/{subreddit}')
            except requests.ConnectionError as e:
                logger.warning(f'Connection error fetching r/{subreddit}: {e}')
            except requests.Timeout as e:
                logger.warning(f'Timeout fetching r/{subreddit}: {e}')
            except requests.HTTPError as e:
                logger.warning(f'HTTP error fetching r/{subreddit}: {e}')
            except Exception as e:
                logger.error(f'Unexpected error fetching r/{subreddit}: {e}', exc_info=True)

        logger.info(f'Reddit search for "{query}" returned {len(results[:limit])} results')
        return results[:limit]
