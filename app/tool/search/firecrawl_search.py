import os
from typing import List

import requests

from app.tool.search.base import SearchItem, WebSearchEngine


class FirecrawlSearchEngine(WebSearchEngine):
    """Firecrawl-backed web search with optional page extraction."""

    endpoint: str = "https://api.firecrawl.dev/v2/search"

    def _api_key(self) -> str:
        return (
            os.getenv("FIRECRAWL_API_KEY", "").strip()
            or os.getenv("OPENMANUS_FIRECRAWL_API_KEY", "").strip()
        )

    def perform_search(
        self, query: str, num_results: int = 10, *args, **kwargs
    ) -> List[SearchItem]:
        api_key = self._api_key()
        if not api_key:
            raise RuntimeError(
                "Firecrawl search is enabled but FIRECRAWL_API_KEY is not configured"
            )

        limit = max(1, min(int(num_results), 5))
        payload = {
            "query": query,
            "limit": limit,
            "sources": ["web"],
            "country": str(kwargs.get("country") or "US").upper(),
            "safe": True,
            "timeout": 30000,
            "highlights": True,
            "scrapeOptions": {"formats": ["markdown"]},
        }
        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=40,
        )
        response.raise_for_status()
        body = response.json()
        if not body.get("success", False):
            raise RuntimeError(body.get("error") or "Firecrawl search failed")

        items = []
        for result in body.get("data", {}).get("web", [])[:limit]:
            url = result.get("url") or result.get("metadata", {}).get("url")
            if not url:
                continue
            markdown = result.get("markdown") or ""
            description = result.get("description") or result.get("metadata", {}).get("description") or ""
            if markdown:
                description = f"{description}\n\n{markdown[:6000]}".strip()
            items.append(
                SearchItem(
                    title=result.get("title") or result.get("metadata", {}).get("title") or url,
                    url=url,
                    description=description[:8000],
                )
            )
        return items
