"""A pool of lava, standing where the forest burned.

Terrain, not a creature: it never moves, never chases, and the ward has no
opinion about it. That is exactly why the spec put this biome at the easy end
-- "lava blocks the way, a visible hazard" -- a danger you can see from a
distance and decide about is the kindest kind there is.

The obsidian belt hangs off these; see ``world/lava``.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config


@dataclass(frozen=True)
class LavaPool:
    pos: pygame.Vector2
    radius: float = config.LAVA_RADIUS_MIN

    def holds(self, point: pygame.Vector2) -> bool:
        return self.pos.distance_to(point) < self.radius
