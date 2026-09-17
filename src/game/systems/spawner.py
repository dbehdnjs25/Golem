"""Time-based fragment spawner. Spawn spots avoid the core's sync zone and
existing fragments; the cadence, the retry cap and the random point rule come
from ``spawn_common`` and are shared with the golem spawner."""

from __future__ import annotations

import random
from dataclasses import dataclass

import pygame

from game import config
from game.entities.core import Core
from game.entities.fragment import Fragment
from game.systems.spawn_common import SPAWN_ATTEMPTS, TimedSpawner, near_player
from game.world.map import WorldMap
from game.world.resources import ore_at


@dataclass
class Spawner(TimedSpawner):
    interval: float = config.SPAWN_INTERVAL
    max_fragments: int = config.SPAWN_MAX

    def update(
        self,
        dt: float,
        fragments: list[Fragment],
        core: Core,
        rng: random.Random,
        world: WorldMap,
        player_pos: pygame.Vector2,
    ) -> Fragment | None:
        if not self.is_due(dt):
            return None
        if len(fragments) >= self.max_fragments:
            return None
        spot = self._find_spot(fragments, core, rng, world, player_pos)
        if spot is None:
            return None
        fragment = Fragment(pos=spot, kind=ore_at(world.distance_fraction(spot), rng))
        fragments.append(fragment)
        return fragment

    def _find_spot(
        self,
        fragments: list[Fragment],
        core: Core,
        rng: random.Random,
        world: WorldMap,
        player_pos: pygame.Vector2,
    ) -> pygame.Vector2 | None:
        for _ in range(SPAWN_ATTEMPTS):
            point = near_player(player_pos, rng, world)
            if point is None:
                continue
            if core.pos.distance_to(point) < core.sync_radius + config.FRAGMENT_RADIUS:
                continue
            too_close = any(
                f.pos.distance_to(point) < config.FRAGMENT_RADIUS * 2 for f in fragments
            )
            if too_close:
                continue
            return point
        return None
