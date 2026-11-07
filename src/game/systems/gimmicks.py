"""The five tricks, written once for both sides of the fight.

The spec says a boss fight is the magic tutorial: the thing done to you becomes
the thing in your hand. So a boss's attack and the player's supreme glyph call
the same function here. Written twice it would be wrong twice -- and the one
that was wrong would be whichever got less play.

Each is chosen against the ground it is fought on, which was laid first:

    fire       lava already blocks a path standing still, so this one FOLLOWS
    ice        the sheets already take grip, so this one MAKES them
    wind       the chasms were dug for a shove
    poison     the mires already drain, so this one TRAVELS
    lightning  the wasteland has nothing to stand behind, so spread out

All five ask something different of the player: go round, keep your footing,
mind your back, keep moving, get apart. None of them is damage in a different
colour, and none of them kills outright.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pygame

from game import config
from game.entities.patch import BURNING, FROST, SLUDGE, Patch
from game.entities.player import Player
from game.systems import status
from game.world.biomes import BOG, BURNT_FOREST, SNOWFIELD, WASTELAND, WIND_PLATEAU, Biome
from game.world.map import WorldMap

# --- the pieces -----------------------------------------------------------


def scorch(at: pygame.Vector2, patches: list[Patch]) -> None:
    """Leave burning ground."""
    patches.append(Patch(pos=pygame.Vector2(at), kind=BURNING))


def freeze(at: pygame.Vector2, patches: list[Patch]) -> None:
    """Leave ice."""
    patches.append(Patch(pos=pygame.Vector2(at), kind=FROST))


def foul(at: pygame.Vector2, patches: list[Patch]) -> None:
    """Leave sludge."""
    patches.append(Patch(pos=pygame.Vector2(at), kind=SLUDGE))


class Body(Protocol):
    """Anything that stands somewhere and takes up room.

    The player on the boss's side of a trick, a golem on the player's. Written
    as a protocol rather than a union so that neither has to know about the
    other to be shoved.
    """

    pos: pygame.Vector2

    @property
    def radius(self) -> float: ...


def shove(body: Body, away_from: pygame.Vector2, world: WorldMap | None = None) -> None:
    """Throw it back. No damage of its own.

    What makes a shove frightening is where it puts you, which is why the
    plateau has holes in it. The shove itself has to stay harmless, or it
    becomes a hit that also moves you rather than a move.
    """
    offset = body.pos - away_from
    if offset.length_squared() == 0:
        # Standing inside whatever threw it. Any direction beats none.
        offset = pygame.Vector2(1, 0)
    body.pos += offset.normalize() * config.SHOVE_DISTANCE
    if world is not None:
        world.clamp(body.pos, body.radius)


def mark(at: pygame.Vector2, marks: list[pygame.Vector2]) -> None:
    """Pin a mark to the ground. One alone does nothing."""
    marks.append(pygame.Vector2(at))


# --- what the ground does to whoever is on it -----------------------------


def slippery(point: pygame.Vector2, patches: list[Patch]) -> bool:
    return any(p.kind == FROST and p.holds(point) for p in patches)


def sludgy(point: pygame.Vector2, patches: list[Patch]) -> bool:
    return any(p.kind == SLUDGE and p.holds(point) for p in patches)


def touch(dt: float, player: Player, patches: list[Patch], moving: bool) -> None:
    """Apply whatever the player is standing in.

    Each kind does exactly what the biome it came from does, so there is one
    rule for burning, one for mud, and none at all for ice -- that one takes
    footing, which the caller reads through ``slippery``. Taking health as
    well would make it the fire in a colder colour.
    """
    if player.hp <= 0:
        return
    for patch in patches:
        if not patch.holds(player.pos):
            continue
        if patch.kind == BURNING:
            status.ignite(player)
        elif patch.kind == SLUDGE:
            # Breath, and only from someone wading -- the bog's own rule.
            player.stamina_hold = config.STAMINA_DELAY
            if moving:
                player.drain(config.MIRE_DRAIN * dt)


def arc(dt: float, player: Player, marks: list[pygame.Vector2]) -> None:
    """Lightning between every pair of marks. One mark alone is harmless.

    The arc is what hurts, not the mark, so standing clear of the lines is the
    answer -- and the wasteland is where there is nothing to stand behind.
    """
    if player.hp <= 0 or len(marks) < 2:
        return
    struck = 0
    for i, a in enumerate(marks):
        for b in marks[i + 1 :]:
            if _near_segment(player.pos, a, b) <= config.ARC_WIDTH:
                struck += 1
    if struck:
        # Floored at one: a gimmick is something to survive and learn from.
        player.hp = max(1.0, player.hp - config.ARC_DPS * struck * dt)


def _near_segment(point: pygame.Vector2, a: pygame.Vector2, b: pygame.Vector2) -> float:
    """How far ``point`` lies from the segment between ``a`` and ``b``."""
    span = b - a
    length = span.length()
    if length == 0:
        return point.distance_to(a)
    along = max(0.0, min(1.0, (point - a).dot(span) / (length * length)))
    return point.distance_to(a + span * along)


def update_patches(dt: float, patches: list[Patch]) -> None:
    """Let the ground cool. A trail that never faded would wall the arena in."""
    for patch in patches:
        patch.ttl -= dt
    patches[:] = [p for p in patches if not p.spent]


def update_marks(dt: float, marks: list[pygame.Vector2], timers: list[float]) -> None:
    """Marks fade too, on timers kept alongside them."""
    for i in range(len(timers)):
        timers[i] -= dt
    keep = [i for i, left in enumerate(timers) if left > 0]
    marks[:] = [marks[i] for i in keep]
    timers[:] = [timers[i] for i in keep]


# --- the table ------------------------------------------------------------


@dataclass(frozen=True)
class Gimmick:
    key: str
    name: str
    biome: Biome
    effect: str  # what it asks of the player, in a word


GIMMICKS: tuple[Gimmick, ...] = (
    Gimmick("burn", "불길", BURNT_FOREST, "ground"),
    Gimmick("chill", "빙결", SNOWFIELD, "footing"),
    Gimmick("gust", "돌풍", WIND_PLATEAU, "position"),
    Gimmick("rot", "부패", BOG, "breath"),
    Gimmick("shock", "감전", WASTELAND, "spacing"),
)

_BY_KEY: dict[str, Gimmick] = {g.key: g for g in GIMMICKS}


def by_key(key: str) -> Gimmick | None:
    """The gimmick a glyph names, or None for one that names nothing."""
    return _BY_KEY.get(key)


def strike(
    gimmick: Gimmick,
    *,
    at: pygame.Vector2,
    victim: Body,
    away_from: pygame.Vector2,
    patches: list[Patch],
    marks: list[pygame.Vector2],
    world: WorldMap | None = None,
) -> None:
    """Raise one gimmick at a point, against whoever is standing on it.

    THE one path. A boss calls it with the player as the victim and itself as
    ``away_from``; the player's supreme glyph calls it with the golem it hit
    and the player's own feet. Two implementations would be wrong twice, and
    the wrong one would be whichever side got less play.

    ``at`` and ``victim.pos`` are usually the same place and deliberately are
    not required to be: a trick that lands short still leaves its ground where
    it landed.
    """
    if gimmick.key == "burn":
        scorch(at, patches)
    elif gimmick.key == "chill":
        freeze(at, patches)
    elif gimmick.key == "rot":
        foul(at, patches)
    elif gimmick.key == "shock":
        mark(at, marks)
    elif gimmick.key == "gust":
        # The only one that leaves nothing behind. It moves what it hits, and
        # away from whoever threw it -- toward would be a pull, and the holes
        # on the plateau are on the far side.
        shove(victim, away_from, world)


_BY_BIOME: dict[Biome, Gimmick] = {g.biome: g for g in GIMMICKS}


def of(biome: Biome | None) -> Gimmick | None:
    """The gimmick belonging to ``biome``, or None where there is not one."""
    return _BY_BIOME.get(biome) if biome is not None else None
