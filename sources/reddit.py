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
