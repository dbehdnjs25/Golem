"""Whether a thing does anything when it is the thing in your hand.

The hotbar is the hand: the selected slot is what the action key acts with.
Five ways a slot can mean something -- a tool digs, the weapon swings, a
staff throws a drawn shape, a station goes down in front of you, food is
eaten -- and one that means something without being used, a detector, which
points at its temple for as long as it is held.

Everything else is cargo. Stone does nothing when selected and never will,
and a slot holding it is a slot the hand cannot use.

One place, built from the tables that already exist. A list written out by
hand here would be a second copy of five catalogues, and the day a food was
added it would be the stale one.
"""

from __future__ import annotations

from game.inventory.stack import Stack
from game.items.grades import TOOL_ITEMS
from game.items.item_kinds import ItemKind
from game.items.recipes import STATION_OF
from game.items.staff import STAFF_ITEMS
from game.systems.consume import EDIBLE
from game.systems.detector import DETECTOR_OF


def usable_kinds() -> frozenset[ItemKind]:
    """Every item that does something from the hand."""
    return frozenset(
        {
            *TOOL_ITEMS,
            *STAFF_ITEMS,
            *STATION_OF,
            *EDIBLE,
            *DETECTOR_OF.values(),
        }
    )


_USABLE = usable_kinds()


def is_usable(thing: object | None) -> bool:
    """Whether ``thing`` would do anything in the selected slot.

    Anything that is not a stack of items is a tool object -- the weapon --
    and a tool is the one thing the hotbar was always for.
    """
    if thing is None:
        return False
    if not isinstance(thing, Stack):
        return True
    return thing.kind in _USABLE
