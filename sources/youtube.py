from youtubesearchpython import VideosSearch
from typing import List, Dict, Any
from .base import ContentSource


class YouTubeSource(ContentSource):
    def search(self, query: str, limit: int = 5, **kwargs) -> List[Dict[str, Any]]:
        results = []
        try:
            videos = VideosSearch(query, limit=limit)
            for vid in videos.result()['result']:
                thumbnails = vid.get('thumbnails') or []
                thumb_url = thumbnails[0].get('url', '') if thumbnails else ''

                desc_snip = vid.get('descriptionSnippet') or []
                description = ' '.join(str(d.get('text', '')) for d in desc_snip) if desc_snip else ''

                results.append({
                    'title': vid.get('title') or 'No title',
                    'url': vid.get('link') or '',
                    'source_type': 'youtube',
                    'source_name': 'YouTube',
                    'raw_date': vid.get('publishedTime') or '',
                    'description': description,
                    'thumbnail_url': thumb_url,
                })
        except Exception:
            pass

        return results
