"""The catalogue of item kinds. Data only — a frozen row per kind, no behaviour.

Same shape as ``items/tools.py``: the table lives here, the systems that act on
it live in ``systems/`` and ``inventory/``. Adding an item kind is adding a row.

``key`` is the stable identifier that goes into save files; ``name`` is what the
player reads. They are separate so renaming the display text never invalidates a
save.
"""

from __future__ import annotations

from dataclasses import dataclass

from game import config


@dataclass(frozen=True)
class ItemKind:
    key: str  # stable id, used for storage and comparison
    name: str  # shown in the inventory grid
    stack_max: int  # how many fit in one slot
    color: tuple[int, int, int]  # icon colour


FRAGMENT = ItemKind(
    key="fragment",
    name="데이터 조각",
    stack_max=config.STACK_MAX_DEFAULT,
    color=config.FRAGMENT_COLOR,
)

# Draw order for inventory lists. Fixed on purpose: rows must not shuffle under
# the cursor as counts change, or drag targets move while the player is aiming.
CATALOGUE: tuple[ItemKind, ...] = (FRAGMENT,)

ITEM_KINDS: dict[str, ItemKind] = {kind.key: kind for kind in CATALOGUE}
