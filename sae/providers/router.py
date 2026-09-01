"""Intelligent Model Router with capability matching, hardware awareness, and strict policy enforcement."""

from enum import Enum
from typing import Any
from sae.events import Event, EventBus, EventType
from sae.models.registry import LocalModelInfo, LocalModelRegistry, ModelCapability
from sae.providers.base import AIRequest, AIResponse, BaseAIProvider, ProviderState
from sae.providers.manager import ProviderManager
from sae.resources import ResourceManager


class RoutingPolicy(str, Enum):
    LOCAL_ONLY = "LOCAL_ONLY"
    LOCAL_FIRST = "LOCAL_FIRST"
    CLOUD_FIRST = "CLOUD_FIRST"
    CLOUD_ONLY = "CLOUD_ONLY"
    MOCK_ONLY = "MOCK_ONLY"


class ModelRouter:
    def __init__(
        self,
        manager: ProviderManager,
        event_bus: EventBus,
        model_registry: LocalModelRegistry | None = None,
        resource_manager: ResourceManager | None = None,
        policy: RoutingPolicy = RoutingPolicy.LOCAL_FIRST,
        priority: list[str] | None = None,
        max_retries: int = 3,
        offline_mode: bool = False
    ):
        self.manager = manager
        self.event_bus = event_bus
        self.model_registry = model_registry or LocalModelRegistry()
        self.resource_manager = resource_manager or ResourceManager()
        self.policy = policy
        self.priority = priority or ["local", "gemini", "mock"]
        self.max_retries = max_retries
        self.offline_mode = offline_mode

    def _is_healthy(self, state: ProviderState) -> bool:
        healthy_states = {
            getattr(ProviderState, "AVAILABLE", None),
            getattr(ProviderState, "READY", None),
            getattr(ProviderState, "HEALTHY", None),
        }
        return state in healthy_states

    def score_model(self, model: LocalModelInfo, required_capability: ModelCapability | None) -> float:
        score = 10.0
        if required_capability:
            if required_capability in model.capabilities:
                score += 50.0
            else:
                score -= 100.0

        if not self.resource_manager.can_accommodate(model.vram_required_gb, model.ram_required_gb):
            score -= 200.0

        return score

    def select_local_model(self, required_capability: ModelCapability | None = None) -> LocalModelInfo | None:
        candidates = self.model_registry.list_models()
        scored = [(self.score_model(m, required_capability), m) for m in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        
        if scored and scored[0][0] > 0:
            return scored[0][1]
        return None

    async def _execute_on_provider(self, provider: BaseAIProvider, request: AIRequest) -> AIResponse:
        if hasattr(provider, "generate"):
            return await provider.generate(request)
        if hasattr(provider, "generate_response"):
            return await provider.generate_response(request)
        raise AttributeError(f"Provider {provider.name} does not have a valid generate method.")

    async def route_and_execute(
        self,
        request: AIRequest,
        required_capability: ModelCapability | None = None
    ) -> AIResponse:
        if self.policy == RoutingPolicy.MOCK_ONLY:
            mock = self.manager.get_provider("mock")
            if mock:
                return await self._execute_on_provider(mock, request)
            raise RuntimeError("Mock provider requested but unavailable.")

        # Local routing attempt
        if self.policy in (RoutingPolicy.LOCAL_FIRST, RoutingPolicy.LOCAL_ONLY):
            best_model = self.select_local_model(required_capability)
            local_provider = self.manager.get_provider("local")

            if local_provider and best_model:
                health = await local_provider.check_health()
                if self._is_healthy(health.state):
                    try:
                        return await self._execute_on_provider(local_provider, request)
                    except Exception as e:
                        await self.event_bus.emit(
                            Event(
                                event_type=EventType.PROVIDER_ERROR,
                                source="ModelRouter",
                                payload={"provider": "local", "error": str(e)}
                            )
                        )

            if self.policy == RoutingPolicy.LOCAL_ONLY:
                raise RuntimeError("Local-only policy active: No capable local model or runtime available.")

        # Priority / Fallback loop
        for prov_name in self.priority:
            if prov_name == "local" and self.policy in (RoutingPolicy.LOCAL_FIRST, RoutingPolicy.LOCAL_ONLY):
                continue
            if self.offline_mode and prov_name == "gemini":
                continue

            provider = self.manager.get_provider(prov_name)
            if not provider:
                continue

            health = await provider.check_health()
            if self._is_healthy(health.state):
                try:
                    return await self._execute_on_provider(provider, request)
                except Exception as e:
                    await self.event_bus.emit(
                        Event(
                            event_type=EventType.PROVIDER_ERROR,
                            source="ModelRouter",
                            payload={"provider": prov_name, "error": str(e)}
                        )
                    )

        # Fallback to Mock
        mock = self.manager.get_provider("mock")
        if mock:
            return await self._execute_on_provider(mock, request)

        raise RuntimeError("ModelRouter exhausted all suitable local and cloud providers.")

    async def route_and_generate(self, request: AIRequest) -> AIResponse:
        return await self.route_and_execute(request)