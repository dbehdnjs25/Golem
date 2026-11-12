"""The staff: what lets a shape become a spell.

Nothing is cut into it. The glyphs live with the player -- in the grimoire and
in their hand -- so a staff holds no magic of its own and is useless without
someone who knows a shape. That is still the spec's line; only where the
knowing lives has moved.

There is one. No grades, because what makes a player better at magic is the
shapes they have found and whether their hand can draw a five-stroke figure
while something is charging them -- and a staff that quietly raised those
numbers would be answering a question the hand is supposed to answer.

What stops the best shape from simply being the right answer is strain. Power
and strain climb together with the rung, so the supreme shape hits hardest and
empties the staff fastest, and the basic one is the only thing that can be
thrown all night. The choice is a budget, and now a hand as well.
"""

from __future__ import annotations

from dataclasses import dataclass

from game import config
from game.items.glyphs import Glyph
from game.items.item_kinds import STAFF_ITEM, ItemKind


@dataclass
class Staff:
    strain: float = 0.0
    lockout: float = 0.0  # seconds left before it will answer again
    name: str = "지팡이"

    @property
    def overloaded(self) -> bool:
        return self.lockout > 0

    @property
    def heat(self) -> float:
        """How full it is, for anything showing it to the player."""
        return min(1.0, self.strain / config.STAFF_STRAIN_MAX)

    def power_of(self, glyph: Glyph) -> float:
        return glyph.power

    def range_of(self) -> float:
        return config.PROJECTILE_TTL

    def fire(self, glyph: Glyph) -> Glyph | None:
        """Throw ``glyph``, and pay for it. None while locked out.

        The strain lands AFTER the throw, so the shot that tips it over still
        goes out -- a staff that silently ate the last one before locking
        would read as a dropped input rather than a cost.
        """
        if self.overloaded:
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
        throw, over and over, and the lockout stops being a setback and becomes
        the normal state.
        """
        if self.overloaded:
            self.lockout = max(0.0, self.lockout - dt)
            if not self.overloaded:
                self.strain = 0.0
            return
        self.strain = max(0.0, self.strain - config.STAFF_COOLING * dt)


# What counts as a staff in hand. One entry, kept as a set so the scene's
# question stays "is this a staff?" rather than "is this THE staff?".
STAFF_ITEMS: frozenset[ItemKind] = frozenset({STAFF_ITEM})
