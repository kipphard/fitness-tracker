"""User-defined meal slots.

The four built-in slots (breakfast/lunch/dinner/snack) are always present and translated in the
UI; users can add their own named slots and reorder / rename / delete the ones they added. The
ordered list is stored per-user on ``Settings.meal_slots`` as
``[{"key": str, "label": str | None}]``, where a null label marks a built-in (its display name
comes from i18n). A ``None``/empty stored value means "just the defaults".

Custom slots carry a stable generated key (``custom_<hex>``) that is independent of the label, so
renaming or reordering a slot never orphans the diary entries logged under it.
"""
from __future__ import annotations

import uuid

DEFAULT_MEAL_SLOTS: tuple[str, ...] = ("breakfast", "lunch", "dinner", "snack")
_BUILTIN = frozenset(DEFAULT_MEAL_SLOTS)
_CUSTOM_PREFIX = "custom_"
MAX_CUSTOM_SLOTS = 8
MAX_LABEL_LEN = 40


def default_slot_list() -> list[dict]:
    return [{"key": k, "label": None} for k in DEFAULT_MEAL_SLOTS]


def effective_slots(stored: list | None) -> list[dict]:
    """The user's slot list to render: the stored order (built-ins get a null label + i18n name,
    customs keep their label), with any missing built-in appended so all four stay available."""
    if not stored:
        return default_slot_list()
    out: list[dict] = []
    seen: set[str] = set()
    for item in stored:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        if not key or key in seen:
            continue
        if key in _BUILTIN:
            seen.add(key)
            out.append({"key": key, "label": None})
        elif key.startswith(_CUSTOM_PREFIX):
            label = str(item.get("label") or "").strip()
            if not label:
                continue
            seen.add(key)
            out.append({"key": key, "label": label[:MAX_LABEL_LEN]})
    for k in DEFAULT_MEAL_SLOTS:
        if k not in seen:
            out.append({"key": k, "label": None})
    return out


def _new_key(seen: set[str]) -> str:
    while True:
        key = _CUSTOM_PREFIX + uuid.uuid4().hex[:8]
        if key not in seen:
            return key


def normalize_slots(items: list) -> list[dict]:
    """Turn a PUT payload (items with ``.key`` / ``.label``) into the storable ordered list.
    Built-ins are kept by key (label dropped — it's translated); custom items keep an existing
    ``custom_`` key or get a fresh one and require a non-empty label. Duplicates are dropped, the
    custom count is capped, and every built-in is guaranteed present."""
    out: list[dict] = []
    seen: set[str] = set()
    custom_count = 0
    for item in items:
        key = str(getattr(item, "key", None) or "").strip()
        label = str(getattr(item, "label", None) or "").strip()
        if key in _BUILTIN:
            if key in seen:
                continue
            seen.add(key)
            out.append({"key": key, "label": None})
        else:
            if not label or custom_count >= MAX_CUSTOM_SLOTS:
                continue
            new_key = (
                key if key.startswith(_CUSTOM_PREFIX) and key not in seen else _new_key(seen)
            )
            seen.add(new_key)
            out.append({"key": new_key, "label": label[:MAX_LABEL_LEN]})
            custom_count += 1
    for k in DEFAULT_MEAL_SLOTS:
        if k not in seen:
            out.append({"key": k, "label": None})
    return out


def allowed_slot_keys(stored: list | None) -> set[str]:
    """Slot keys a diary entry may use for this user (built-ins + their custom slots)."""
    return {s["key"] for s in effective_slots(stored)}


def slot_out_list(stored: list | None) -> list[dict]:
    """``effective_slots`` annotated with a ``builtin`` flag, for the API response."""
    return [
        {"key": s["key"], "label": s["label"], "builtin": s["key"] in _BUILTIN}
        for s in effective_slots(stored)
    ]
