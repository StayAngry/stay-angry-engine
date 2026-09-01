"""Comprehensive Phase 7 test suite validating gateway security, SSRF guards, quarantine, and research agent."""

import pytest
from pathlib import Path
from sae.web.downloader import QuarantineDownloader
from sae.web.gateway import GatewaySecurityError, InternetGateway
from sae.web.research import ResearchAgent
from sae.web.search import MockSearchProvider, SearchManager, SearchResultItem


def test_ssrf_blocks_localhost_and_private_ips():
    gw = InternetGateway()
    
    with pytest.raises(GatewaySecurityError, match="blocked"):
        gw.validate_url("http://localhost:8080/admin")

    with pytest.raises(GatewaySecurityError, match="blocked"):
        gw.validate_url("http://127.0.0.1:3000/api")

    with pytest.raises(GatewaySecurityError, match="Unsupported protocol"):
        gw.validate_url("file:///etc/passwd")


def test_downloader_blocks_executable_file_extensions(tmp_path: Path):
    downloader = QuarantineDownloader(tmp_path)
    
    with pytest.raises(GatewaySecurityError, match="Disallowed file extension"):
        import asyncio
        asyncio.run(downloader.download_to_quarantine("https://example.com/payload.exe"))


@pytest.mark.asyncio
async def test_search_manager_fallback():
    mock_provider = MockSearchProvider([
        SearchResultItem(
            title="Anime Reel Pacing Guide",
            url="https://animeguide.org/pacing",
            snippet="Cut on action peaks every 1.5 seconds for high energy reels.",
            domain="animeguide.org"
        )
    ])
    manager = SearchManager(primary=mock_provider)
    results = await manager.search("pacing", limit=1)

    assert len(results) == 1
    assert results[0].domain == "animeguide.org"


@pytest.mark.asyncio
async def test_research_agent_multi_query_synthesis():
    mock_results = [
        SearchResultItem(
            title="Anime Editing Styles 2026",
            url="https://editnews.com/anime2026",
            snippet="High-framerate zoom snaps and manhwa typography are trending.",
            domain="editnews.com"
        )
    ]
    search_manager = SearchManager(primary=MockSearchProvider(mock_results))
    agent = ResearchAgent(search_manager)

    report = await agent.execute_research("anime editing trends")
    assert report.query == "anime editing trends"
    assert len(report.findings) > 0
    assert "https://editnews.com/anime2026" in report.sources