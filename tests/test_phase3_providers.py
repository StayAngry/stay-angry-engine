import pytest
import httpx
from sae.events import EventBus
from sae.logger import SensitiveDataFilter
from sae.providers.base import (
    AICapability,
    AIRequest,
    ErrorCategory,
    ProviderError,
    ProviderState,
)
from sae.providers.gemini import GeminiProvider
from sae.providers.local import LocalAIProvider
from sae.providers.manager import ProviderManager
from sae.providers.mock import MockProvider
from sae.providers.resources import ResourceAuditor
from sae.providers.router import ModelRouter


@pytest.mark.asyncio
async def test_mock_provider_offline():
    mock = MockProvider(simulated_response="Local reasoning output")
    health = await mock.check_health()
    assert health.is_available is True
    assert health.state == ProviderState.AVAILABLE

    res = await mock.generate(AIRequest(prompt="Analyze task"))
    assert res.success is True
    assert res.content == "Local reasoning output"


@pytest.mark.asyncio
async def test_local_provider_unavailable_graceful_handling():
    local = LocalAIProvider(endpoint="http://localhost:59999", model_name="qwen3:8b")
    health = await local.check_health()
    
    assert health.is_available is False
    assert health.state == ProviderState.UNAVAILABLE
    assert "not reachable" in health.status_message


@pytest.mark.asyncio
async def test_provider_registration_and_removal():
    bus = EventBus()
    manager = ProviderManager(bus)
    mock = MockProvider()
    
    manager.register_provider(mock)
    assert "mock" in manager.list_providers()
    
    manager.unregister_provider("mock")
    assert "mock" not in manager.list_providers()


@pytest.mark.asyncio
async def test_gemini_missing_api_key_degrades_gracefully():
    gemini = GeminiProvider(api_key=None)
    health = await gemini.check_health()
    
    assert health.is_available is False
    assert health.state == ProviderState.MISCONFIGURED

    with pytest.raises(ProviderError) as exc_info:
        await gemini.generate(AIRequest(prompt="Test"))
    
    assert exc_info.value.category == ErrorCategory.AUTHENTICATION


@pytest.mark.asyncio
async def test_local_to_mock_fallback_pipeline():
    bus = EventBus()
    manager = ProviderManager(bus)

    local = LocalAIProvider(endpoint="http://localhost:59999", model_name="qwen3:8b")
    mock = MockProvider(simulated_response="Fallback executed successfully")
    
    manager.register_provider(local)
    manager.register_provider(mock)

    router = ModelRouter(
        manager=manager,
        event_bus=bus,
        priority=["local", "mock"],
        max_retries=1
    )

    response = await router.route_and_generate(AIRequest(prompt="Execute plan"))
    assert response.success is True
    assert response.content == "Fallback executed successfully"
    assert response.provider_name == "mock"


@pytest.mark.asyncio
async def test_gemini_quota_exhaustion_triggers_fallback():
    bus = EventBus()
    manager = ProviderManager(bus)

    def mock_gemini_transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "Resource has been exhausted"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(mock_gemini_transport))
    failing_gemini = GeminiProvider(api_key="mock_secret_key", client=client)
    backup_mock = MockProvider(simulated_response="Local backup executed")

    manager.register_provider(failing_gemini)
    manager.register_provider(backup_mock)

    router = ModelRouter(
        manager=manager,
        event_bus=bus,
        priority=["gemini", "mock"],
        max_retries=1
    )

    response = await router.route_and_generate(AIRequest(prompt="Generate scene"))
    assert response.success is True
    assert response.content == "Local backup executed"


@pytest.mark.asyncio
async def test_offline_mode_filters_cloud_providers():
    bus = EventBus()
    manager = ProviderManager(bus)

    gemini = GeminiProvider(api_key="valid_key")
    mock = MockProvider(simulated_response="Offline local inference")

    manager.register_provider(gemini)
    manager.register_provider(mock)

    router = ModelRouter(
        manager=manager,
        event_bus=bus,
        priority=["gemini", "mock"],
        offline_mode=True
    )

    response = await router.route_and_generate(AIRequest(prompt="Render text"))
    assert response.success is True
    assert response.provider_name == "mock"


def test_sensitive_secret_redaction():
    filter_obj = SensitiveDataFilter()
    
    class FakeRecord:
        msg = "Encountered issue with token_secret_123456 and api_key=AIzaSySecretToken99"

    record = FakeRecord()
    assert filter_obj.filter(record) is True
    assert record.msg == "[REDACTED_SECURITY_SENSITIVE_STRING]"


def test_resource_auditor_metrics():
    metrics = ResourceAuditor.get_local_resource_metrics()
    assert metrics.total_ram_gb > 0
    assert metrics.free_disk_gb >= 0