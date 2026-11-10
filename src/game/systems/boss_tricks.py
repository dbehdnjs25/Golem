"""The attribute tricks: casting them, and running what they put on the floor.

``cast`` turns a trick's name into hazards. ``update`` moves them and works out
who is standing in the way. The names come from ``entities/boss.TRICKS``, which
is where the design lives; ten of the fifteen are still only names, and
reaching for one of those is quiet rather than a crash -- a boss must not take
the game down by having a trick nobody has built yet.

The one rule that shapes all of it: every trick announces itself. The circle
before the blow, the wall slower than a walk, the ring you can be inside of.
None of them is damage for being in the room, which the contact damage already
is, and none of them kills outright.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from game import config
from game.entities.hazard import Falling, Ring, Wall
from game.entities.patch import BURNING, Patch
from game.entities.player import Player


@dataclass
class Casting:
    """A trick that lays itself down a beat at a time.

    Kept here rather than on the boss because what matters to each beat is
    where the player is NOW -- the whole point of a channel is that it
    follows -- and this is the thing that gets told that every frame.
    """

    beat: str  # which maker to call each time
    left: int
    every: float
    might: float = 1.0
    timer: float = 0.0


class Field:
    """Everything a boss has put on the floor. One per fight."""

    def __init__(self) -> None:
        self.falling: list[Falling] = []
        self.walls: list[Wall] = []
        self.rings: list[Ring] = []
        self.casting: list[Casting] = []

    def clear(self) -> None:
        self.falling.clear()
        self.walls.clear()
        self.rings.clear()
        self.casting.clear()

    @property
    def busy(self) -> bool:
        return bool(self.falling or self.walls or self.rings or self.casting)


def _hurt(player: Player, amount: float) -> None:
    if amount and not player.invulnerable and player.hp > 0:
        player.hp -= amount


def _leave(
    kind: str | None,
    at: pygame.Vector2,
    patches: list[Patch],
    radius: float = config.PATCH_RADIUS,
) -> None:
    """Put ground down, the size of whatever put it there.

    The size matters more than it sounds. Taking the global patch radius
    meant a trick could leave fire wider than the circle it announced, and
    then stepping correctly out of the warning still burned you.
    """
    if kind is not None:
        patches.append(Patch(pos=pygame.Vector2(at), kind=kind, radius=radius))


# --- running what is on the floor -----------------------------------------


def update(dt: float, field: Field, player: Player, patches: list[Patch]) -> None:
    """Advance every hazard and settle what it does."""
    _update_casting(dt, field, player)
    _update_falling(dt, field, player, patches)
    _update_walls(dt, field, player)
    _update_rings(dt, field, player, patches)


def _update_casting(dt: float, field: Field, player: Player) -> None:
    """Lay down the next beat of anything still casting."""
    for cast_in_progress in list(field.casting):
        cast_in_progress.timer -= dt
        if cast_in_progress.timer > 0:
            continue
        _BEATS[cast_in_progress.beat](field, player.pos, cast_in_progress.might)
        cast_in_progress.left -= 1
        cast_in_progress.timer = cast_in_progress.every
        if cast_in_progress.left <= 0:
            field.casting.remove(cast_in_progress)


def _update_falling(dt: float, field: Field, player: Player, patches: list[Patch]) -> None:
    landed: list[Falling] = []
    for spot in field.falling:
        spot.left -= dt
        if spot.left <= 0:
            landed.append(spot)
    for spot in landed:
        if spot.pos.distance_to(player.pos) <= spot.radius + player.radius:
            _hurt(player, spot.damage)
        _leave(spot.leaves, spot.pos, patches, spot.radius)
        field.falling.remove(spot)


def _update_walls(dt: float, field: Field, player: Player) -> None:
    for wall in list(field.walls):
        wall.pos += wall.vel * dt
        wall.ttl -= dt
        if not wall.spent and _within_wall(player.pos, wall, player.radius):
            _hurt(player, wall.damage)
            wall.spent = True  # once, not sixty times a second
        if wall.ttl <= 0:
            field.walls.remove(wall)


def _within_wall(point: pygame.Vector2, wall: Wall, pad: float) -> bool:
    """A front is a rectangle: wide across its travel, thin along it."""
    facing = wall.vel.normalize() if wall.vel.length_squared() else pygame.Vector2(1, 0)
    offset = point - wall.pos
    along = abs(offset.dot(facing))
    across = abs(offset.dot(pygame.Vector2(-facing.y, facing.x)))
    return along <= wall.reach + pad and across <= wall.width / 2 + pad


def _update_rings(dt: float, field: Field, player: Player, patches: list[Patch]) -> None:
    for ring in list(field.rings):
        before = ring.radius
        ring.radius += ring.speed * dt
        gap = ring.pos.distance_to(player.pos)
        if not ring.caught and before - player.radius <= gap <= ring.radius + player.radius:
            _hurt(player, ring.damage)
            ring.caught = True
        if ring.leaves is not None:
            _scatter_behind(ring, before, patches)
        if ring.radius >= ring.reach:
            field.rings.remove(ring)


def _scatter_behind(ring: Ring, before: float, patches: list[Patch]) -> None:
    """Drop what the ring leaves, spaced out along the way rather than every
    frame -- otherwise one ring would carpet the room."""
    step = ring.reach / max(1, config.ASHHEART_EMBERS)
    if math.floor(ring.radius / step) == math.floor(before / step):
        return
    angle = (len(ring.dropped) * 137.5) % 360  # spread apart, not in a line
    at = ring.pos + pygame.Vector2(1, 0).rotate(angle) * ring.radius
    ring.dropped.append(at)
    _leave(ring.leaves, at, patches, config.RING_EMBER_RADIUS)


# --- casting ---------------------------------------------------------------


def cast(
    key: str,
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float = 1.0,
    rng: random.Random | None = None,
) -> float:
    """Throw the trick ``key``, and say how long the boss is busy with it.

    Zero for the instant ones and for the ten nobody has built yet. The
    number has to come from the trick rather than be guessed where it is
    called: only the trick knows whether it is a throw or a channel.
    """
    maker = _CASTS.get(key)
    if maker is None:
        return 0.0
    return maker(
        field, pygame.Vector2(boss_pos), pygame.Vector2(target), might, rng or random.Random()
    )


def _ember_beat(field: Field, at: pygame.Vector2, might: float) -> None:
    """One circle, around wherever the player is standing right now.

    Sometimes directly on them, and that is deliberate: the warning is long
    enough to walk out of, so a circle underfoot is a reason to move rather
    than a hit. Kept always to one side, standing perfectly still would be the
    safest thing to do, which is the opposite of what this asks.
    """
    angle = _SPIN.uniform(0, 360)
    reach = _SPIN.uniform(0, config.EMBER_SPREAD)
    field.falling.append(
        Falling(
            pos=at + pygame.Vector2(1, 0).rotate(angle) * reach,
            damage=config.EMBER_DAMAGE * might,
            leaves=BURNING,
        )
    )


def _ember(
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float,
    rng: random.Random,
) -> float:
    """Shot into the sky, coming down one at a time around whoever moved.

    The boss holds still for the whole of it -- a channel it could walk out of
    would be a free hit rather than a commitment -- and each circle appears
    beside the player as its turn comes, so standing still collects all five.
    Walking away IS the answer to this one.
    """
    _ember_beat(field, target, might)  # the first lands with the cast
    field.casting.append(
        Casting(
            beat="ember",
            left=config.EMBER_DROPS - 1,
            every=config.EMBER_INTERVAL,
            might=might,
            timer=config.EMBER_INTERVAL,
        )
    )
    return config.EMBER_INTERVAL * (config.EMBER_DROPS - 1)


def _flame(
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float,
    rng: random.Random,
) -> float:
    """One front, walking at where you were. Slower than you are."""
    toward = target - boss_pos
    facing = toward.normalize() if toward.length_squared() else pygame.Vector2(1, 0)
    field.walls.append(
        Wall(
            pos=pygame.Vector2(boss_pos),
            vel=facing * config.FLAME_SPEED,
            damage=config.FLAME_DAMAGE * might,
        )
    )
    return 0.0  # thrown and forgotten; the wall lives on its own


def _ashheart(
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float,
    rng: random.Random,
) -> float:
    """The floor struck, and fire opening out of it in every direction."""
    field.rings.append(
        Ring(
            pos=pygame.Vector2(boss_pos),
            damage=config.ASHHEART_DAMAGE * might,
            leaves=BURNING,
        )
    )
    return 0.0  # one strike; the ring opens out by itself


# One generator for every beat of every channel. The casts take an injected
# one, but a beat happens frames later with nobody holding the dice.
_SPIN = random.Random()

_BEATS = {
    "ember": _ember_beat,
}

# Ten of the fifteen are still names in the design. They land here as they are
# built; until then ``cast`` returns False and the boss simply does nothing
# with that slot.
_CASTS = {
    "ember": _ember,
    "flame": _flame,
    "ashheart": _ashheart,
}
