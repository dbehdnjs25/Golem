"""What a dead boss hands over.

Three things, kept apart on purpose:

- the SUPREME GLYPH, learned on the spot. The spec's rule for this whole step
  is that the thing done to you becomes the thing in your hand, so the glyph a
  boss gives is the trick it was throwing, under the same name
- the SIGIL, a thing to carry. The cap it opens is granted at the core, so a
  victory is a trip home rather than a number that rises wherever the player
  happened to be standing
- its biome's GOLEMS, which start turning up in raids -- handled by
  ``enemy.raid_kinds``, since what a raid is made of is the spawner's business

Pure lookups. Nothing here changes anything; the caller decides what to do with
what it is told.
"""

from __future__ import annotations

from game.entities.boss import BossKind
from game.items.glyphs import SUPREME, Glyph, glyphs_of
from game.items.item_kinds import CORE_SIGIL, ItemKind


def glyph_of(kind: BossKind) -> Glyph:
    """The supreme glyph of this boss's element."""
    return next(g for g in glyphs_of(kind.biome) if g.tier == SUPREME)


def drop_of(kind: BossKind) -> ItemKind:
    """What it leaves on the floor. One sigil, the same from every boss.

    The same item from all five rather than one each: what it opens is the next
    rung of one ladder, and five different sigils would read as five different
    ladders.
    """
    return CORE_SIGIL
