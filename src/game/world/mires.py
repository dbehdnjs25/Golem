"""Where the mires lie.

Only in the bog, which is what makes the bog the bog: the biome around them is
ordinary walking, and the patches are what the spec's drain actually means.

Reproducible from a seed, and never overlapping -- two merged patches would
read as one oddly-shaped patch and the edge is the whole of what a player
reads here.
"""

from __future__ import annotations

import math
import random

import pygame

from game import config
from game.entities.mire import Mire
from game.world.biomes import BOG
from game.world.map import WorldMap

_ATTEMPTS = 400


def place(world: WorldMap, rng: random.Random) -> list[Mire]:
    """Lay the patches down. Angles are tried and rejected rather than aimed.

    Which angle the bog occupies moves with the map's rotation, so retrying is
    cheaper and harder to get wrong than re-deriving the sector here.
    """
    pools: list[Mire] = []
    wanted = rng.randint(config.MIRES_MIN, config.MIRES_MAX)
    for _ in range(_ATTEMPTS):
        if len(pools) >= wanted:
            break
        radius = rng.uniform(config.MIRE_RADIUS_MIN, config.MIRE_RADIUS_MAX)
        reach = world.grassland_radius + world.ring_width * rng.uniform(0.08, 0.94)
        radians = math.radians(rng.uniform(0.0, 360.0))
        spot = pygame.Vector2(
            world.center.x + math.cos(radians) * reach,
            world.center.y + math.sin(radians) * reach,
        )
        if world.biome_at(spot) is not BOG:
            continue
        if any(p.pos.distance_to(spot) <= p.radius + radius for p in pools):
            continue
        pools.append(Mire(pos=spot, radius=radius))
    return pools


def holds(point: pygame.Vector2, pools: list[Mire]) -> bool:
    return any(pool.holds(point) for pool in pools)
