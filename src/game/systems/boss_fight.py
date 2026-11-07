"""The thrown arm.

Four of the five commons land where the boss is standing. This one leaves the
body: it flies at where the player was, and if it closes on them it drags them
back in. It is the only blow that can be stepped out of entirely, and that is
the point -- while the arm is away the boss cannot use its close blows, so
dodging it is what buys the window.

Three rules keep the trade honest:

- it only catches what it TOUCHES, so standing still is the mistake, not being
  in the room
- the window exists only while it is out, so a catch costs the player the
  opening they were owed
- it comes home whether or not it hit. Left out forever, one dodge would
  disarm the boss for the rest of the fight
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from game import config

HOME = "home"
OUT = "out"
BACK = "back"


@dataclass
class Arm:
    """One boss's arm. Lives beside the boss, not on it: the boss is a row of
    numbers and a position, and this is a small machine with its own state."""

    state: str = HOME
    pos: pygame.Vector2 = field(default_factory=pygame.Vector2)
    aim: pygame.Vector2 = field(default_factory=pygame.Vector2)
    caught: pygame.Vector2 | None = None  # where a caught player is dragged to

    @property
    def out(self) -> bool:
        return self.state != HOME

    @property
    def melee_locked(self) -> bool:
        """Whether the close blows are unavailable. True while the arm is away."""
        return self.out

    def throw(self, shoulder: pygame.Vector2, at: pygame.Vector2) -> None:
        """Send it at ``at``. Refused while one is already in flight."""
        if self.out:
            return
        self.state = OUT
        self.pos = pygame.Vector2(shoulder)
        toward = at - shoulder
        self.aim = toward.normalize() if toward.length_squared() > 0 else pygame.Vector2(1, 0)
        self.caught = None

    def update(self, dt: float, shoulder: pygame.Vector2, player: pygame.Vector2 | None) -> None:
        """Fly out, or come home. ``player`` None means nobody to catch."""
        if self.state == HOME:
            return
        if self.state == OUT:
            self.pos += self.aim * config.ARM_SPEED * dt
            if player is not None and self.pos.distance_to(player) <= config.ARM_RADIUS:
                self._catch(shoulder, player)
                return
            if self.pos.distance_to(shoulder) >= config.ARM_REACH:
                self.state = BACK
            return
        # Coming home, faster than it went: the window is meant to be short.
        home = shoulder - self.pos
        step = config.ARM_RETURN_SPEED * dt
        if home.length() <= step:
            self.pos.update(shoulder)
            self.state = HOME
            return
        self.pos += home.normalize() * step

    def _catch(self, shoulder: pygame.Vector2, player: pygame.Vector2) -> None:
        """Drag the player in, and start back. Dragged TO a distance rather
        than onto the boss, so the catch opens with a blow rather than with
        the player standing inside it."""
        toward = player - shoulder
        if toward.length_squared() == 0:
            toward = pygame.Vector2(1, 0)
        self.caught = shoulder + toward.normalize() * config.ARM_DRAG_TO
        self.state = BACK
