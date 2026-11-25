"""Waking a boss, and the door that shuts when you do.

What used to be here laid a biome's terrain across the floor the moment the
boss was called -- lava in the burnt forest, sheets in the snowfield. The
temple is a building now and the boss's room is left bare: the fifteen
attribute tricks already put plenty on the floor, and a room that starts
full leaves the player nothing to read when the fight adds to it.

So this is down to one thing: the door shuts until someone dies. Fought with
a way out, phase two is just something to retreat from.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass
class Ground:
    """The state of the room a fight is happening in."""

    sealed: bool = False


def seal(ground: Ground) -> bool:
    """Shut the door. False if it was already shut."""
    if ground.sealed:
        return False
    ground.sealed = True
    return True


def release(ground: Ground) -> None:
    """Open it again. Called when either side dies."""
    ground.sealed = False


def hold(pos: pygame.Vector2, middle: pygame.Vector2, radius: float, ground: Ground) -> None:
    """Keep a body inside a sealed floor, in place.

    A circle, because every piece of the fight already measures against one:
    a thrown ball breaking on the wall, a charge's reach, a leap that may not
    land outside. Being held at the edge is how a shove into one reads.
    """
    if not ground.sealed:
        return
    offset = pos - middle
    if offset.length() <= radius:
        return
    if offset.length_squared() == 0:
        return
    pos.update(middle + offset.normalize() * radius)
