"""Golems, and the table of what kinds of golem there are.

A golem marches on the core. That is what makes it a golem -- anything that
hunts the player is an animal, and lives in ``entities/beast``.

The numbers live in a frozen row per kind, the same shape as ``ItemKind`` and
``Biome``. Five biome golems arrive in step 8, and they should be five rows
rather than five subclasses.

``scale`` is separate from the kind: distance from the core makes a golem
tougher without making it a different sort of golem, so it multiplies the row
rather than replacing it.

Logic-only: it chases a point each step, so it is unit-testable headlessly.
Contact damage is applied by systems/combat, not here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from game import config
from game.world.map import WorldMap

# What a thing is walking towards. The split is the whole classification: the
# core, or the player.
TARGET_CORE = "core"
TARGET_PLAYER = "player"


@dataclass(frozen=True)
class EnemyKind:
    key: str  # stable id, used for saves and comparison
    name: str  # shown to the player
    target: str
    hp: float
    speed: float  # px/s
    radius: float
    contact_dps: float  # hp/s while touching what it is after
    color: tuple[int, int, int]


PLAIN_GOLEM = EnemyKind(
    key="golem",
    name="골렘",
    target=TARGET_CORE,
    hp=config.GOLEM_HP,
    speed=config.GOLEM_SPEED,
    radius=config.GOLEM_RADIUS,
    contact_dps=config.GOLEM_CONTACT_DPS,
    color=config.GOLEM_COLOR,
)

# One for now. The five biome golems join this tuple in step 8, and the raid
# composition reads from it.
GOLEM_KINDS: tuple[EnemyKind, ...] = (PLAIN_GOLEM,)


@dataclass
class Golem:
    pos: pygame.Vector2
    kind: EnemyKind = PLAIN_GOLEM
    scale: float = 1.0
    hp: float = field(default=0.0)

    def __post_init__(self) -> None:
        if not self.hp:
            self.hp = self.kind.hp * self.scale

    @property
    def speed(self) -> float:
        # Scaled less than health: a golem twice as tough that also moves twice
        # as fast is not harder, it is unfightable.
        return self.kind.speed * (1 + (self.scale - 1) * config.GOLEM_SPEED_SCALING)

    @property
    def radius(self) -> float:
        return self.kind.radius

    @property
    def contact_dps(self) -> float:
        return self.kind.contact_dps

    @property
    def color(self) -> tuple[int, int, int]:
        return self.kind.color

    @property
    def is_dead(self) -> bool:
        return self.hp <= 0

    def damage(self, amount: float) -> None:
        self.hp -= amount

    def update(self, dt: float, target: pygame.Vector2, world: WorldMap) -> None:
        to_target = target - self.pos
        if to_target.length_squared() > 0:
            self.pos += to_target.normalize() * self.speed * dt
        world.clamp(self.pos, self.radius)
