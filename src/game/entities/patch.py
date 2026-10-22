"""Ground a gimmick left behind, which fades.

Three kinds, all the same shape: a circle with a clock on it. Burning ground
sets you alight, frost takes your footing, sludge takes your breath -- the same
three things the burnt forest, the snowfield and the bog already do, except
these follow the fight instead of lying where the world put them.

Kept apart from the permanent terrain on purpose. Pushed into those lists, a
long fight would quietly grow the map a dozen new lava pools that never cool.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config

BURNING = "burning"
FROST = "frost"
SLUDGE = "sludge"


@dataclass
class Patch:
    pos: pygame.Vector2
    kind: str
    radius: float = config.PATCH_RADIUS
    ttl: float = config.PATCH_SECONDS

    @property
    def spent(self) -> bool:
        return self.ttl <= 0

    def holds(self, point: pygame.Vector2) -> bool:
        return self.pos.distance_to(point) < self.radius
