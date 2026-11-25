"""The shape of one room: its walls, its doorways, and where things stand.

A room is a rectangle the size of a screen, and every room in a temple is
drawn in the SAME place -- centred on the temple's own spot on the map. Only
what is in it changes. That is what makes "one room, one screen" true without
the camera ever having to chase anything: walking through a door swaps the
contents, not the view.

Pure arithmetic over a centre point. No surfaces, no scene, so where a body
ends up when it comes through the north door is a question a test can ask.
"""

from __future__ import annotations

import math
import random

import pygame

from game import config
from game.world.dungeon import NORTH, SOUTH, WEST


def rect(at: pygame.Vector2) -> pygame.Rect:
    """The room itself, centred on a temple's place on the map."""
    return pygame.Rect(
        round(at.x - config.ROOM_WIDTH / 2),
        round(at.y - config.ROOM_HEIGHT / 2),
        round(config.ROOM_WIDTH),
        round(config.ROOM_HEIGHT),
    )


def inner(at: pygame.Vector2) -> pygame.Rect:
    """What a body may actually stand in: the room, less its walls."""
    return rect(at).inflate(-2 * config.ROOM_WALL, -2 * config.ROOM_WALL)


def doorway(at: pygame.Vector2, way: str) -> pygame.Rect:
    """The opening in one wall, as a band a body can be inside of."""
    room = rect(at)
    wide = round(config.DOOR_WIDTH)
    deep = round(config.ROOM_WALL * 2)
    if way is NORTH:
        return pygame.Rect(room.centerx - wide // 2, room.top, wide, deep)
    if way is SOUTH:
        return pygame.Rect(room.centerx - wide // 2, room.bottom - deep, wide, deep)
    if way is WEST:
        return pygame.Rect(room.left, room.centery - wide // 2, deep, wide)
    return pygame.Rect(room.right - deep, room.centery - wide // 2, deep, wide)


def in_doorway(pos: pygame.Vector2, at: pygame.Vector2, way: str) -> bool:
    return doorway(at, way).collidepoint(pos.x, pos.y)


def arrival(at: pygame.Vector2, way: str) -> pygame.Vector2:
    """Where a body stands after coming through ``way`` INTO this room.

    Just inside the door it arrived by, far enough from the wall that the
    next step does not read as walking straight back out again.
    """
    room = rect(at)
    step = config.ROOM_WALL + config.DOOR_STEP
    if way is NORTH:
        return pygame.Vector2(room.centerx, room.top + step)
    if way is SOUTH:
        return pygame.Vector2(room.centerx, room.bottom - step)
    if way is WEST:
        return pygame.Vector2(room.left + step, room.centery)
    return pygame.Vector2(room.right - step, room.centery)


def hold(pos: pygame.Vector2, at: pygame.Vector2, radius: float = 0.0) -> None:
    """Keep a body inside the room, in place.

    The same shape as the map's own clamp, and the reason a locked door reads
    as a wall rather than as nothing happening.
    """
    room = inner(at)
    pos.x = max(room.left + radius, min(room.right - radius, pos.x))
    pos.y = max(room.top + radius, min(room.bottom - radius, pos.y))


def arena_radius() -> float:
    """The circle a boss fight happens in, inscribed in the room.

    A round floor inside a square room. Every piece of the boss fight already
    measures against a centre and a radius -- a thrown ball breaking on the
    wall, a charge's reach, the leap that may not land outside -- and a
    rectangle would mean teaching all of it a second shape for no gain the
    player can see.
    """
    return min(config.ROOM_WIDTH, config.ROOM_HEIGHT) / 2 - config.ROOM_WALL


def scatter(at: pygame.Vector2, count: int, rng: random.Random) -> list[pygame.Vector2]:
    """Spots for ``count`` bodies, spread around the middle of the room.

    Evenly around a ring and then jostled, the same way the old guard ring
    was placed: a clump reads as one fight in a corner, and a perfect circle
    reads as furniture.
    """
    if count <= 0:
        return []
    spread = min(config.ROOM_WIDTH, config.ROOM_HEIGHT) * config.ROOM_GUARD_RING
    start = rng.uniform(0.0, math.tau)
    spots: list[pygame.Vector2] = []
    for n in range(count):
        angle = start + n * math.tau / count
        reach = spread * rng.uniform(0.45, 1.0)
        spot = at + pygame.Vector2(math.cos(angle) * reach, math.sin(angle) * reach)
        hold(spot, at, config.GOLEM_RADIUS)
        spots.append(spot)
    return spots
