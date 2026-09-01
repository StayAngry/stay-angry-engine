from sae.permissions import PermissionGuard, PermissionLevel, RiskLevel


def test_low_risk_read_permission():
    result = PermissionGuard.evaluate(PermissionLevel.READ, RiskLevel.LOW)
    assert result.allowed is True
    assert result.requires_interactive_confirmation is False


def test_destructive_delete_permission():
    result = PermissionGuard.evaluate(PermissionLevel.DELETE, RiskLevel.HIGH)
    assert result.allowed is True
    assert result.requires_interactive_confirmation is True


def test_system_permission():
    result = PermissionGuard.evaluate(PermissionLevel.SYSTEM, RiskLevel.MEDIUM)
    assert result.allowed is True
    assert result.requires_interactive_confirmation is True