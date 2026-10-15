"""The staff: nothing but what is carved on it.

A weapon hits on its own and a glyph makes it hit harder. A staff does not.
With nothing cut into it, it is useless rather than weak -- that is the spec's
line and it is what makes the whole glyph ladder worth climbing.

What stops the best glyph being simply the right answer is strain. Power and
strain climb together, so the supreme cut hits hardest and empties the staff
fastest, and the basic cut is the only one that can be thrown all night. The
choice is a budget, not a number.

Slots come from biome material: a better staff is a staff with more room on
it. Never from the ore grade -- the two ladders stay apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game import config
from game.items.engraving import Engraved
from game.items.glyphs import STAFF, Glyph
from game.items.item_kinds import (
    GREATER_STAFF_ITEM,
    STAFF_ITEM,
    SUPREME_STAFF_ITEM,
    ItemKind,
)

STAFF_SLOTS = 1
GREATER_STAFF_SLOTS = 2
SUPREME_STAFF_SLOTS = 3


@dataclass
class Staff:
    slots: int = STAFF_SLOTS
    engraved: Engraved = field(init=False)
    strain: float = 0.0
    lockout: float = 0.0  # seconds left before it will answer again
    chosen: int = 0
    name: str = "지팡이"

    def __post_init__(self) -> None:
        self.engraved = Engraved(kind=STAFF, slots=self.slots)

    @property
    def overloaded(self) -> bool:
        return self.lockout > 0

    @property
    def ready(self) -> Glyph | None:
        """The glyph it would throw, or None if there is nothing to throw."""
        carved = self.engraved.glyphs
        if not carved or self.overloaded:
            return None
        return carved[min(self.chosen, len(carved) - 1)]

    def choose(self, index: int) -> None:
        """Pick which carved glyph to throw.

        Out of range raises rather than wrapping: wrapping would quietly throw
        the wrong magic, which in a fight is worse than nothing happening.
        """
        if not 0 <= index < len(self.engraved.glyphs):
            raise IndexError(f"no glyph at slot {index}")
        self.chosen = index

    def fire(self) -> Glyph | None:
        """Throw, and pay for it. None if it cannot.

        The strain lands AFTER the throw, so the shot that tips it over still
        goes out -- a staff that silently ate the last shot before locking
        would read as a dropped input.
        """
        glyph = self.ready
        if glyph is None:
            return None
        self.strain += glyph.strain
        if self.strain >= config.STAFF_STRAIN_MAX:
            self.strain = config.STAFF_STRAIN_MAX
            self.lockout = config.STAFF_LOCKOUT
        return glyph

    def update(self, dt: float) -> None:
        """Cool off, and count down a lockout.

        Coming back from an overload drains the strain completely rather than
        resuming where it stopped: otherwise the staff locks again on the next
        shot, over and over, and the lockout stops being a setback and becomes
        the normal state.
        """
        if self.overloaded:
            self.lockout = max(0.0, self.lockout - dt)
            if not self.overloaded:
                self.strain = 0.0
            return
        self.strain = max(0.0, self.strain - config.STAFF_COOLING * dt)


# Which staff item means how much room. Crafting the better one IS the upgrade:
# there is no second step where the player has to install it.
STAFF_KINDS: dict[ItemKind, int] = {
    STAFF_ITEM: STAFF_SLOTS,
    GREATER_STAFF_ITEM: GREATER_STAFF_SLOTS,
    SUPREME_STAFF_ITEM: SUPREME_STAFF_SLOTS,
}
