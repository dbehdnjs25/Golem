"""The interval accumulator shared by the time-based spawners, plus the retry cap.

Keeping the cadence rule in one place means the node and golem spawners cannot
drift apart on it, and neither can the rule for where a spawn may land.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from game import config
from game.world.map import WorldMap

SPAWN_ATTEMPTS = 20  # capped retries so a saturated world cannot hang the loop


def near_player(
    player_pos: pygame.Vector2,
    rng: random.Random,
    world: WorldMap,
) -> pygame.Vector2 | None:
    """A random point within ``SPAWN_RADIUS`` of the player, or None if off-map.

    The map is far larger than a single trip, so scattering spawns over all of
    it would leave nothing to find. Returning None rather than retrying inside
    keeps the retry budget in one place -- the caller's loop.

    The square root spreads points evenly by area; sampling the radius flat
    would crowd them around the player's feet.
    """
    angle = rng.uniform(0.0, 2 * math.pi)
    distance = config.SPAWN_RADIUS * math.sqrt(rng.random())
    point = pygame.Vector2(
        player_pos.x + math.cos(angle) * distance,
        player_pos.y + math.sin(angle) * distance,
    )
    return point if world.contains(point) else None


@dataclass
class TimedSpawner:
    """Interval accumulator: ``is_due`` returns True once per ``interval`` of dt.

    It subtracts the interval rather than zeroing the accumulator, so leftover
    time carries into the next tick and the spawn rate stays exact under any
    step size."""

    interval: float
    _accumulator: float = field(default=0.0, init=False)

    def is_due(self, dt: float) -> bool:
        self._accumulator += dt
        if self._accumulator < self.interval:
            return False
        self._accumulator -= self.interval
        return True
