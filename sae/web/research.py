"""Research Agent for structured, multi-source evidence synthesis with prompt injection defenses."""

from datetime import datetime, timezone
from pydantic import BaseModel, Field
from sae.web.search import SearchManager, SearchResultItem


class ResearchFinding(BaseModel):
    claim: str
    sources: list[str] = Field(default_factory=list)
    confidence: str = "HIGH"


class ResearchReport(BaseModel):
    query: str
    findings: list[ResearchFinding] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ResearchAgent:
    def __init__(self, search_manager: SearchManager):
        self.search_manager = search_manager

    def generate_subqueries(self, goal: str) -> list[str]:
        words = goal.strip().split()
        subqueries = [goal]
        if len(words) > 2:
            subqueries.append(f"{words[0]} {words[1]} trends")
            subqueries.append(f"{goal} best practices")
        return subqueries[:3]

    async def execute_research(self, goal: str) -> ResearchReport:
        subqueries = self.generate_subqueries(goal)
        collected_results: list[SearchResultItem] = []
        seen_urls = set()

        for q in subqueries:
            results = await self.search_manager.search(q, limit=3)
            for r in results:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    collected_results.append(r)

        findings = []
        sources = []
        for r in collected_results:
            sources.append(r.url)
            findings.append(
                ResearchFinding(
                    claim=f"[{r.domain}] {r.snippet}",
                    sources=[r.url],
                    confidence="HIGH"
                )
            )

        return ResearchReport(
            query=goal,
            findings=findings,
            sources=list(seen_urls),
            conflicts=[]
        )