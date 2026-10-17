"""A sheet of bare ice, where the snowfield's drifts have blown clear.

Terrain, like the lava and the mires and the chasms: placed once from the
world's seed, never moving.

What it takes away is GRIP. Nothing else on the map does that -- lava blocks
the way, a chasm drops you, a mire takes your breath and the wasteland will
not let you leave. Ice simply will not let you stop.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config


@dataclass(frozen=True)
class IceSheet:
    pos: pygame.Vector2
    radius: float = config.ICE_RADIUS_MIN

    def holds(self, point: pygame.Vector2) -> bool:
        return self.pos.distance_to(point) < self.radius
