"""Where the ground gives out.

Only in the wind plateau: narrow ridges with nothing between them is what that
biome is. Reproducible from a seed, and never overlapping -- two merged holes
would read as one oddly-shaped hole, and the rim is the whole of what a player
reads here.
"""

from __future__ import annotations

import math
import random

import pygame

from game import config
from game.entities.chasm import Chasm
from game.world.biomes import WIND_PLATEAU
from game.world.map import WorldMap

_ATTEMPTS = 500


def place(world: WorldMap, rng: random.Random) -> list[Chasm]:
    """Cut the holes. Angles are tried and rejected rather than aimed.

    Which angle the plateau occupies moves with the map's rotation, so
    retrying is cheaper and harder to get wrong than re-deriving the sector.
    """
    holes: list[Chasm] = []
    wanted = rng.randint(config.CHASMS_MIN, config.CHASMS_MAX)
    for _ in range(_ATTEMPTS):
        if len(holes) >= wanted:
            break
        radius = rng.uniform(config.CHASM_RADIUS_MIN, config.CHASM_RADIUS_MAX)
        reach = world.grassland_radius + world.ring_width * rng.uniform(0.08, 0.94)
        radians = math.radians(rng.uniform(0.0, 360.0))
        spot = pygame.Vector2(
            world.center.x + math.cos(radians) * reach,
            world.center.y + math.sin(radians) * reach,
        )
        if world.biome_at(spot) is not WIND_PLATEAU:
            continue
        if any(h.pos.distance_to(spot) <= h.radius + radius for h in holes):
            continue
        holes.append(Chasm(pos=spot, radius=radius))
    return holes


def over(point: pygame.Vector2, holes: list[Chasm]) -> Chasm | None:
    """The hole this point is over, if any."""
    for hole in holes:
        if hole.holds(point):
            return hole
    return None
