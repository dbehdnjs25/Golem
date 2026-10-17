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
from game.items.item_kinds import (
    COPPER_ORE,
    GOLD_ORE,
    GRASS,
    IRON_ORE,
    PEBBLE,
    STONE,
    TWIG,
    WOOD,
    ZINC_ORE,
    ItemKind,
)
from game.world.biomes import Biome

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


# Out in the ring, the biome decides rather than the distance. Every sector of
# the ring is equally far from home, so a distance band there would be the same
# table five times over -- and then the only thing separating four of the
# biomes would be the name of a six-percent rock.
#
# What each is FOR:
#   burnt forest  gold and iron, and obsidian from the lava's rim
#   snowfield     the place to come for iron
#   wind plateau  the place to come for gold
#   bog           copper by the bucket, which the first smelting eats
#   wasteland     poor ground, and the thunder stone that pays for the trip
_RING_ORE: dict[str, tuple[tuple[ItemKind, int], ...]] = {
    "burnt_forest": ((STONE, 10), (COPPER_ORE, 15), (IRON_ORE, 35), (GOLD_ORE, 40)),
    "snowfield": ((STONE, 10), (COPPER_ORE, 15), (IRON_ORE, 55), (GOLD_ORE, 20)),
    "wind_plateau": ((STONE, 10), (COPPER_ORE, 10), (IRON_ORE, 20), (GOLD_ORE, 60)),
    "bog": ((STONE, 15), (COPPER_ORE, 50), (IRON_ORE, 25), (GOLD_ORE, 10)),
    "wasteland": ((STONE, 35), (COPPER_ORE, 20), (IRON_ORE, 25), (GOLD_ORE, 20)),
}


def _draw(table: tuple[tuple[ItemKind, int], ...], rng: random.Random) -> ItemKind:
    kinds = [kind for kind, _ in table]
    weights = [weight for _, weight in table]
    return rng.choices(kinds, weights=weights, k=1)[0]


def ore_at(fraction: float, rng: random.Random, biome: Biome | None = None) -> ItemKind:
    """What a node yields: the biome's own table out in the ring, bands at home.

    The grassland keeps its distance bands, which is where "further out is
    better" still means something -- gold does not appear there at all, and
    zinc only on its rim.
    """
    if biome is not None and biome.key in _RING_ORE:
        return _draw(_RING_ORE[biome.key], rng)
    for bound, table in _BANDS:
        if fraction < bound:
            return _draw(table, rng)
    raise AssertionError(f"no ore band covers {fraction}")  # pragma: no cover


LITTER: tuple[ItemKind, ...] = (TWIG, PEBBLE, GRASS)


def node_at(fraction: float, rng: random.Random, biome: Biome | None = None) -> ItemKind:
    """What a node at ``fraction`` of the way to the map edge turns out to be.

    A ring biome yields its own material some of the time, and that is the only
    place any of it comes from. It is scarce next to the ordinary ore because
    it gates a whole second ladder -- it should be worth the trip rather than
    something picked up on the way past.

    Trees and litter are flat shares at every distance rather than rows on the
    ore table. Folding them in would make deep ground grow fewer trees, which
    is backwards: distance decides ore QUALITY, and a branch is a branch
    wherever it fell.

    Litter keeps turning up on purpose. A run that has somehow lost every tool
    can always start again from what is lying on the ground.
    """
    roll = rng.random()
    timber = biome.timber if biome is not None else WOOD
    if roll < config.LITTER_SHARE:
        return rng.choice(LITTER)
    if roll < config.LITTER_SHARE + config.TREE_SHARE:
        # Every biome grows its own. The same share of nodes are trees
        # everywhere -- a burnt forest is not barren, nor a frozen one --
        # but what they turn out to be differs.
        return timber
    # The scattered-material roll is skipped where the trees already ARE the
    # material. Rolling it as well would hand the burnt forest nearly twice the
    # charred wood of any other biome's material, for no reason anyone asked for.
    if biome is not None and biome.material is timber:
        return ore_at(fraction, rng, biome)
    if (
        biome is not None
        and biome.material is not None
        and rng.random() < config.BIOME_MATERIAL_SHARE
    ):
        return biome.material
    return ore_at(fraction, rng, biome)
