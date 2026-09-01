"""Base tool contracts."""

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field
from sae.permissions import PermissionLevel, RiskLevel
from sae.verification import VerificationResult


class ToolResult(BaseModel):
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    verification: VerificationResult | None = None


class BaseTool(ABC):
    name: str
    description: str
    version: str = "0.1.0"
    permission_level: PermissionLevel
    risk_level: RiskLevel

    @abstractmethod
    def validate_input(self, **kwargs: Any) -> bool:
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        pass