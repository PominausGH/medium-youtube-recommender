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
