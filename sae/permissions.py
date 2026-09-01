"""Permission matrix, risk tiers, and authorization evaluation."""

from enum import Enum
from pydantic import BaseModel


class PermissionLevel(str, Enum):
    READ = "READ"
    CREATE = "CREATE"
    MODIFY = "MODIFY"
    DELETE = "DELETE"
    EXECUTE = "EXECUTE"
    NETWORK = "NETWORK"
    SYSTEM = "SYSTEM"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PermissionCheckResult(BaseModel):
    allowed: bool
    requires_interactive_confirmation: bool
    reason: str


class PermissionGuard:
    @staticmethod
    def evaluate(permission: PermissionLevel, risk: RiskLevel) -> PermissionCheckResult:
        if permission in [PermissionLevel.DELETE, PermissionLevel.SYSTEM] or risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            return PermissionCheckResult(
                allowed=True,
                requires_interactive_confirmation=True,
                reason=f"Action requires elevated authorization: Permission={permission.value}, Risk={risk.value}"
            )
        
        return PermissionCheckResult(
            allowed=True,
            requires_interactive_confirmation=False,
            reason="Action permitted within standard execution policy."
        )