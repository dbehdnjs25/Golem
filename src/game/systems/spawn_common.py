"""Machinery shared by the time-based spawners. Keeping the interval accumulator
and the "random spawnable point" rule in one place means the fragment and golem
spawners cannot drift apart on cadence or on which part of the world is usable.
Randomness stays injected (``random.Random``) so spawns remain deterministic."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import pygame

from game import config

MARGIN = 64  # keep spawns clear of the world edge
SPAWN_ATTEMPTS = 20  # capped retries so a saturated world cannot hang the loop


def random_point(rng: random.Random) -> pygame.Vector2:
    """A uniformly random world point, inset by ``MARGIN`` on every side."""
    return pygame.Vector2(
        rng.uniform(MARGIN, config.WORLD_WIDTH - MARGIN),
        rng.uniform(MARGIN, config.WORLD_HEIGHT - MARGIN),
    )


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
