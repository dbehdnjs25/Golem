"""Where the player is facing, and what lies in front of them.

With no cursor, the body is the aim: the way they last walked is the way they
face, and whatever stands in a fan in front of them within reach is what a
swing or a dig lands on. Everything here is plain vector maths.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Protocol, TypeVar

import pygame

from game import config


class Placed(Protocol):
    pos: pygame.Vector2


T = TypeVar("T", bound=Placed)


def face(move_dir: pygame.Vector2, facing: pygame.Vector2) -> pygame.Vector2:
    """The new facing: the way they are pushing, or the old one when still.

    Standing still keeps the last direction, so stopping to dig does not
    reset the aim to some default.
    """
    if move_dir.length_squared() == 0:
        return pygame.Vector2(facing)
    return move_dir.normalize()


def in_fan(
    origin: pygame.Vector2,
    facing: pygame.Vector2,
    point: pygame.Vector2,
    reach: float,
    pad: float = 0.0,
    half_angle: float = config.AIM_HALF_ANGLE,
) -> bool:
    """Whether ``point`` (with ``pad`` of body around it) is in the fan.

    Anything overlapping the player counts whatever the angle -- a golem
    standing on your toes is in front of you from every side.
    """
    to = point - origin
    gap = to.length()
    if gap > reach + pad:
        return False
    if gap <= pad or facing.length_squared() == 0:
        return True
    cos = to.dot(facing) / (gap * facing.length())
    # Widen by the body's own angular size, so a big target whose edge is in
    # the fan is hit even when its centre is just outside it.
    slack = math.asin(min(1.0, pad / gap)) if pad else 0.0
    return math.acos(max(-1.0, min(1.0, cos))) <= math.radians(half_angle) + slack


def in_front(
    origin: pygame.Vector2,
    facing: pygame.Vector2,
    things: Iterable[T],
    reach: float,
    pad_of: float = 0.0,
) -> list[T]:
    """Every one of ``things`` in the fan, nearest first."""
    hit = [t for t in things if in_fan(origin, facing, t.pos, reach, _pad(t, pad_of))]
    return sorted(hit, key=lambda t: origin.distance_to(t.pos))


def _pad(thing: object, default: float) -> float:
    radius = getattr(thing, "radius", None)
    return float(radius) if isinstance(radius, int | float) else default


def ahead(origin: pygame.Vector2, facing: pygame.Vector2, distance: float) -> pygame.Vector2:
    """The point ``distance`` in front of the player."""
    if facing.length_squared() == 0:
        return pygame.Vector2(origin)
    return origin + facing.normalize() * distance
