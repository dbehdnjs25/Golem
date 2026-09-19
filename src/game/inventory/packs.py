"""Which pack holds how much.

Kept apart from ``item_kinds`` because a slot count is behaviour, not identity:
the catalogue says what exists, this says what wearing one does. Ordinary items
answer 0 here, which is what makes ``is_pack`` a lookup rather than a list of
special cases.
"""

from __future__ import annotations

from game import config
from game.items.item_kinds import LEATHER_PACK, WORN_PACK, ItemKind

PACK_SLOTS: dict[ItemKind, int] = {
    WORN_PACK: config.BACKPACK_SLOTS,
    LEATHER_PACK: config.BACKPACK_SLOTS * 2,
}


def is_pack(kind: ItemKind) -> bool:
    return kind in PACK_SLOTS


def slots_of(kind: ItemKind) -> int:
    return PACK_SLOTS.get(kind, 0)
