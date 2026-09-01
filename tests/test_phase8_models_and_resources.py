"""Comprehensive Phase 8 test suite validating model registry, capability matching, hardware leasing, and router policies."""

import pytest
from sae.events import EventBus
from sae.models.registry import LocalModelInfo, LocalModelRegistry, ModelCapability, ModelStatus
from sae.models.runtimes import MockLocalRuntime
from sae.providers.base import AIRequest
from sae.providers.manager import ProviderManager
from sae.providers.mock import MockProvider
from sae.providers.router import ModelRouter, RoutingPolicy
from sae.resources import ResourceManager


@pytest.fixture
def resource_mgr():
    return ResourceManager()


@pytest.fixture
def model_reg():
    return LocalModelRegistry()


def test_model_registry_registration_and_capability_filtering(model_reg: LocalModelRegistry):
    vision_models = model_reg.find_by_capability(ModelCapability.VISION)
    assert len(vision_models) >= 1
    assert vision_models[0].model_id == "llava:7b"

    reasoning_models = model_reg.find_by_capability(ModelCapability.REASONING)
    assert len(reasoning_models) >= 1
    assert reasoning_models[0].model_id == "qwen3:8b"


@pytest.mark.asyncio
async def test_resource_reservation_and_release(resource_mgr: ResourceManager):
    lease = await resource_mgr.reserve(task_id="test_task_1", vram_gb=1.0, ram_gb=0.5)
    assert lease is not None
    assert lease.reserved_vram_gb == 1.0

    released = await resource_mgr.release(lease.lease_id)
    assert released is True


@pytest.mark.asyncio
async def test_runtime_health_check():
    mock_runtime = MockLocalRuntime(installed_models=["qwen3:8b"])
    health_ready = await mock_runtime.get_model_health("qwen3:8b")
    health_missing = await mock_runtime.get_model_health("uninstalled_model")

    assert health_ready == ModelStatus.READY
    assert health_missing == ModelStatus.NOT_INSTALLED


@pytest.mark.asyncio
async def test_router_capability_selection(model_reg: LocalModelRegistry, resource_mgr: ResourceManager):
    bus = EventBus()
    manager = ProviderManager(bus)
    manager.register_provider(MockProvider())

    router = ModelRouter(
        manager=manager,
        event_bus=bus,
        model_registry=model_reg,
        resource_manager=resource_mgr,
        policy=RoutingPolicy.MOCK_ONLY
    )

    req = AIRequest(prompt="Analyze this frame", system_prompt="Vision analysis")
    res = await router.route_and_execute(req, required_capability=ModelCapability.VISION)
    assert res.content is not None