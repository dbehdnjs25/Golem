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
from game.entities.player import Player
from game.systems.boss_fight import Arm

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
    move: str | None = None
    phase: str = REST
    timer: float = config.BOSS_MOVE_GAP
    aim: pygame.Vector2 = field(default_factory=pygame.Vector2)
    struck: bool = False  # whether the current blow has landed its ACT
    thrown: int = 0  # how many blows have been started, ever

    def update(
        self,
        dt: float,
        boss: Boss,
        player: Player,
        room: pygame.Vector2,
        radius: float,
        forced: str | None = None,
    ) -> None:
        """Advance the clock, and whatever is in flight.

        ``forced`` picks the next blow instead of the dice. For tests and the
        tuning scripts; the game never passes it.
        """
        self.arm.update(dt, boss.pos, player.pos)
        if self.arm.caught is not None:
            player.pos.update(self.arm.caught)
            _hurt(player, config.SLAM_DAMAGE * self._might(boss))
            self.arm.caught = None
        self.timer -= dt
        if self.timer > 0:
            return
        if self.move is None:
            self._begin(boss, player, forced)
            return
        if self.phase == WIND:
            self._strike(boss, player, room, radius)
        elif self.phase == ACT:
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
        self.move = forced if forced is not None else self.rng.choice(boss.commons_now)
        self.phase = WIND
        self.timer = config.BOSS_WIND
        self.aim = pygame.Vector2(player.pos)
        self.struck = False
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
            self._charge(boss, player, room, radius, might)
        elif self.move == "leap":
            self._leap(boss, player, room, radius, might)
        elif self.move == "grab":
            self.arm.throw(boss.pos, self.aim)
        self.struck = True
        self.phase = ACT
        self.timer = config.LEAP_SECONDS if self.move == "leap" else 0.0

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

    def _charge(
        self,
        boss: Boss,
        player: Player,
        room: pygame.Vector2,
        radius: float,
        might: float,
    ) -> None:
        """Straight through where you were, and it hurts along the way.

        Resolved in one step rather than animated across frames: the line it
        runs is what matters, and a player who was on that line was on it when
        the wind ended.
        """
        facing = _facing(self.aim, boss.pos)
        start = pygame.Vector2(boss.pos)
        boss.pos += facing * config.CHARGE_REACH
        offset = boss.pos - room
        held = radius - boss.radius
        if offset.length() > held:  # pulled up at the wall
            boss.pos.update(room + offset.normalize() * held)
        if _near_line(player.pos, start, boss.pos) <= boss.radius + player.radius:
            _hurt(player, config.CHARGE_DAMAGE * might)

    def _leap(
        self,
        boss: Boss,
        player: Player,
        room: pygame.Vector2,
        radius: float,
        might: float,
    ) -> None:
        """Onto where you were standing. The ACT beat is the time in the air,
        so the landing is the thing to step out of rather than the jump."""
        landing = pygame.Vector2(self.aim)
        offset = landing - room
        held = radius - boss.radius
        if offset.length() > held:
            landing = room + offset.normalize() * held
        boss.pos.update(landing)
        if boss.pos.distance_to(player.pos) <= config.LEAP_RADIUS + player.radius:
            _hurt(player, config.LEAP_DAMAGE * might)


def _near_line(point: pygame.Vector2, a: pygame.Vector2, b: pygame.Vector2) -> float:
    """How far ``point`` is from the segment a--b."""
    run = b - a
    length = run.length_squared()
    if length == 0:
        return point.distance_to(a)
    along = max(0.0, min(1.0, (point - a).dot(run) / length))
    return point.distance_to(a + run * along)
