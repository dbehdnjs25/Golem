"""Pointing at a temple without giving it away.

A detector answers with a bearing and a WORD. Never a number: a number would
make the random placement pointless, because the player would walk the bearing
watching a counter tick down, which is a puzzle with exactly one move in it.
A word leaves the last stretch to actually looking.

One per ring biome, made of that biome's own material, and it points at that
biome's temple and nothing else -- so finding the fifth temple means having
mined in the fifth biome first.

Pure. The temple sites are handed in rather than looked up, because the map
generates them from a seed and this has no business owning that.
"""

from __future__ import annotations

import math

import pygame

from game import config
from game.items.item_kinds import (
    BOG_DETECTOR,
    BURNT_FOREST_DETECTOR,
    SNOWFIELD_DETECTOR,
    WASTELAND_DETECTOR,
    WIND_DETECTOR,
    ItemKind,
)
from game.world.biomes import (
    BOG,
    BURNT_FOREST,
    RING_BIOMES,
    SNOWFIELD,
    WASTELAND,
    WIND_PLATEAU,
    Biome,
)
from game.world.map import WorldMap

DETECTOR_OF: dict[Biome, ItemKind] = {
    BURNT_FOREST: BURNT_FOREST_DETECTOR,
    SNOWFIELD: SNOWFIELD_DETECTOR,
    WIND_PLATEAU: WIND_DETECTOR,
    BOG: BOG_DETECTOR,
    WASTELAND: WASTELAND_DETECTOR,
}

_BIOME_OF: dict[ItemKind, Biome] = {item: biome for biome, item in DETECTOR_OF.items()}


def biome_of(kind: ItemKind) -> Biome | None:
    """Which biome this item detects, or None if it is not a detector."""
    return _BIOME_OF.get(kind)


def temple_for(
    kind: ItemKind, world: WorldMap, sites: tuple[pygame.Vector2, ...]
) -> pygame.Vector2 | None:
    """The temple this detector points at.

    ``sites`` comes back from ``WorldMap.temple_sites`` in ``RING_BIOMES``
    order, so the index is the biome's place in that tuple.
    """
    biome = biome_of(kind)
    if biome is None:
        return None
    return sites[RING_BIOMES.index(biome)]


def bearing(here: pygame.Vector2, there: pygame.Vector2) -> float:
    """Degrees from ``here`` to ``there``, 0 to 360.

    Standing exactly on it answers zero rather than dividing by nothing: a
    detector that crashes when it finally works would be a cruel joke.
    """
    offset = there - here
    if offset.length_squared() == 0:
        return 0.0
    return math.degrees(math.atan2(offset.y, offset.x)) % 360.0


def rough_distance(here: pygame.Vector2, there: pygame.Vector2) -> str:
    """How far, in words. See the module docstring for why not a number."""
    gap = here.distance_to(there)
    for word, bound in zip(config.DISTANCE_WORDS, config.DISTANCE_BANDS, strict=False):
        if gap < bound:
            return word
    return config.DISTANCE_WORDS[-1]
