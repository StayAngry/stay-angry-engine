"""Optional Gemini Provider."""

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


class GeminiProvider(BaseAIProvider):
    provider_name = "gemini"
    is_local = False

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-2.5-flash",
        client: httpx.AsyncClient | None = None
    ):
        self.api_key = api_key
        self.model_name = model_name
        self._client = client

    def get_supported_capabilities(self) -> list[AICapability]:
        return [
            AICapability.TEXT,
            AICapability.STRUCTURED_OUTPUT,
            AICapability.VISION,
            AICapability.AUDIO,
            AICapability.REASONING,
            AICapability.TOOL_USE
        ]

    async def check_health(self) -> ProviderHealth:
        if not self.api_key or self.api_key.strip() == "":
            return ProviderHealth(
                provider_name=self.provider_name,
                state=ProviderState.MISCONFIGURED,
                is_available=False,
                status_message="Gemini API key not configured (Cloud AI is optional).",
                model_name=self.model_name,
                supported_capabilities=self.get_supported_capabilities()
            )

        return ProviderHealth(
            provider_name=self.provider_name,
            state=ProviderState.AVAILABLE,
            is_available=True,
            status_message="Gemini provider configured and active.",
            model_name=self.model_name,
            supported_capabilities=self.get_supported_capabilities()
        )

    async def generate(self, request: AIRequest) -> AIResponse:
        start_time = time.perf_counter()

        if not self.api_key or self.api_key.strip() == "":
            raise ProviderError(
                message="Gemini API key is missing or blank.",
                category=ErrorCategory.AUTHENTICATION,
                provider_name=self.provider_name,
                is_transient=False
            )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        
        contents = [{"parts": [{"text": request.prompt}]}]
        body = {"contents": contents}
        if request.system_instruction:
            body["systemInstruction"] = {"parts": [{"text": request.system_instruction}]}

        try:
            client = self._client or httpx.AsyncClient(timeout=request.timeout_seconds)
            async with client as active_client:
                resp = await active_client.post(url, json=body)
                
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        content_text = "".join(p.get("text", "") for p in parts)
                        return AIResponse(
                            success=True,
                            content=content_text,
                            provider_name=self.provider_name,
                            model_name=self.model_name,
                            duration_seconds=time.perf_counter() - start_time,
                            usage=data.get("usageMetadata", {})
                        )
                    return AIResponse(
                        success=True,
                        content="",
                        provider_name=self.provider_name,
                        model_name=self.model_name,
                        duration_seconds=time.perf_counter() - start_time
                    )
                elif resp.status_code in (401, 403):
                    raise ProviderError(
                        message="Invalid or unauthorized Gemini API key.",
                        category=ErrorCategory.AUTHENTICATION,
                        provider_name=self.provider_name,
                        is_transient=False
                    )
                elif resp.status_code == 429:
                    raise ProviderError(
                        message="Gemini rate limit exceeded or quota exhausted.",
                        category=ErrorCategory.QUOTA_OR_RATE_LIMIT,
                        provider_name=self.provider_name,
                        is_transient=False
                    )
                else:
                    raise ProviderError(
                        message=f"Gemini API returned error code HTTP {resp.status_code}",
                        category=ErrorCategory.SERVER_ERROR,
                        provider_name=self.provider_name,
                        is_transient=False
                    )
        except httpx.TimeoutException as e:
            raise ProviderError(
                message=f"Gemini request timed out after {request.timeout_seconds}s",
                category=ErrorCategory.TIMEOUT,
                provider_name=self.provider_name,
                is_transient=True,
                raw_error=e
            )
        except httpx.ConnectError as e:
            raise ProviderError(
                message="Network connection failure reaching Gemini cloud endpoints.",
                category=ErrorCategory.CONNECTION_FAILURE,
                provider_name=self.provider_name,
                is_transient=True,
                raw_error=e
            )
        except Exception as e:
            if isinstance(e, ProviderError):
                raise e
            raise ProviderError(
                message=f"Unexpected Gemini error: {e}",
                category=ErrorCategory.UNKNOWN,
                provider_name=self.provider_name,
                is_transient=False,
                raw_error=e
            )