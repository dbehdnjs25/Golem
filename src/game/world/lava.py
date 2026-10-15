"""Where the lava stands.

Only in the burnt forest, which is what the burnt forest IS -- anywhere else
it would be a hazard with no story behind it.

Pools never overlap. Two that merged would read as one strangely-shaped pool,
and the obsidian belt that hangs off each would double up along the seam.

Reproducible from a seed, like the temples and the ruins.
"""

from __future__ import annotations

import math
import random

import pygame

from game import config
from game.entities.lava import LavaPool
from game.world.biomes import BURNT_FOREST
from game.world.map import WorldMap

_ATTEMPTS = 400


def place(world: WorldMap, rng: random.Random) -> list[LavaPool]:
    """Pour the pools. Angles are tried and rejected rather than aimed.

    Which angle the burnt forest occupies moves with the map's rotation, so
    retrying is cheaper and harder to get wrong than re-deriving the sector.
    """
    pools: list[LavaPool] = []
    wanted = rng.randint(config.LAVA_POOLS_MIN, config.LAVA_POOLS_MAX)
    for _ in range(_ATTEMPTS):
        if len(pools) >= wanted:
            break
        radius = rng.uniform(config.LAVA_RADIUS_MIN, config.LAVA_RADIUS_MAX)
        reach = world.grassland_radius + world.ring_width * rng.uniform(0.1, 0.92)
        radians = math.radians(rng.uniform(0.0, 360.0))
        spot = pygame.Vector2(
            world.center.x + math.cos(radians) * reach,
            world.center.y + math.sin(radians) * reach,
        )
        if world.biome_at(spot) is not BURNT_FOREST:
            continue
        # Clear of every other pool by both radii AND the obsidian belt, so the
        # belts cannot run into each other either.
        gap = radius + config.OBSIDIAN_BELT
        if any(p.pos.distance_to(spot) <= p.radius + gap for p in pools):
            continue
        pools.append(LavaPool(pos=spot, radius=radius))
    return pools


def burns(point: pygame.Vector2, pools: list[LavaPool]) -> bool:
    return any(pool.holds(point) for pool in pools)
