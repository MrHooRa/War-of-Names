from types import SimpleNamespace

from app.core.enums import ProtectionType
from app.modules.attacks.protection_service import (
    ADMIN_PROTECTION_SOURCE,
    ATTACK_PARTIAL_PROTECTION_SOURCE,
    record_affects_membership_protection,
    resolve_membership_protection,
)


def _record(protection_type: ProtectionType, source_type: str):
    return SimpleNamespace(protection_type=protection_type, source_type=source_type)


def test_attacker_scoped_partial_does_not_affect_membership_cache():
    record = _record(ProtectionType.PARTIAL, ATTACK_PARTIAL_PROTECTION_SOURCE)

    assert record_affects_membership_protection(record) is False
    assert resolve_membership_protection([record]) == ProtectionType.NONE


def test_global_partial_still_resolves_to_partial():
    record = _record(ProtectionType.PARTIAL, ADMIN_PROTECTION_SOURCE)

    assert record_affects_membership_protection(record) is True
    assert resolve_membership_protection([record]) == ProtectionType.PARTIAL


def test_full_protection_has_precedence_over_partial_records():
    records = [
        _record(ProtectionType.PARTIAL, ADMIN_PROTECTION_SOURCE),
        _record(ProtectionType.PARTIAL, ATTACK_PARTIAL_PROTECTION_SOURCE),
        _record(ProtectionType.FULL, "attack_exposure"),
    ]

    assert resolve_membership_protection(records) == ProtectionType.FULL
