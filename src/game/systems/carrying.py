"""Where a picked-up thing goes.

The backpack takes it. The hotbar only takes it when there is NO backpack at
all -- not when the backpack is merely full.

That asymmetry is the point. The five hotbar slots are the only thing death
spares, so filling them behind the player's back would spend that protection for
them. A full backpack should stop the pickup and send them home.

``store`` and ``room_for`` share the branch on purpose: "you can put it here"
must never disagree with what happens when you do.
"""

from __future__ import annotations

from game.inventory.hotbar import Hotbar
from game.inventory.storage import Container
from game.items.item_kinds import ItemKind


def store(kind: ItemKind, n: int, backpack: Container | None, hotbar: Hotbar) -> int:
    """Put up to ``n`` of ``kind`` away. Return how many actually fit."""
    if backpack is not None:
        return backpack.add(kind, n)
    return hotbar.add(kind, n)


def room_for(kind: ItemKind, backpack: Container | None, hotbar: Hotbar) -> int:
    """How many of ``kind`` would fit, by the same rule ``store`` follows."""
    if backpack is not None:
        return backpack.fits(kind, 1)
    return 1 if hotbar.has_room_for(kind) else 0
