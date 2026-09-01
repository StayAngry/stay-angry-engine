"""Structured local model registry, capability definitions, and metadata tracking."""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ModelCapability(str, Enum):
    TEXT = "TEXT"
    REASONING = "REASONING"
    CODING = "CODING"
    TOOL_USE = "TOOL_USE"
    VISION = "VISION"
    EMBEDDING = "EMBEDDING"


class ModelStatus(str, Enum):
    READY = "READY"
    BUSY = "BUSY"
    NOT_INSTALLED = "NOT_INSTALLED"
    ERROR = "ERROR"


class LocalModelInfo(BaseModel):
    model_id: str
    name: str
    runtime_name: str
    quantization: str = "Q4_K_M"
    context_length: int = 8192
    vram_required_gb: float = 5.5
    ram_required_gb: float = 4.0
    capabilities: list[ModelCapability] = Field(default_factory=list)
    status: ModelStatus = ModelStatus.READY
    metadata: dict[str, Any] = Field(default_factory=dict)


class LocalModelRegistry:
    def __init__(self):
        self._models: dict[str, LocalModelInfo] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(
            LocalModelInfo(
                model_id="qwen3:8b",
                name="Qwen3 8B Instruct",
                runtime_name="ollama",
                quantization="Q4_K_M",
                context_length=8192,
                vram_required_gb=5.5,
                ram_required_gb=4.0,
                capabilities=[
                    ModelCapability.TEXT,
                    ModelCapability.REASONING,
                    ModelCapability.CODING,
                    ModelCapability.TOOL_USE
                ]
            )
        )
        self.register(
            LocalModelInfo(
                model_id="llava:7b",
                name="LLaVA 7B Vision",
                runtime_name="ollama",
                quantization="Q4_0",
                context_length=4096,
                vram_required_gb=5.0,
                ram_required_gb=3.5,
                capabilities=[
                    ModelCapability.TEXT,
                    ModelCapability.VISION
                ]
            )
        )

    def register(self, model: LocalModelInfo) -> None:
        self._models[model.model_id] = model

    def unregister(self, model_id: str) -> bool:
        if model_id in self._models:
            del self._models[model_id]
            return True
        return False

    def get(self, model_id: str) -> LocalModelInfo | None:
        return self._models.get(model_id)

    def list_models(self) -> list[LocalModelInfo]:
        return list(self._models.values())

    def find_by_capability(self, capability: ModelCapability) -> list[LocalModelInfo]:
        return [m for m in self._models.values() if capability in m.capabilities and m.status == ModelStatus.READY]