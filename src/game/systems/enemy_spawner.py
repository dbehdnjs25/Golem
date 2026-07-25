"""Time-based virus spawner. Randomness comes from an injected ``random.Random``
so tests are deterministic. Spawn spots avoid the core's sync zone and a radius
around the player; a capped retry count prevents an infinite loop."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import pygame

from game import config
from game.entities.core import Core
from game.entities.enemy import Virus

_MARGIN = 64
_SPAWN_ATTEMPTS = 20
_MIN_PLAYER_DIST = 300.0


@dataclass
class EnemySpawner:
    interval: float = config.VIRUS_SPAWN_INTERVAL
    max_enemies: int = config.VIRUS_SPAWN_MAX
    _accumulator: float = field(default=0.0, init=False)

    def update(
        self,
        dt: float,
        enemies: list[Virus],
        player_pos: pygame.Vector2,
        core: Core,
        rng: random.Random,
    ) -> Virus | None:
        self._accumulator += dt
        if self._accumulator < self.interval:
            return None
        self._accumulator -= self.interval
        if len(enemies) >= self.max_enemies:
            return None
        spot = self._find_spot(player_pos, core, rng)
        if spot is None:
            return None
        virus = Virus(pos=spot)
        enemies.append(virus)
        return virus

    def _find_spot(
        self,
        player_pos: pygame.Vector2,
        core: Core,
        rng: random.Random,
    ) -> pygame.Vector2 | None:
        for _ in range(_SPAWN_ATTEMPTS):
            point = pygame.Vector2(
                rng.uniform(_MARGIN, config.WORLD_WIDTH - _MARGIN),
                rng.uniform(_MARGIN, config.WORLD_HEIGHT - _MARGIN),
            )
            if core.pos.distance_to(point) < core.sync_radius + config.VIRUS_RADIUS:
                continue
            if player_pos.distance_to(point) < _MIN_PLAYER_DIST:
                continue
            return point
        return None
