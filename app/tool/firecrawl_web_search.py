import os
from typing import Optional

import requests
from pydantic import Field

from app.tool.base import BaseTool, ToolResult


class FirecrawlWebSearchResult(ToolResult):
    query: str = Field(description="The search query that was executed")
    results: list[dict] = Field(default_factory=list)

    def model_post_init(self, __context) -> None:
        if self.error:
            return
        lines = [f"Firecrawl search results for '{self.query}':"]
        for index, item in enumerate(self.results, 1):
            lines.append(f"\n{index}. {item.get('title') or 'Untitled'}")
            lines.append(f"   URL: {item.get('url') or ''}")
            if item.get('description'):
                lines.append(f"   Description: {item['description']}")
            if item.get('markdown'):
                preview = item['markdown'][:1500].replace("\n", " ").strip()
                if len(item['markdown']) > 1500:
                    preview += "..."
                lines.append(f"   Extracted content: {preview}")
        self.output = "\n".join(lines)


class FirecrawlWebSearch(BaseTool):
    """Low-cost Firecrawl-backed web search used by Cataron's agents."""

    name: str = "web_search"
    description: str = (
        "Search the public web through Firecrawl. Returns a small set of relevant "
        "pages with extracted metadata and content. Use this for web research and "
        "reference-site discovery instead of direct search-engine scraping."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The web search query.",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return. Keep this small for research.",
                "default": 2,
                "maximum": 2,
            },
            "lang": {
                "type": "string",
                "description": "Optional language hint.",
                "default": "en",
            },
            "country": {
                "type": "string",
                "description": "Optional country code.",
                "default": "us",
            },
        },
        "required": ["query"],
    }

    async def execute(
        self,
        query: str,
        num_results: int = 2,
        lang: Optional[str] = None,
        country: Optional[str] = None,
    ) -> FirecrawlWebSearchResult:
        api_key = (
            os.getenv("FIRECRAWL_API_KEY", "").strip()
            or os.getenv("OPENMANUS_FIRECRAWL_API_KEY", "").strip()
            or os.getenv("OPENMANUS_SECRET_FIRECRAWL_API_KEY", "").strip()
        )
        if not api_key:
            return FirecrawlWebSearchResult(
                query=query,
                error="Firecrawl is not configured: add the Render secret OPENMANUS_SECRET_FIRECRAWL_API_KEY.",
            )

        limit = max(1, min(int(num_results), 2))
        payload = {
            "query": query,
            "limit": limit,
            "sources": ["web"],
            "safe": True,
            "timeout": 30000,
            "highlights": True,
            "scrapeOptions": {"formats": ["markdown"]},
        }
        if country:
            payload["country"] = country.upper()

        try:
            response = requests.post(
                "https://api.firecrawl.dev/v2/search",
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

            results = []
            for result in body.get("data", {}).get("web", [])[:limit]:
                metadata = result.get("metadata") or {}
                results.append(
                    {
                        "title": result.get("title") or metadata.get("title") or "Untitled",
                        "url": result.get("url") or metadata.get("url") or metadata.get("sourceURL") or "",
                        "description": result.get("description") or metadata.get("description") or "",
                        "markdown": result.get("markdown") or "",
                    }
                )
            return FirecrawlWebSearchResult(query=query, results=results)
        except Exception as exc:
            return FirecrawlWebSearchResult(
                query=query,
                error=f"Firecrawl search failed: {exc}",
            )
