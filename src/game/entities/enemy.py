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
from typing import Protocol

import pygame

from game import config
from game.world.biomes import RING_BIOMES, Biome
from game.world.map import WorldMap

# What a thing is walking towards. The split is the whole classification: the
# core, or the player.
TARGET_CORE = "core"
TARGET_PLAYER = "player"


class Creature(Protocol):
    """What everything on the field has in common: a place, a size, a colour.

    Golems and animals share no behaviour -- one walks on the core and one
    hunts the player -- but drawing them is the same job, and a protocol says
    that without inventing a base class neither of them wants.
    """

    pos: pygame.Vector2

    @property
    def radius(self) -> float: ...

    @property
    def color(self) -> tuple[int, int, int]: ...


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
    biome: Biome | None = None  # None is the plain golem, which belongs nowhere

    @property
    def hit(self) -> float:
        """What one swing of this kind takes.

        Worked out from the old contact rate rather than written down twice:
        a kind that was twice as nasty to stand next to is twice as nasty to
        be hit by, and there is no second number to keep in step.
        """
        return self.contact_dps * config.GOLEM_HIT_SECONDS


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


def _biome_golem(biome: Biome, toughness: float) -> EnemyKind:
    """One biome's golem: the plain row with its numbers raised.

    NUMBERS ONLY, and deliberately. Give these their biome's trick and a raid
    becomes five bosses at once -- the trick is what the temple is for, and a
    raid is a crowd, not a boss fight repeated.
    """
    return EnemyKind(
        key=f"{biome.key}_golem",
        name=f"{biome.name} 골렘",
        target=TARGET_CORE,
        hp=PLAIN_GOLEM.hp * toughness,
        speed=PLAIN_GOLEM.speed,
        radius=PLAIN_GOLEM.radius * 1.2,
        contact_dps=PLAIN_GOLEM.contact_dps * toughness,
        color=biome.color,
        biome=biome,
    )


# In ring order, which is difficulty order, and they join the raids in the
# order their bosses fall -- so the crowd thickens the way the map does rather
# than all at once.
BIOME_GOLEMS: tuple[EnemyKind, ...] = tuple(
    _biome_golem(biome, toughness)
    for biome, toughness in zip(RING_BIOMES, config.BIOME_GOLEM_TOUGHNESS, strict=True)
)

GOLEM_KINDS: tuple[EnemyKind, ...] = (PLAIN_GOLEM, *BIOME_GOLEMS)


_BY_BIOME = {kind.biome: kind for kind in BIOME_GOLEMS if kind.biome is not None}


def golem_of(biome: Biome | None) -> EnemyKind:
    """The golem belonging to a biome, or the plain one for anywhere else."""
    return _BY_BIOME.get(biome, PLAIN_GOLEM) if biome is not None else PLAIN_GOLEM


def raid_kinds(bosses_killed: int) -> tuple[EnemyKind, ...]:
    """What a raid may be made of. The plain golem, plus one per boss killed."""
    return (PLAIN_GOLEM, *BIOME_GOLEMS[: min(bosses_killed, len(BIOME_GOLEMS))])


class swing:
    """The three beats of a golem's swing. A namespace, not a class to build.

    Walking, winding up, and the pause afterwards. Kept as names rather than
    a bool because what the player is shown differs for each: nothing while
    it walks, a closing red ring while it winds, and a flash when it lands.
    """

    WALK = "walk"
    WIND = "wind"
    REST = "rest"


@dataclass
class Golem:
    pos: pygame.Vector2
    kind: EnemyKind = PLAIN_GOLEM
    scale: float = 1.0
    hp: float = field(default=0.0)
    # Whether this one is standing in a temple's ring. A real field rather
    # than something stuck on at the call site: the scene has to ask every
    # step whether the ring is still up, and that question deserves an
    # answer the type checker can see.
    guarding: bool = False
    # Seconds of mud still clinging. Set by whatever it is standing in and
    # ticked down as it walks, so stepping out of sludge is a recovery rather
    # than a switch.
    mired: float = 0.0
    # The swing. ``beat`` is what is left of the current one; ``flash`` is how
    # long the landed blow stays drawn.
    phase: str = "walk"
    beat: float = 0.0
    flash: float = 0.0

    def __post_init__(self) -> None:
        if not self.hp:
            self.hp = self.kind.hp * self.scale

    @property
    def speed(self) -> float:
        # Scaled less than health: a golem twice as tough that also moves twice
        # as fast is not harder, it is unfightable.
        quick = self.kind.speed * (1 + (self.scale - 1) * config.GOLEM_SPEED_SCALING)
        return quick * config.MIRE_SLOW if self.mired > 0 else quick

    @property
    def radius(self) -> float:
        return self.kind.radius

    @property
    def contact_dps(self) -> float:
        return self.kind.contact_dps

    @property
    def hit(self) -> float:
        """What one swing takes, scaled like everything else by its size."""
        return self.kind.hit * self.scale

    @property
    def reach(self) -> float:
        """How close it comes before it stops and swings."""
        return self.radius + config.GOLEM_REACH

    @property
    def wound(self) -> float:
        """How far through the wind-up it is, 0 to 1. Drawing reads this.

        The red ring on screen closes as this fills, so the player reads WHEN
        as well as where -- which is the whole difference between a telegraph
        and a warning light.
        """
        if self.phase is not swing.WIND or config.GOLEM_WIND <= 0:
            return 0.0
        return 1.0 - self.beat / config.GOLEM_WIND

    @property
    def color(self) -> tuple[int, int, int]:
        return self.kind.color

    @property
    def is_dead(self) -> bool:
        return self.hp <= 0

    def damage(self, amount: float) -> None:
        self.hp -= amount

    def update(self, dt: float, target: pygame.Vector2, world: WorldMap) -> None:
        self.mired = max(0.0, self.mired - dt)
        to_target = target - self.pos
        if to_target.length_squared() > 0:
            self.pos += to_target.normalize() * self.speed * dt
        world.clamp(self.pos, self.radius)
