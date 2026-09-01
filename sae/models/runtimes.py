"""Runtime abstractions decoupling SAE from specific backend engines (Ollama, llama.cpp, LM Studio)."""

from abc import ABC, abstractmethod
from typing import Any
import httpx
from sae.models.registry import LocalModelInfo, ModelStatus


class BaseLocalRuntime(ABC):
    @abstractmethod
    async def is_available(self) -> bool:
        pass

    @abstractmethod
    async def list_installed_models(self) -> list[str]:
        pass

    @abstractmethod
    async def get_model_health(self, model_id: str) -> ModelStatus:
        pass


class OllamaRuntime(BaseLocalRuntime):
    def __init__(self, endpoint: str = "http://localhost:11434"):
        self.endpoint = endpoint.rstrip("/")

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                res = await client.get(f"{self.endpoint}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def list_installed_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.endpoint}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            pass
        return []

    async def get_model_health(self, model_id: str) -> ModelStatus:
        models = await self.list_installed_models()
        return ModelStatus.READY if any(model_id in m for m in models) else ModelStatus.NOT_INSTALLED


class MockLocalRuntime(BaseLocalRuntime):
    def __init__(self, installed_models: list[str] | None = None):
        self.installed = installed_models or ["qwen3:8b", "llava:7b"]

    async def is_available(self) -> bool:
        return True

    async def list_installed_models(self) -> list[str]:
        return self.installed

    async def get_model_health(self, model_id: str) -> ModelStatus:
        return ModelStatus.READY if model_id in self.installed else ModelStatus.NOT_INSTALLED