"""The three shapes a boss's trick comes in.

Fifteen tricks, but mostly the same few things aimed differently: something
that lands where it was announced, something that travels, and something that
opens out from a point. Writing those three once is why the snowfield's pillar
and the plateau's rings will not each need their own machinery.

Logic-only rows, like every other entity here. What moves them and what they do
to whoever is standing there is ``systems/boss_tricks``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from game import config


@dataclass
class Falling:
    """A circle on the floor that becomes a blow when the warning runs out.

    The warning is the trick: the player is told where, and given long enough
    to not be there. A hit is then a choice rather than a tax.
    """

    pos: pygame.Vector2
    damage: float = 0.0
    radius: float = config.FALL_RADIUS
    left: float = config.FALL_WARNING
    leaves: str | None = None  # a patch kind to put down where it lands
    stands: bool = False  # whether a column is left standing where it landed


@dataclass
class Wall:
    """A front that travels. Slower than a walk, or it is not a wall.

    What it asks is to be gone round, which only works if it can be outpaced;
    anything faster than the player is a hit with extra steps.
    """

    pos: pygame.Vector2
    vel: pygame.Vector2
    damage: float = 0.0
    width: float = config.WALL_WIDTH
    reach: float = config.WALL_REACH
    ttl: float = config.WALL_SECONDS
    spent: bool = False  # it hits once, not sixty times a second


@dataclass
class Ring:
    """An edge opening out from a point, catching whatever it crosses.

    Where it started is where it is NOT, which is what makes closing in the
    answer to one.
    """

    pos: pygame.Vector2
    speed: float = config.RING_SPEED
    reach: float = config.RING_REACH
    damage: float = 0.0
    radius: float = 0.0
    leaves: str | None = None
    dropped: list[pygame.Vector2] = field(default_factory=list)
    caught: bool = False  # it crosses a given body once


@dataclass
class Ball:
    """Something thrown that does its real work on arrival.

    Nothing to dodge while it crosses the room; the danger is where it ends.
    Which is what makes standing near a wall the mistake, and the reason the
    snowfield's basic is a thrown thing rather than another falling circle.
    """

    pos: pygame.Vector2
    vel: pygame.Vector2
    damage: float = 0.0
    radius: float = config.BALL_RADIUS
    ttl: float = config.BALL_SECONDS
    splits: int = 0  # how many shards it breaks into at the wall; 0 for a shard
    spent: bool = False  # it hits once, not sixty times a second


@dataclass
class Pillar:
    """A column standing in the way. The one thing in the game that is.

    It can be broken, and it melts on its own -- left standing for the rest of
    a fight, one bad cast would wall the room off permanently.
    """

    pos: pygame.Vector2
    hp: float = config.PILLAR_HP
    radius: float = config.PILLAR_RADIUS
    left: float = config.PILLAR_SECONDS

    @property
    def is_broken(self) -> bool:
        return self.hp <= 0

    def damage(self, amount: float) -> None:
        self.hp -= amount
