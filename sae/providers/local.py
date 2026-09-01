"""Local AI Provider (Qwen3 8B default)."""

import time
import httpx
from sae.providers.base import (
    AICapability,
    AIRequest,
    AIResponse,
    BaseAIProvider,
    ErrorCategory,
    ProviderError,
    ProviderHealth,
    ProviderState,
)


class LocalAIProvider(BaseAIProvider):
    provider_name = "local"
    is_local = True

    def __init__(
        self,
        endpoint: str = "http://localhost:11434",
        model_name: str = "qwen3:8b",
        runtime: str = "ollama",
        client: httpx.AsyncClient | None = None
    ):
        self.endpoint = endpoint.rstrip("/")
        self.model_name = model_name
        self.runtime = runtime
        self._client = client

    def get_supported_capabilities(self) -> list[AICapability]:
        return [
            AICapability.TEXT,
            AICapability.STRUCTURED_OUTPUT,
            AICapability.REASONING,
            AICapability.TOOL_USE
        ]

    async def check_health(self) -> ProviderHealth:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{self.endpoint}/api/tags")
                if resp.status_code == 200:
                    models_data = resp.json().get("models", [])
                    available_models = [m.get("name", "") for m in models_data]
                    model_found = any(self.model_name in name for name in available_models)
                    
                    return ProviderHealth(
                        provider_name=self.provider_name,
                        state=ProviderState.AVAILABLE if model_found else ProviderState.DEGRADED,
                        is_available=True,
                        status_message=f"Local runtime ({self.runtime}) active. Model {self.model_name} configured.",
                        model_name=self.model_name,
                        supported_capabilities=self.get_supported_capabilities()
                    )
        except Exception:
            pass

        return ProviderHealth(
            provider_name=self.provider_name,
            state=ProviderState.UNAVAILABLE,
            is_available=False,
            status_message=f"Local runtime ({self.runtime}) not reachable at {self.endpoint}. SAE remains operational.",
            model_name=self.model_name,
            supported_capabilities=self.get_supported_capabilities()
        )

    async def generate(self, request: AIRequest) -> AIResponse:
        start_time = time.perf_counter()
        
        payload = {
            "model": self.model_name,
            "prompt": request.prompt,
            "stream": False,
            "options": {"temperature": request.temperature}
        }
        if request.system_instruction:
            payload["system"] = request.system_instruction

        try:
            client = self._client or httpx.AsyncClient(timeout=request.timeout_seconds)
            async with client as active_client:
                resp = await active_client.post(f"{self.endpoint}/api/generate", json=payload)
                
                if resp.status_code == 200:
                    data = resp.json()
                    return AIResponse(
                        success=True,
                        content=data.get("response", ""),
                        provider_name=self.provider_name,
                        model_name=self.model_name,
                        duration_seconds=time.perf_counter() - start_time,
                        usage={"total_duration": data.get("total_duration", 0)}
                    )
                else:
                    raise ProviderError(
                        message=f"Local runtime returned HTTP {resp.status_code}",
                        category=ErrorCategory.SERVER_ERROR,
                        provider_name=self.provider_name,
                        is_transient=False
                    )
        except httpx.ConnectError as e:
            raise ProviderError(
                message=f"Local runtime offline at {self.endpoint}: {e}",
                category=ErrorCategory.CONNECTION_FAILURE,
                provider_name=self.provider_name,
                is_transient=False,
                raw_error=e
            )
        except httpx.TimeoutException as e:
            raise ProviderError(
                message=f"Local inference timed out after {request.timeout_seconds}s",
                category=ErrorCategory.TIMEOUT,
                provider_name=self.provider_name,
                is_transient=True,
                raw_error=e
            )
        except Exception as e:
            if isinstance(e, ProviderError):
                raise e
            raise ProviderError(
                message=f"Unexpected local provider error: {e}",
                category=ErrorCategory.UNKNOWN,
                provider_name=self.provider_name,
                is_transient=False,
                raw_error=e
            )