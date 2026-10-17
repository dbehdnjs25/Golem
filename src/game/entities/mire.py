"""A patch of standing mire, soft enough to wade but not to hurry through.

Terrain, like the lava pools in the burnt forest, and the same shape of thing:
placed once from the world's seed, never moving, with no opinion from the ward.

What it takes is BREATH, and only from someone who is moving. Standing still
costs nothing -- but nothing comes back either, because a mire holds the
recovery off regardless, and once the breath is gone it starts on blood.
There is no waiting one out: the way through is out of it, or a meal.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config


@dataclass(frozen=True)
class Mire:
    pos: pygame.Vector2
    radius: float = config.MIRE_RADIUS_MIN

    def holds(self, point: pygame.Vector2) -> bool:
        return self.pos.distance_to(point) < self.radius
