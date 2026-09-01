"""Provider Manager."""

from sae.events import Event, EventBus, EventType
from sae.providers.base import (
    AICapability,
    BaseAIProvider,
    ProviderHealth,
    ProviderState,
)


class ProviderManager:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._providers: dict[str, BaseAIProvider] = {}

    def register_provider(self, provider: BaseAIProvider) -> None:
        self._providers[provider.provider_name] = provider

    def unregister_provider(self, provider_name: str) -> None:
        if provider_name in self._providers:
            del self._providers[provider_name]

    def get_provider(self, provider_name: str) -> BaseAIProvider | None:
        return self._providers.get(provider_name)

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    async def get_all_health(self) -> dict[str, ProviderHealth]:
        health_map = {}
        for name, provider in self._providers.items():
            health_map[name] = await provider.check_health()
        return health_map

    async def get_available_providers(
        self,
        capability: AICapability,
        offline_only: bool = False
    ) -> list[BaseAIProvider]:
        candidates: list[BaseAIProvider] = []
        for provider in self._providers.values():
            if offline_only and not provider.is_local:
                continue
            if capability in provider.get_supported_capabilities():
                health = await provider.check_health()
                if health.is_available and health.state not in (
                    ProviderState.UNAVAILABLE,
                    ProviderState.RATE_LIMITED,
                    ProviderState.QUOTA_EXHAUSTED,
                    ProviderState.MISCONFIGURED
                ):
                    candidates.append(provider)
        return candidates