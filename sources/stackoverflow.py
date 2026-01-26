# sources/stackoverflow.py
"""Stack Overflow content source for programming Q&A."""

import logging
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base import ContentSource

logger = logging.getLogger(__name__)


class StackOverflowSource(ContentSource):
    """Content source for Stack Overflow questions and answers."""

    def __init__(self):
        self.base_url = 'https://api.stackexchange.com/2.3'
        self.timeout = 10

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
        reraise=True
    )
    def _fetch_questions(self, query: str, limit: int) -> dict[str, Any]:
        """Fetch questions from Stack Overflow API with retry logic."""
        url = f'{self.base_url}/search/advanced'
        params = {
            'order': 'desc',
            'sort': 'relevance',
            'q': query,
            'site': 'stackoverflow',
            'pagesize': limit,
            'filter': 'withbody',
            'accepted': 'True',  # Only questions with accepted answers
        }
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def search(self, query: str, limit: int = 5, **kwargs: Any) -> list[dict[str, Any]]:
        """Search Stack Overflow for questions.
        
        Args:
            query: Search query string.
            limit: Maximum number of results.
            
        Returns:
            List of question metadata dictionaries.
        """
        results = []
        try:
            data = self._fetch_questions(query, limit)

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
            logger.debug(f'Fetched {len(results)} questions from Stack Overflow')
        except requests.ConnectionError as e:
            logger.warning(f'Connection error fetching Stack Overflow: {e}')
        except requests.Timeout as e:
            logger.warning(f'Timeout fetching Stack Overflow: {e}')
        except requests.HTTPError as e:
            logger.warning(f'HTTP error fetching Stack Overflow: {e}')
        except Exception as e:
            logger.error(f'Unexpected error fetching Stack Overflow: {e}', exc_info=True)

        logger.info(f'Stack Overflow search for "{query}" returned {len(results)} results')
        return results
