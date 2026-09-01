"""Mock AI Provider for testing."""

import time
from sae.providers.base import (
    AICapability,
    AIRequest,
    AIResponse,
    BaseAIProvider,
    ProviderHealth,
    ProviderState,
)


class MockProvider(BaseAIProvider):
    provider_name = "mock"
    is_local = True

    def __init__(
        self,
        model_name: str = "mock-agent-v1",
        default_state: ProviderState = ProviderState.AVAILABLE,
        simulated_response: str | None = None
    ):
        self.model_name = model_name
        self.state = default_state
        self.simulated_response = simulated_response

    def get_supported_capabilities(self) -> list[AICapability]:
        return [
            AICapability.TEXT,
            AICapability.STRUCTURED_OUTPUT,
            AICapability.REASONING,
            AICapability.TOOL_USE
        ]

    async def check_health(self) -> ProviderHealth:
        is_avail = self.state in (ProviderState.AVAILABLE, ProviderState.DEGRADED)
        return ProviderHealth(
            provider_name=self.provider_name,
            state=self.state,
            is_available=is_avail,
            status_message=f"Mock provider operational in state: {self.state.value}",
            model_name=self.model_name,
            supported_capabilities=self.get_supported_capabilities()
        )

    async def generate(self, request: AIRequest) -> AIResponse:
        start = time.perf_counter()
        if self.state == ProviderState.UNAVAILABLE:
            return AIResponse(
                success=False,
                error="Mock provider configured as UNAVAILABLE.",
                provider_name=self.provider_name,
                model_name=self.model_name,
                duration_seconds=time.perf_counter() - start
            )

        output = self.simulated_response or f"Deterministic mock response for: {request.prompt}"
        return AIResponse(
            success=True,
            content=output,
            provider_name=self.provider_name,
            model_name=self.model_name,
            duration_seconds=time.perf_counter() - start,
            metadata={"mock": True}
        )