"""The glyphs -- the drawings a player finds, learns, and carves.

Two ladders run through this game and they do not mix. The ore grade decides
what a tool can break; a glyph decides what a weapon can throw. A steel pick
does not breathe fire and a fire glyph does not open a gold vein.

There is no matchup table and there will not be one. The spec is explicit: what
drags a player around the ring is a VISIBLE collection, not a hidden multiplier
nobody can see. So an element is strength and spectacle, never scissors-beats-
paper, and there is one fewer table to balance.

Pure data. Knowing a glyph is free and permanent; the cost is in the carving,
which lives in ``items/strokes``.
"""

from __future__ import annotations

from dataclasses import dataclass

from game import config
from game.world.biomes import (
    BOG,
    BURNT_FOREST,
    GRASSLAND,
    SNOWFIELD,
    WASTELAND,
    WIND_PLATEAU,
    Biome,
)

# What a glyph can be carved onto. A weapon already hits; a staff is nothing
# until something is carved on it.
WEAPON = "weapon"
STAFF = "staff"

# Tiers, weakest first. The order of this tuple is the ladder.
BASIC = "basic"
GREATER = "greater"
SUPREME = "supreme"
TIERS: tuple[str, ...] = (BASIC, GREATER, SUPREME)

# Where one is found. FROM_BOSS is unreachable until step 8 -- marked rather
# than omitted, so nothing scatters a supreme glyph in a roadside structure and
# quietly skips the boss that was supposed to guard it.
FROM_STRUCTURE = "structure"
FROM_TEMPLE = "temple"
FROM_BOSS = "boss"


@dataclass(frozen=True)
class Glyph:
    key: str  # stable id, used for saves and comparison
    name: str  # shown to the player
    biome: Biome | None  # None in the grassland, which has no element
    element: str | None  # always its biome's; kept here so callers need not hop
    tier: str
    gimmick: str  # what it DOES, in a word -- two cuts of one gimmick share it
    power: float  # damage added on a weapon, or thrown by a staff
    strain: float  # what a staff pays to throw it; see systems/staff
    fits: frozenset[str]
    source: str


def _ladder(biome: Biome, gimmick: str, names: tuple[str, str, str]) -> tuple[Glyph, ...]:
    """One biome's three glyphs, climbing.

    Power and strain both climb, which is what makes a staff a budget rather
    than a bigger number: the supreme cut hits hardest and empties the staff
    fastest.
    """
    rungs = (
        (BASIC, config.GLYPH_POWER_BASIC, FROM_STRUCTURE),
        (GREATER, config.GLYPH_POWER_GREATER, FROM_TEMPLE),
        (SUPREME, config.GLYPH_POWER_SUPREME, FROM_BOSS),
    )
    return tuple(
        Glyph(
            key=f"{biome.key}_{tier}",
            name=name,
            biome=biome,
            element=biome.element,
            tier=tier,
            gimmick=gimmick,
            power=power,
            strain=power * config.GLYPH_STRAIN_PER_POWER,
            fits=frozenset({WEAPON, STAFF}),
            source=source,
        )
        for (tier, power, source), name in zip(rungs, names, strict=True)
    )


BURNT_GLYPHS = _ladder(BURNT_FOREST, "burn", ("불1", "불2", "불3"))
SNOWFIELD_GLYPHS = _ladder(SNOWFIELD, "chill", ("얼음1", "얼음2", "얼음3"))
WIND_GLYPHS = _ladder(WIND_PLATEAU, "gust", ("바람1", "바람2", "바람3"))
BOG_GLYPHS = _ladder(BOG, "rot", ("독1", "독2", "독3"))
WASTELAND_GLYPHS = _ladder(WASTELAND, "shock", ("번개1", "번개2", "번개3"))

GLYPHS: tuple[Glyph, ...] = (
    *BURNT_GLYPHS,
    *SNOWFIELD_GLYPHS,
    *WIND_GLYPHS,
    *BOG_GLYPHS,
    *WASTELAND_GLYPHS,
)

GLYPH_BY_KEY: dict[str, Glyph] = {glyph.key: glyph for glyph in GLYPHS}


def glyphs_of(biome: Biome | None) -> tuple[Glyph, ...]:
    """Every glyph belonging to ``biome``.

    The grassland has none. It used to hold an elementless pair, which was two
    more shapes to keep straight for a gimmick that was not an element -- and
    the shapes are the part a player has to carry in their head.
    """
    wanted = None if biome is None or biome is GRASSLAND else biome
    return tuple(g for g in GLYPHS if g.biome is wanted)


def basic_glyphs() -> tuple[Glyph, ...]:
    """The ones a structure may hold. Everything else is guarded by step 8."""
    return tuple(g for g in GLYPHS if g.source == FROM_STRUCTURE)
