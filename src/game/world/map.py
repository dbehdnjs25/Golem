"""The world map: a circle, a central grassland, and a ring split into sectors.

Pure data with pure methods. It holds no pygame surface, mutates nothing, and
takes its randomness as an injected ``random.Random`` -- so a seed reproduces a
map exactly, and every question it answers is testable headlessly.

The biome a point belongs to is computed from its distance and angle, not looked
up in a grid. There is no map file to load and none to ship: ``MAP_RADIUS`` and
``GRASSLAND_RADIUS`` are the whole terrain description.

``rotation`` decides which way the ring faces. Randomising it in ``create``
makes each run's layout different, which is what gives the temple locators a job
-- set it to 0.0 to pin the layout instead. Nothing else changes.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from game import config
from game.world.biomes import GRASSLAND, RING_BIOMES, Biome


@dataclass(frozen=True)
class WorldMap:
    radius: float = config.MAP_RADIUS
    grassland_radius: float = config.GRASSLAND_RADIUS
    rotation: float = 0.0  # degrees; where the first ring sector starts

    @classmethod
    def create(cls, rng: random.Random) -> WorldMap:
        return cls(rotation=rng.uniform(0.0, 360.0))

    @property
    def center(self) -> pygame.Vector2:
        # A fresh vector every call: the map is frozen, and handing out a shared
        # mutable Vector2 would let a caller move the centre of the world.
        return pygame.Vector2(self.radius, self.radius)

    @property
    def sector_degrees(self) -> float:
        return 360.0 / config.BIOME_COUNT

    def contains(self, point: pygame.Vector2) -> bool:
        return self.center.distance_to(point) <= self.radius

    def distance_fraction(self, point: pygame.Vector2) -> float:
        """0.0 at the core, 1.0 at the map edge. Clamped, never above 1."""
        return min(1.0, self.center.distance_to(point) / self.radius)

    def biome_at(self, point: pygame.Vector2) -> Biome | None:
        """The biome under ``point``, or None outside the map circle."""
        offset = point - self.center
        distance = offset.length()
        if distance > self.radius:
            return None
        if distance <= self.grassland_radius:
            return GRASSLAND
        degrees = math.degrees(math.atan2(offset.y, offset.x))
        index = int(((degrees - self.rotation) % 360.0) // self.sector_degrees)
        # A point landing exactly on 360.0 would index past the end after the
        # modulo's rounding; clamping costs nothing and cannot surprise anyone.
        return RING_BIOMES[min(index, len(RING_BIOMES) - 1)]
