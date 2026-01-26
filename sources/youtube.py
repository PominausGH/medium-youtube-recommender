# sources/youtube.py
"""YouTube video source for content curation."""

import logging
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential
from youtubesearchpython import VideosSearch

from .base import ContentSource

logger = logging.getLogger(__name__)


class YouTubeSource(ContentSource):
    """Content source for YouTube videos."""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _search_videos(self, query: str, limit: int) -> dict[str, Any]:
        """Search YouTube with retry logic."""
        search = VideosSearch(query, limit=limit)
        return search.result()

    def search(self, query: str, limit: int = 5, **kwargs: Any) -> list[dict[str, Any]]:
        """Search YouTube videos.
        
        Args:
            query: Search query string.
            limit: Maximum number of results.
            
        Returns:
            List of video metadata dictionaries.
        """
        results = []
        try:
            search_result = self._search_videos(query, limit)
            video_list = search_result.get('result', [])
            
            for vid in video_list:
                thumbnails = vid.get('thumbnails') or []
                thumb_url = thumbnails[0].get('url', '') if thumbnails else ''

                desc_snip = vid.get('descriptionSnippet') or []
                description = ' '.join(
                    str(d.get('text', '')) for d in desc_snip
                ) if desc_snip else ''

                results.append({
                    'title': vid.get('title') or 'No title',
                    'url': vid.get('link') or '',
                    'source_type': 'youtube',
                    'source_name': 'YouTube',
                    'raw_date': vid.get('publishedTime') or '',
                    'description': description,
                    'thumbnail_url': thumb_url,
                })
            logger.debug(f'YouTube search for "{query}" returned {len(results)} videos')
        except ConnectionError as e:
            logger.warning(f'Connection error searching YouTube: {e}')
        except TimeoutError as e:
            logger.warning(f'Timeout searching YouTube: {e}')
        except Exception as e:
            logger.error(f'Unexpected error searching YouTube: {e}', exc_info=True)

        logger.info(f'YouTube search completed with {len(results)} results')
        return results
