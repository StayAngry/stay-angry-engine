"""Common AI Provider Contracts, Capabilities, Requests, and Normalized Errors."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class AICapability(str, Enum):
    TEXT = "TEXT"
    STRUCTURED_OUTPUT = "STRUCTURED_OUTPUT"
    VISION = "VISION"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    EMBEDDING = "EMBEDDING"
    REASONING = "REASONING"
    TOOL_USE = "TOOL_USE"


class ProviderState(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    MISCONFIGURED = "MISCONFIGURED"
    UNKNOWN = "UNKNOWN"


class ErrorCategory(str, Enum):
    AUTHENTICATION = "AUTHENTICATION"
    QUOTA_OR_RATE_LIMIT = "QUOTA_OR_RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    CONNECTION_FAILURE = "CONNECTION_FAILURE"
    UNSUPPORTED_CAPABILITY = "UNSUPPORTED_CAPABILITY"
    RUNTIME_MISCONFIGURED = "RUNTIME_MISCONFIGURED"
    SERVER_ERROR = "SERVER_ERROR"
    UNKNOWN = "UNKNOWN"


class ProviderError(Exception):
    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        provider_name: str,
        is_transient: bool = False,
        raw_error: Any = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.provider_name = provider_name
        self.is_transient = is_transient
        self.raw_error = raw_error


class ProviderHealth(BaseModel):
    provider_name: str
    state: ProviderState
    is_available: bool
    status_message: str
    model_name: str
    supported_capabilities: list[AICapability] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AIRequest(BaseModel):
    prompt: str
    system_instruction: str | None = None
    required_capabilities: list[AICapability] = Field(default_factory=lambda: [AICapability.TEXT])
    temperature: float = 0.7
    max_tokens: int | None = None
    timeout_seconds: float = 30.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class AIResponse(BaseModel):
    success: bool
    content: str | None = None
    provider_name: str
    model_name: str
    error: str | None = None
    error_category: ErrorCategory | None = None
    duration_seconds: float = 0.0
    usage: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseAIProvider(ABC):
    provider_name: str
    is_local: bool = False

    @abstractmethod
    def get_supported_capabilities(self) -> list[AICapability]:
        pass

    @abstractmethod
    async def check_health(self) -> ProviderHealth:
        pass

    @abstractmethod
    async def generate(self, request: AIRequest) -> AIResponse:
        pass