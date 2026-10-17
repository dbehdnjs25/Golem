"""A break in the ground, where the plateau's ridges run out.

The same shape of thing as a lava pool or a mire: placed once from the world's
seed, never moving, with no opinion from the ward.

Falling in hurts and puts you back on the rim. It does NOT keep you -- the
point of a hole is being pushed into one, not dying at the bottom of it, and
the wind boss's shove is what this terrain was laid for.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config


@dataclass(frozen=True)
class Chasm:
    pos: pygame.Vector2
    radius: float = config.CHASM_RADIUS_MIN

    def holds(self, point: pygame.Vector2) -> bool:
        return self.pos.distance_to(point) < self.radius
