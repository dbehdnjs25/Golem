"""What the player has learned.

Learning is free and permanent: open a ruin, read what is inside, and it is
yours for the rest of the run. Nothing is spent and nothing can be lost.

The cost lives in the carving instead -- see ``items/engraving``. That split is
the spec's, and it is what makes a glyph a collectible rather than a
consumable: the drawing is knowledge, the chisel is the price of using it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game.items.glyphs import GLYPHS, Glyph
from game.world.biomes import Biome


@dataclass
class Grimoire:
    learned: set[str] = field(default_factory=set)

    def knows(self, glyph: Glyph) -> bool:
        return glyph.key in self.learned

    def learn(self, glyph: Glyph) -> bool:
        """Take it in. False if it was already known.

        Two ruins can hold the same drawing, and the second must not read as a
        find -- the player should be told they already had it.
        """
        if self.knows(glyph):
            return False
        self.learned.add(glyph.key)
        return True

    def known(self, biome: Biome | None = None) -> tuple[Glyph, ...]:
        """Everything learned, in catalogue order; optionally one biome's.

        Catalogue order rather than the order they were found, so the list on
        screen does not reshuffle itself every time something new turns up.
        """
        found = tuple(g for g in GLYPHS if self.knows(g))
        if biome is None:
            return found
        return tuple(g for g in found if g.biome is biome)
