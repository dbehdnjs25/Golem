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

    @property
    def is_dead(self) -> bool:
        """The same thing under the name a shot looks for.

        See ``systems/combat.Hurtable``: being shootable is what makes
        breaking one a real option rather than a line in the design.
        """
        return self.is_broken

    def damage(self, amount: float) -> None:
        self.hp -= amount


@dataclass
class Zone:
    """A circle that stays, and does something to whoever is in it.

    The three earlier shapes all resolve once: a circle lands, a front passes,
    a ring crosses. This one is a PLACE rather than an event, and it is why the
    wind can grow and the lightning orb can sit there humming. Being in it
    costs per second, so a brush past is cheap and standing in it is not.

    It may fly before it settles, drag bodies toward its middle, or push them
    all one way. Nothing uses all three at once; what matters is that the
    pulling and the pushing live with the circle instead of each wind trick
    carrying its own copy.
    """

    pos: pygame.Vector2
    radius: float
    vel: pygame.Vector2 = field(default_factory=pygame.Vector2)
    settle: float = 0.0  # seconds of flight before it stops where it is
    dps: float = 0.0
    grow: float = 0.0  # px/s the edge opens out
    pull: float = 0.0  # px/s toward the middle; a whirl
    drift: pygame.Vector2 = field(default_factory=pygame.Vector2)  # px/s, one way
    ttl: float = 4.0
    shock: float = 0.0  # seconds of 감전 left on whoever stands in it


@dataclass
class Lob:
    """Something thrown at a PLACE, which lands there.

    A ball is thrown in a direction and keeps going; this is thrown at a spot
    and arrives. The difference is what the player reads: a ball is a line to
    step off, a lob is a circle to not be standing in, announced by the arc
    itself rather than by a ring on the floor.
    """

    start: pygame.Vector2
    to: pygame.Vector2
    flight: float = config.LOB_SECONDS
    gone: float = 0.0  # how much of the flight is behind it
    damage: float = 0.0
    radius: float = config.LOB_RADIUS
    leaves: str | None = None
    pos: pygame.Vector2 = field(default_factory=pygame.Vector2)

    def __post_init__(self) -> None:
        if not self.pos:
            self.pos = pygame.Vector2(self.start)

    @property
    def share(self) -> float:
        """How far along it is, 0 to 1."""
        return min(1.0, self.gone / self.flight) if self.flight > 0 else 1.0

    @property
    def landed(self) -> bool:
        return self.share >= 1.0

    @property
    def height(self) -> float:
        """How high off the ground it is drawn, peaking halfway.

        Drawing only -- nothing flies over anything. But a thrown thing that
        slides along the floor reads as a ball, and the whole point of a lob
        is that it is going to come down somewhere.
        """
        share = self.share
        return 4 * config.LOB_ARC * share * (1 - share)


@dataclass
class Rod:
    """A thing stuck in the ground that is not in the way, and fires.

    A pillar you walk round; a rod you walk past, and then it kills you from
    somewhere else. It keeps its own clock and is breakable, which is the whole
    of what the desert asks: the floor fills up with them, and a player who
    never clears any has built the supreme trick's weapon themselves.
    """

    pos: pygame.Vector2
    hp: float = config.ROD_HP
    radius: float = config.ROD_RADIUS
    left: float = config.ROD_SECONDS
    spark: float = config.ROD_SPARK  # seconds until it throws its next line
    might: float = 1.0  # carried from the cast that planted it
    # Whether this one throws lines or is only something to be joined to.
    # Each cast plants exactly one that fires, so a floor full of rods is a
    # floor the player let fill up.
    fires: bool = False

    @property
    def is_broken(self) -> bool:
        return self.hp <= 0

    @property
    def is_dead(self) -> bool:
        """The same thing under the name a shot looks for; see Pillar."""
        return self.is_broken

    def damage(self, amount: float) -> None:
        self.hp -= amount


@dataclass
class Beam:
    """A line between two points that fires after a beat, and hurts once.

    Announced like everything else: while the warning runs it is a thread, and
    stepping off the thread is the whole answer. Fired, it is a line nobody
    should be standing on, and then it is gone.
    """

    a: pygame.Vector2
    b: pygame.Vector2
    damage: float = 0.0
    width: float = config.BEAM_WIDTH
    left: float = config.BEAM_WARNING
    ttl: float = config.BEAM_SECONDS
    spent: bool = False

    @property
    def live(self) -> bool:
        return self.left <= 0
