"""Pure tests for the user-defined meal-slot helpers."""
from types import SimpleNamespace

from backend.food.slots import (
    DEFAULT_MEAL_SLOTS,
    allowed_slot_keys,
    effective_slots,
    normalize_slots,
    slot_out_list,
)


def _item(key=None, label=None):
    return SimpleNamespace(key=key, label=label)


def test_effective_slots_defaults_when_empty():
    slots = effective_slots(None)
    assert [s["key"] for s in slots] == list(DEFAULT_MEAL_SLOTS)
    assert all(s["label"] is None for s in slots)


def test_normalize_generates_key_for_new_custom_and_keeps_builtins():
    out = normalize_slots(
        [_item(key="breakfast"), _item(label="Pre-Workout"), _item(key="lunch")]
    )
    keys = [s["key"] for s in out]
    # built-ins preserved, custom gets a generated key, missing built-ins appended
    assert "breakfast" in keys and "lunch" in keys and "dinner" in keys and "snack" in keys
    custom = [s for s in out if s["key"].startswith("custom_")]
    assert len(custom) == 1
    assert custom[0]["label"] == "Pre-Workout"


def test_normalize_preserves_existing_custom_key_on_rename():
    out = normalize_slots([_item(key="custom_abc12345", label="Renamed")])
    custom = [s for s in out if s["key"].startswith("custom_")]
    assert custom[0]["key"] == "custom_abc12345"
    assert custom[0]["label"] == "Renamed"


def test_normalize_drops_custom_without_label_and_caps_count():
    out = normalize_slots([_item(label="")] + [_item(label=f"c{i}") for i in range(20)])
    customs = [s for s in out if s["key"].startswith("custom_")]
    assert len(customs) == 8  # MAX_CUSTOM_SLOTS


def test_allowed_slot_keys_includes_custom():
    stored = normalize_slots([_item(key="breakfast"), _item(label="Snack 2")])
    keys = allowed_slot_keys(stored)
    assert "breakfast" in keys
    assert any(k.startswith("custom_") for k in keys)
    assert "nope" not in keys


def test_slot_out_list_flags_builtin():
    stored = normalize_slots([_item(label="Second Dinner")])
    out = {s["key"]: s for s in slot_out_list(stored)}
    assert out["breakfast"]["builtin"] is True
    custom = next(s for s in slot_out_list(stored) if not s["builtin"])
    assert custom["label"] == "Second Dinner"
