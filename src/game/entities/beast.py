"""Wild animals. They hunt the player, never the core.

That is the whole split from a golem: a golem walks past you to reach the core,
an animal is the thing in your way while you are out gathering. They give
materials and nothing else -- no progress is gated behind killing one.

They are also the only thing abroad before the core is lit. Golems wait for
something to march on; these do not, and a night spent out with nowhere to heal
is what makes lighting the core worth doing.

Logic-only, so it is unit-testable headlessly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from game import config
from game.entities.enemy import TARGET_PLAYER, EnemyKind
from game.items.item_kinds import HIDE, RAW_MEAT, ItemKind
from game.world.map import WorldMap


@dataclass(frozen=True)
class BeastKind:
    kind: EnemyKind
    flees: bool  # a rabbit runs; a wolf closes
    drops: tuple[tuple[ItemKind, int], ...]

    @property
    def key(self) -> str:
        return self.kind.key

    @property
    def target(self) -> str:
        return self.kind.target

    @property
    def contact_dps(self) -> float:
        return self.kind.contact_dps


WOLF = BeastKind(
    kind=EnemyKind(
        key="wolf",
        name="늑대",
        target=TARGET_PLAYER,
        hp=24.0,
        speed=175.0,  # under the player's, so a fight is always refusable
        radius=10.0,
        contact_dps=14.0,
        color=(118, 108, 120),
    ),
    flees=False,
    drops=((RAW_MEAT, 2), (HIDE, 1)),
)

RABBIT = BeastKind(
    kind=EnemyKind(
        key="rabbit",
        name="토끼",
        target=TARGET_PLAYER,
        hp=8.0,
        speed=190.0,  # just under the player's: a patient chase wins
        radius=7.0,
        contact_dps=0.0,
        color=(206, 196, 186),
    ),
    flees=True,
    drops=((RAW_MEAT, 1), (HIDE, 1)),
)

BEAST_KINDS: tuple[BeastKind, ...] = (WOLF, RABBIT)


@dataclass
class Beast:
    pos: pygame.Vector2
    kind: BeastKind = WOLF
    hp: float = field(default=0.0)

    def __post_init__(self) -> None:
        if not self.hp:
            self.hp = self.kind.kind.hp

    @property
    def speed(self) -> float:
        return self.kind.kind.speed

    @property
    def radius(self) -> float:
        return self.kind.kind.radius

    @property
    def contact_dps(self) -> float:
        return self.kind.contact_dps

    @property
    def color(self) -> tuple[int, int, int]:
        return self.kind.kind.color

    @property
    def is_dead(self) -> bool:
        return self.hp <= 0

    def damage(self, amount: float) -> None:
        self.hp -= amount

    def update(self, dt: float, player_pos: pygame.Vector2, world: WorldMap) -> None:
        to_player = player_pos - self.pos
        gap = to_player.length()
        if gap == 0:
            return
        if self.kind.flees:
            # Only when you are close. A rabbit that flees from across the map
            # ends up pinned against the rim, where it can never be caught and
            # looks broken besides.
            if gap > config.BEAST_FLEE_RANGE:
                return
            way = -to_player / gap
        else:
            way = to_player / gap
        self.pos += way * self.speed * dt
        world.clamp(self.pos, self.radius)
