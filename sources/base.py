from abc import ABC, abstractmethod
from typing import List, Dict, Any


class ContentSource(ABC):
    @abstractmethod
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Search for content. Returns list of dicts with keys:
        title, url, source_type, source_name, raw_date, description, thumbnail_url (optional)
        """
        pass
