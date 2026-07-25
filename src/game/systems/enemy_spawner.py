"""Time-based virus spawner. Spawn spots avoid the core's sync zone and a radius
around the player, so viruses never appear on top of either; the cadence, the
retry cap and the random point rule are shared with the fragment spawner."""

from __future__ import annotations

import random
from dataclasses import dataclass

import pygame

from game import config
from game.entities.core import Core
from game.entities.enemy import Virus
from game.systems.spawn_common import SPAWN_ATTEMPTS, TimedSpawner, random_point

_MIN_PLAYER_DIST = 300.0


@dataclass
class EnemySpawner(TimedSpawner):
    interval: float = config.VIRUS_SPAWN_INTERVAL
    max_enemies: int = config.VIRUS_SPAWN_MAX

    def update(
        self,
        dt: float,
        enemies: list[Virus],
        player_pos: pygame.Vector2,
        core: Core,
        rng: random.Random,
    ) -> Virus | None:
        if not self.is_due(dt):
            return None
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
        for _ in range(SPAWN_ATTEMPTS):
            point = random_point(rng)
            if core.pos.distance_to(point) < core.sync_radius + config.VIRUS_RADIUS:
                continue
            if player_pos.distance_to(point) < _MIN_PLAYER_DIST:
                continue
            return point
        return None
