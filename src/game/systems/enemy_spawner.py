"""Time-based golem spawner. Spawn spots avoid the core's sync zone and a radius
around the player, so golems never appear on top of either; the cadence, the
retry cap and the random point rule are shared with the fragment spawner."""

from __future__ import annotations

import random
from dataclasses import dataclass

import pygame

from game import config
from game.entities.core import Core
from game.entities.enemy import Golem
from game.systems.spawn_common import SPAWN_ATTEMPTS, TimedSpawner, near_player
from game.world.map import WorldMap

_MIN_PLAYER_DIST = 600.0  # never on top of the player, inside SPAWN_RADIUS


@dataclass
class EnemySpawner(TimedSpawner):
    interval: float = config.GOLEM_SPAWN_INTERVAL
    max_enemies: int = config.GOLEM_SPAWN_MAX

    def update(
        self,
        dt: float,
        enemies: list[Golem],
        player_pos: pygame.Vector2,
        core: Core,
        rng: random.Random,
        world: WorldMap,
    ) -> Golem | None:
        if not self.is_due(dt):
            return None
        if len(enemies) >= self.max_enemies:
            return None
        spot = self._find_spot(player_pos, core, rng, world)
        if spot is None:
            return None
        golem = Golem(pos=spot)
        enemies.append(golem)
        return golem

    def _find_spot(
        self,
        player_pos: pygame.Vector2,
        core: Core,
        rng: random.Random,
        world: WorldMap,
    ) -> pygame.Vector2 | None:
        for _ in range(SPAWN_ATTEMPTS):
            point = near_player(player_pos, rng, world)
            if point is None:
                continue
            if core.pos.distance_to(point) < core.sync_radius + config.GOLEM_RADIUS:
                continue
            if player_pos.distance_to(point) < _MIN_PLAYER_DIST:
                continue
            return point
        return None
