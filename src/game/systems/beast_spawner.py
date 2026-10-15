"""Night-time animal spawner.

They turn up near the player but never inside the ward, so the safe ground
stays safe and the walk out of it does not. Before the core is lit there is no
ward to stand
outside of, and the rule simply reads as "near the player".

Nothing comes out in daylight, but nothing already out disappears at sunrise
either -- a wolf that evaporates when the sun comes up is a timer, not an
animal.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from game import config
from game.entities.beast import BEAST_KINDS, Beast
from game.entities.core import Core
from game.systems.spawn_common import SPAWN_ATTEMPTS, TimedSpawner
from game.world.map import WorldMap


@dataclass
class BeastSpawner(TimedSpawner):
    interval: float = config.BEAST_SPAWN_INTERVAL
    max_beasts: int = config.BEAST_SPAWN_MAX

    def update(
        self,
        dt: float,
        beasts: list[Beast],
        player_pos: pygame.Vector2,
        core: Core,
        rng: random.Random,
        world: WorldMap,
        night: bool,
    ) -> Beast | None:
        if not self.is_due(dt):
            return None
        if not night:
            return None
        if len(beasts) >= self.max_beasts:
            return None
        spot = self._find_spot(player_pos, core, rng, world)
        if spot is None:
            return None
        beast = Beast(pos=spot, kind=rng.choice(BEAST_KINDS))
        beasts.append(beast)
        return beast

    def _find_spot(
        self,
        player_pos: pygame.Vector2,
        core: Core,
        rng: random.Random,
        world: WorldMap,
    ) -> pygame.Vector2 | None:
        """Near the player, but never inside the ward.

        One rule, two behaviours. Stand in the ward and the only places that
        satisfy it are out on its rim, which is the spec's "they mass around
        the ward". Walk out to mine and they turn up around you instead, which
        is what makes the trip out the thing they tax.

        An earlier version pinned them to the ward's rim always, and then a
        player gathering far out was bothered by nothing at all -- the animals
        were dutifully gathering twenty thousand units behind them.
        """
        for _ in range(SPAWN_ATTEMPTS):
            angle = rng.uniform(0.0, 2 * math.pi)
            step = pygame.Vector2(math.cos(angle), math.sin(angle))
            point = player_pos + step * rng.uniform(config.BEAST_RING / 2, config.BEAST_RING)
            if not world.contains(point) or core.is_in_ward(point):
                continue
            return point
        return None
