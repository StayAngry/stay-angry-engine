"""Search provider abstractions with normalized results and offline fallback."""

from abc import ABC, abstractmethod
from typing import Any
import httpx
from pydantic import BaseModel, Field
from sae.web.gateway import InternetGateway


class SearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str
    domain: str
    timestamp: str | None = None


class BaseSearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[SearchResultItem]:
        pass


class DuckDuckGoSearchProvider(BaseSearchProvider):
    def __init__(self, gateway: InternetGateway | None = None):
        self.gateway = gateway or InternetGateway()

    async def search(self, query: str, limit: int = 5) -> list[SearchResultItem]:
        url = f"https://api.duckduckgo.com/?q={httpx.URL(query).raw_path.decode()}&format=json&no_html=1"
        try:
            res = await self.gateway.fetch_page(url)
            import json
            data = json.loads(res["content"])
            items = []
            
            # Instant Answer Topic
            if data.get("AbstractText"):
                items.append(
                    SearchResultItem(
                        title=data.get("Heading", query),
                        url=data.get("AbstractURL", url),
                        snippet=data.get("AbstractText", ""),
                        domain="duckduckgo.com"
                    )
                )

            # Related Topics
            for topic in data.get("RelatedTopics", []):
                if "Text" in topic and "FirstURL" in topic:
                    items.append(
                        SearchResultItem(
                            title=topic.get("Text", "")[:60],
                            url=topic.get("FirstURL", ""),
                            snippet=topic.get("Text", ""),
                            domain="duckduckgo.com"
                        )
                    )
                if len(items) >= limit:
                    break

            return items[:limit]
        except Exception:
            return []


class MockSearchProvider(BaseSearchProvider):
    def __init__(self, mock_results: list[SearchResultItem] | None = None):
        self.mock_results = mock_results or [
            SearchResultItem(
                title="Anime Editing Trends 2026 - Fast Transitions & Color Flow",
                url="https://example.com/anime-trends-2026",
                snippet="Popular 2026 styles feature dynamic beat synchronization, manhwa graphic overlays, and 9:16 vertical ratio.",
                domain="example.com"
            ),
            SearchResultItem(
                title="Top Reel Formats & Visual Effects",
                url="https://example.com/reels-vfx",
                snippet="Standardizing on 9:16 canvas at 60 FPS with punch-in zoom cuts.",
                domain="example.com"
            )
        ]

    async def search(self, query: str, limit: int = 5) -> list[SearchResultItem]:
        filtered = [r for r in self.mock_results if any(w.lower() in r.title.lower() or w.lower() in r.snippet.lower() for w in query.split())]
        return (filtered if filtered else self.mock_results)[:limit]


class SearchManager:
    def __init__(self, primary: BaseSearchProvider, fallback: BaseSearchProvider | None = None):
        self.primary = primary
        self.fallback = fallback

    async def search(self, query: str, limit: int = 5) -> list[SearchResultItem]:
        results = await self.primary.search(query, limit)
        if not results and self.fallback:
            results = await self.fallback.search(query, limit)
        return results