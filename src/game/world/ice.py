"""Where the ice lies.

Only in the snowfield. Reproducible from a seed, and never overlapping -- two
merged sheets would read as one oddly-shaped sheet, and the rim is what a
player has to judge before committing to a run across.
"""

from __future__ import annotations

import math
import random

import pygame

from game import config
from game.entities.ice_sheet import IceSheet
from game.world.biomes import SNOWFIELD
from game.world.map import WorldMap

_ATTEMPTS = 500


def place(world: WorldMap, rng: random.Random) -> list[IceSheet]:
    """Freeze the sheets. Angles are tried and rejected rather than aimed.

    Which angle the snowfield occupies moves with the map's rotation, so
    retrying is cheaper and harder to get wrong than re-deriving the sector.
    """
    sheets: list[IceSheet] = []
    wanted = rng.randint(config.ICE_MIN, config.ICE_MAX)
    for _ in range(_ATTEMPTS):
        if len(sheets) >= wanted:
            break
        radius = rng.uniform(config.ICE_RADIUS_MIN, config.ICE_RADIUS_MAX)
        reach = world.grassland_radius + world.ring_width * rng.uniform(0.08, 0.94)
        radians = math.radians(rng.uniform(0.0, 360.0))
        spot = pygame.Vector2(
            world.center.x + math.cos(radians) * reach,
            world.center.y + math.sin(radians) * reach,
        )
        if world.biome_at(spot) is not SNOWFIELD:
            continue
        if any(s.pos.distance_to(spot) <= s.radius + radius for s in sheets):
            continue
        sheets.append(IceSheet(pos=spot, radius=radius))
    return sheets


def holds(point: pygame.Vector2, sheets: list[IceSheet]) -> bool:
    return any(sheet.holds(point) for sheet in sheets)
