"""What a boss does with its hands, element aside.

Five blows, shared out two per boss, and one small machine that decides when
one happens. Every blow has the same three beats:

    WIND   it commits to an aim and does nothing
    ACT    the blow happens
    REST   it stands there, and the player gets their turn

The WIND is the entire reason a boss is a fight rather than a wall. The aim is
fixed when the wind starts and never re-read, so a telegraph actually tells you
something -- tracked through the wind-up, every blow would land wherever you
ended up and reading it would be pointless.

The arm is the odd one out and lives in ``boss_fight``: it leaves the body, so
it has a life of its own after the ACT beat ends. Nothing else is chosen while
it is away, which is what dodging it buys.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from game import config
from game.entities.boss import Boss
from game.entities.patch import Patch
from game.entities.player import Player
from game.systems import boss_tricks
from game.systems.boss_fight import Arm

# The two blows that cross the ground rather than happening where it stands.
_TRAVELS = ("charge", "leap")
# And the one that keeps taking aim through its wind-up.
_TRACKS = ("charge",)

WIND = "wind"
ACT = "act"
REST = "rest"


def _hurt(player: Player, amount: float) -> bool:
    """Land ``amount`` on the player unless they are rolling through it."""
    if player.invulnerable or player.hp <= 0:
        return False
    player.hp -= amount
    return True


def _facing(point: pygame.Vector2, at: pygame.Vector2) -> pygame.Vector2:
    toward = point - at
    return toward.normalize() if toward.length_squared() > 0 else pygame.Vector2(1, 0)


@dataclass
class Brawl:
    """One boss's hands. Built beside a boss, not on it.

    A boss is a row of numbers and a position; this is the state machine that
    turns the clock into blows, and it has a clock, a phase and an aim that the
    boss itself has no business carrying around.
    """

    rng: random.Random = field(default_factory=random.Random)
    arm: Arm = field(default_factory=Arm)
    tricks: boss_tricks.Field = field(default_factory=boss_tricks.Field)
    move: str | None = None
    phase: str = REST
    timer: float = config.BOSS_MOVE_GAP
    aim: pygame.Vector2 = field(default_factory=pygame.Vector2)
    struck: bool = False  # whether this blow has connected
    landed: bool = False  # whether this blow has finished its ACT beat
    thrown: int = 0  # how many blows have been started, ever
    # Where a travelling blow is going and how much of it is left. A charge
    # and a leap cross the ground over their ACT beat; resolved in one frame
    # they were teleports, with nothing passing over the ground in between
    # and so nothing to step out of.
    going: pygame.Vector2 = field(default_factory=pygame.Vector2)
    takeoff: pygame.Vector2 = field(default_factory=pygame.Vector2)
    landing: pygame.Vector2 = field(default_factory=pygame.Vector2)
    left: float = 0.0

    @property
    def busy(self) -> bool:
        """Whether a blow is under way.

        The scene stops walking the boss while this is true. Winding up
        and drifting forward at the same time makes the telegraph a lie:
        the rectangle is drawn from where it stands, and it was not there
        by the time it ran.
        """
        return self.move is not None

    def update(
        self,
        dt: float,
        boss: Boss,
        player: Player,
        room: pygame.Vector2,
        radius: float,
        forced: str | None = None,
        patches: list[Patch] | None = None,
    ) -> None:
        """Advance the clock, and whatever is in flight.

        ``forced`` picks the next move instead of the dice. For tests and the
        tuning scripts; the game never passes it.
        """
        boss_tricks.update(dt, self.tricks, player, patches if patches is not None else [])
        self.arm.update(dt, boss.pos, player.pos)
        if self.arm.caught is not None:
            player.pos.update(self.arm.caught)
            _hurt(player, config.SLAM_DAMAGE * self._might(boss))
            self.arm.caught = None
        if self.phase == WIND and self.move in _TRACKS:
            # The only blow that keeps taking aim. Its telegraph is a PATH
            # rather than a place, and a path drawn where you no longer are
            # tells you nothing -- the boss just runs past. Locked the
            # instant it sets off, or it would be a homing missile.
            self.aim = pygame.Vector2(player.pos)
        if self.phase == ACT and self.move in _TRAVELS:
            self._travel(dt, boss, player, room, radius)
        self.timer -= dt
        if self.timer > 0:
            return
        if self.move is None:
            self._begin(boss, player, forced)
            return
        if self.phase == WIND:
            self._strike(boss, player, room, radius)
            return
        elif self.phase == ACT:
            self._land(boss, player)
            self.phase = REST
            self.timer = config.BOSS_REST
        else:
            self.move = None
            self.timer = config.BOSS_MOVE_GAP

    # --- choosing -----------------------------------------------------
    def _begin(self, boss: Boss, player: Player, forced: str | None) -> None:
        if self.arm.out:
            # Half of what it hits with is in flight. Picking a close blow now
            # would hand back the window that dodging the arm just bought.
            self.timer = config.BOSS_REST
            return
        choices = (*boss.commons_now, *boss.tricks_now)
        self.move = forced if forced is not None else self.rng.choice(choices)
        self.phase = WIND
        self.timer = config.BOSS_WIND
        self.aim = pygame.Vector2(player.pos)
        self.struck = False
        self.landed = False
        self.thrown += 1

    # --- the blow -----------------------------------------------------
    def _might(self, boss: Boss) -> float:
        """What the second phase does to a blow: the same one, harder."""
        return boss.contact_dps / boss.kind.contact_dps

    def _strike(self, boss: Boss, player: Player, room: pygame.Vector2, radius: float) -> None:
        might = self._might(boss)
        if self.move == "slam":
            self._slam(boss, player, might)
        elif self.move == "sweep":
            self._sweep(boss, player, might)
        elif self.move == "charge":
            self._charge(boss)
        elif self.move == "leap":
            self._leap(boss, room, radius)
        elif self.move == "grab":
            self.arm.throw(boss.pos, self.aim)
        else:
            # An element trick. Unbuilt ones cast nothing and the beat simply
            # passes, which is what keeps a half-finished design playable.
            boss_tricks.cast(self.move or "", self.tricks, boss.pos, self.aim, might, self.rng)
        self.takeoff = pygame.Vector2(boss.pos)
        self.struck = self.move not in _TRAVELS  # travellers strike en route
        self.phase = ACT
        if self.move == "leap":
            self.timer = config.LEAP_SECONDS
        elif self.move == "charge":
            self.timer = config.CHARGE_REACH / config.CHARGE_SPEED
        else:
            self.timer = 0.0

    def _slam(self, boss: Boss, player: Player, might: float) -> None:
        """A ring around its own feet. The one blow that asks you to be away."""
        if boss.pos.distance_to(player.pos) <= config.SLAM_RADIUS + player.radius:
            _hurt(player, config.SLAM_DAMAGE * might)

    def _sweep(self, boss: Boss, player: Player, might: float) -> None:
        """A wedge in front of where it committed. Behind it is safe, which is
        what makes walking through the answer."""
        offset = player.pos - boss.pos
        if offset.length() > config.SWEEP_RANGE + player.radius:
            return
        facing = _facing(self.aim, boss.pos)
        toward = offset.normalize() if offset.length_squared() > 0 else facing
        if math.degrees(math.acos(max(-1.0, min(1.0, facing.dot(toward))))) <= (
            config.SWEEP_ARC / 2
        ):
            _hurt(player, config.SWEEP_DAMAGE * might)

    def _charge(self, boss: Boss) -> None:
        """Set off. The running happens during the ACT beat."""
        self.going = _facing(self.aim, boss.pos)
        self.left = config.CHARGE_REACH

    def _leap(self, boss: Boss, room: pygame.Vector2, radius: float) -> None:
        """Take off toward where you were standing.

        The air time is the warning, so nothing happens until it comes down.
        Hurt on take-off, the jump itself would be the blow and there would be
        nothing to step out of.
        """
        landing = pygame.Vector2(self.aim)
        offset = landing - room
        held = radius - boss.radius
        if offset.length() > held:
            landing = room + offset.normalize() * held
        self.landing = landing
        self.left = config.LEAP_SECONDS

    # --- crossing the ground ----------------------------------------------
    def _travel(
        self, dt: float, boss: Boss, player: Player, room: pygame.Vector2, radius: float
    ) -> None:
        """Move a charge or a leap along, one frame at a time."""
        if self.move == "charge":
            step = min(self.left, config.CHARGE_SPEED * dt)
            was = pygame.Vector2(boss.pos)
            boss.pos += self.going * step
            self.left -= step
            offset = boss.pos - room
            held = radius - boss.radius
            if offset.length() > held:  # pulled up at the wall
                boss.pos.update(room + offset.normalize() * held)
                self.left = 0.0
            caught = _near_line(player.pos, was, boss.pos) <= boss.radius + player.radius
            if not self.struck and caught:
                _hurt(player, config.CHARGE_DAMAGE * self._might(boss))
                self.struck = True  # once per charge, not once per frame
            if self.left <= 0:
                self.timer = min(self.timer, 0.0)
            return
        self.left -= dt
        share = 1.0 - max(0.0, self.left) / config.LEAP_SECONDS
        boss.pos.update(self.takeoff.lerp(self.landing, min(1.0, share)))

    def _land(self, boss: Boss, player: Player) -> None:
        """The end of the ACT beat: what a leap does when it comes down."""
        self.landed = True
        if self.move != "leap":
            return
        boss.pos.update(self.landing)
        if boss.pos.distance_to(player.pos) <= config.LEAP_RADIUS + player.radius:
            _hurt(player, config.LEAP_DAMAGE * self._might(boss))


def _near_line(point: pygame.Vector2, a: pygame.Vector2, b: pygame.Vector2) -> float:
    """How far ``point`` is from the segment a--b."""
    run = b - a
    length = run.length_squared()
    if length == 0:
        return point.distance_to(a)
    along = max(0.0, min(1.0, (point - a).dot(run) / length))
    return point.distance_to(a + run * along)
