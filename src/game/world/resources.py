"""What a mined node yields, as a function of how far out it is.

Pure. The distance fraction comes from ``WorldMap.distance_fraction`` -- 0.0 at
the core, 1.0 at the map edge -- and the randomness is injected, so a seed
reproduces a world's ore exactly.

The bands are keyed to the map's own radii rather than to bare numbers: the
grassland's rim moves if ``GRASSLAND_RADIUS`` moves, and zinc moves with it.
"""

from __future__ import annotations

import random

from game import config
from game.items.item_kinds import COPPER_ORE, GOLD_ORE, IRON_ORE, STONE, WOOD, ZINC_ORE, ItemKind

_GRASSLAND_EDGE = config.GRASSLAND_RADIUS / config.MAP_RADIUS
_INNER_GRASSLAND = _GRASSLAND_EDGE / 2
_INNER_RING = _GRASSLAND_EDGE + (1.0 - _GRASSLAND_EDGE) / 2

# (upper bound of the band, ((kind, weight), ...)). Read top to bottom; the first
# band whose bound the fraction falls under wins.
#
# Gold is a ring tier and never shows up in the grassland. Zinc is the opposite:
# it lives ONLY on the grassland's rim, so brass costs a trip to the edge of the
# safe land rather than a trip into a biome.
_BANDS: tuple[tuple[float, tuple[tuple[ItemKind, int], ...]], ...] = (
    (_INNER_GRASSLAND, ((STONE, 70), (COPPER_ORE, 30))),
    (_GRASSLAND_EDGE, ((STONE, 40), (COPPER_ORE, 35), (IRON_ORE, 20), (ZINC_ORE, 5))),
    (_INNER_RING, ((STONE, 20), (COPPER_ORE, 25), (IRON_ORE, 35), (GOLD_ORE, 20))),
    (1.01, ((STONE, 10), (COPPER_ORE, 15), (IRON_ORE, 35), (GOLD_ORE, 40))),
)


def ore_at(fraction: float, rng: random.Random) -> ItemKind:
    """What a node at ``fraction`` of the way to the map edge yields."""
    for bound, table in _BANDS:
        if fraction < bound:
            kinds = [kind for kind, _ in table]
            weights = [weight for _, weight in table]
            return rng.choices(kinds, weights=weights, k=1)[0]
    raise AssertionError(f"no ore band covers {fraction}")  # pragma: no cover


def node_at(fraction: float, rng: random.Random) -> ItemKind:
    """What a node at ``fraction`` of the way to the map edge turns out to be.

    Trees are a flat share at every distance rather than a row on the ore
    table. Folding them in would make deep ground grow fewer trees, which is
    backwards: distance decides ore QUALITY, and wood is wood wherever it is.
    """
    if rng.random() < config.TREE_SHARE:
        return WOOD
    return ore_at(fraction, rng)
