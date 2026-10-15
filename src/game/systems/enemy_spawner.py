"""Time-based golem spawner. Silent until the core is lit.

Golems march on the core, so before it burns there is nothing to march on and
nothing spawns. That leaves the opening quiet enough to gather in -- the threat
before ignition is the wild animals' job, not theirs.

Where they appear depends on the night.

On an ordinary one they turn up near the player, out where the mining is, and
their strength follows how far out that is -- these are the ones a trip into
the ring has to be worth. A player at home meets none of them, which is what
the ward is for.

On a raid night they come at the core instead, on a band outside the ward, and
walk in. That change had to happen: spawning near the player meant a player
standing in a four-thousand-unit ward left nowhere legal to appear, so the
first raid arrived with nobody in it at all.
"""

from __future__ import annotations

import math
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
        raid: bool = False,
    ) -> Golem | None:
        if not self.is_due(dt, config.RAID_SPAWN_INTERVAL if raid else None):
            return None
        if not core.ignited:
            return None  # they come for the core; before it burns there is none
        if len(enemies) >= (config.RAID_SPAWN_MAX if raid else self.max_enemies):
            return None
        spot = (
            self._at_the_ward(core, player_pos, rng, world)
            if raid
            else self._near_player(player_pos, core, rng, world)
        )
        if spot is None:
            return None
        golem = Golem(pos=spot, scale=scale_at(world.distance_fraction(spot)))
        enemies.append(golem)
        return golem

    def _near_player(
        self,
        player_pos: pygame.Vector2,
        core: Core,
        rng: random.Random,
        world: WorldMap,
    ) -> pygame.Vector2 | None:
        """Out where the player is working. Never in the ward, never underfoot."""
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

    def _at_the_ward(
        self,
        core: Core,
        player_pos: pygame.Vector2,
        rng: random.Random,
        world: WorldMap,
    ) -> pygame.Vector2 | None:
        """A raid: they gather just outside the rim and come in at the core."""
        for _ in range(SPAWN_ATTEMPTS):
            angle = rng.uniform(0.0, 2 * math.pi)
            step = pygame.Vector2(math.cos(angle), math.sin(angle))
            # A share of the ward's own reach, so a wider ward means a longer
            # march -- which is part of what the player bought.
            out = core.ward_radius * rng.uniform(1.02, 1.0 + config.GOLEM_APPROACH)
            point = core.pos + step * out
            if not world.contains(point) or core.is_in_ward(point):
                continue
            if player_pos.distance_to(point) < _MIN_PLAYER_DIST:
                continue  # never right on top of someone
            return point
        return None


def scale_at(fraction: float) -> float:
    """How much tougher a golem is at ``fraction`` of the way to the map edge.

    One beside the ward is the table's own numbers; one at the rim is
    ``GOLEM_SCALE_AT_EDGE`` times that. Straight-line, so the player can feel
    the trade as they walk rather than meeting a cliff.
    """
    return 1.0 + (config.GOLEM_SCALE_AT_EDGE - 1.0) * max(0.0, min(1.0, fraction))
