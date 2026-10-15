"""Time-based golem spawner. Silent until the core is lit.

Golems march on the core, so before it burns there is nothing to march on and
nothing spawns. That leaves the opening quiet enough to gather in -- the threat
before ignition is the wild animals' job, not theirs.

Once lit, spawn spots avoid the ward, the core's sync zone and a radius around
the player, so a golem never appears on top of anything; the cadence, the retry
cap and the "near the player" rule are shared with the node spawner.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import pygame

from game import config
from game.entities.core import Core
from game.entities.enemy import PLAIN_GOLEM, Golem
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
        if not core.ignited:
            return None  # they come for the core; before it burns there is none
        if len(enemies) >= self.max_enemies:
            return None
        spot = self._find_spot(player_pos, core, rng, world)
        if spot is None:
            return None
        golem = Golem(pos=spot, scale=scale_at(world.distance_fraction(spot)))
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
            if core.is_in_ward(point):
                continue  # the ward is what the core buys
            if core.pos.distance_to(point) < core.sync_radius + PLAIN_GOLEM.radius:
                continue
            if player_pos.distance_to(point) < _MIN_PLAYER_DIST:
                continue
            return point
        return None


def scale_at(fraction: float) -> float:
    """How much tougher a golem is at ``fraction`` of the way to the map edge.

    One beside the ward is the table's own numbers; one at the rim is
    ``GOLEM_SCALE_AT_EDGE`` times that. Straight-line, so the player can feel
    the trade as they walk rather than meeting a cliff.
    """
    return 1.0 + (config.GOLEM_SCALE_AT_EDGE - 1.0) * max(0.0, min(1.0, fraction))
