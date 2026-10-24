"""Calling a boss, and what the floor becomes when you do.

A temple is an empty building until its altar is used. Looking around, opening
the chest and eating something are all safe -- with a boss that wakes on entry,
all of that has to happen outside, and the only thing that achieves is making
the door frightening.

Summoning lays that biome's own terrain across the floor: lava in the burnt
forest, sheets in the snowfield, holes in the plateau, mires in the bog. The
boss's tricks and the ground it fights on become the same thing. The wasteland
lays nothing, because its terrain IS the absence of any -- an empty floor is
the truest reading of nowhere to hide.

The door shuts until someone dies. Fought with a way out, phase two is just
something to retreat from.

The arena keeps its OWN lists. Pushed into the world's, a dozen summons would
quietly grow the map a dozen lava pools that never cool.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from game import config
from game.entities.chasm import Chasm
from game.entities.ice_sheet import IceSheet
from game.entities.lava import LavaPool
from game.entities.mire import Mire
from game.entities.temple import Temple
from game.world.biomes import BOG, BURNT_FOREST, SNOWFIELD, WIND_PLATEAU

_Laid = LavaPool | IceSheet | Chasm | Mire


@dataclass
class Ground:
    """An arena's own floor. Empty until something is called onto it."""

    sealed: bool = False
    lava: list[LavaPool] = field(default_factory=list)
    ice: list[IceSheet] = field(default_factory=list)
    chasms: list[Chasm] = field(default_factory=list)
    mires: list[Mire] = field(default_factory=list)

    def what_was_laid(self) -> list[_Laid]:
        return [*self.lava, *self.ice, *self.chasms, *self.mires]

    def clear(self) -> None:
        self.lava.clear()
        self.ice.clear()
        self.chasms.clear()
        self.mires.clear()


def why_not(temple: Temple) -> str | None:
    """Why the altar will not answer, or None if it will."""
    if not temple.inside or temple.layout is None:
        return "제단 앞에 서야 한다"
    if not temple.guards_down:
        return "수호 골렘이 제단을 지키고 있다"
    if temple.boss_killed:
        return "이미 끝난 사원이다"
    return None


def summon(temple: Temple, ground: Ground, rng: random.Random) -> bool:
    """Call the boss. False if the altar will not answer, or one is already up.

    The caller is what actually puts a boss on the floor -- this lays the
    ground and shuts the door, which is the part the temple owns.
    """
    if ground.sealed or why_not(temple) is not None:
        return False
    ground.sealed = True
    _lay(temple, ground, rng)
    return True


def release(ground: Ground) -> None:
    """Open the door and clear the floor. Called when either side dies."""
    ground.sealed = False
    ground.clear()


def hold(pos: pygame.Vector2, temple: Temple, ground: Ground) -> None:
    """Keep ``pos`` inside a sealed room, in place.

    The same shape as the map's own clamp: the room is a circle, and being
    held at its wall is how a shove into one reads.
    """
    if not ground.sealed:
        return
    offset = pos - temple.pos
    reach = temple.radius - config.ARENA_WALL
    if offset.length() <= reach:
        return
    if offset.length_squared() == 0:
        offset = pygame.Vector2(1, 0)
    pos.update(temple.pos + offset.normalize() * reach)


# --- laying the floor -----------------------------------------------------

_COUNT = {
    BURNT_FOREST: config.ARENA_LAVA,
    SNOWFIELD: config.ARENA_ICE,
    WIND_PLATEAU: config.ARENA_CHASMS,
    BOG: config.ARENA_MIRES,
}


def _lay(temple: Temple, ground: Ground, rng: random.Random) -> None:
    """Scatter that biome's terrain, clear of the altar and inside the wall.

    The wasteland is not in the table at all, so it simply gets nothing.
    """
    wanted = _COUNT.get(temple.biome, 0)
    assert temple.layout is not None  # why_not has already checked
    altar = temple.layout.altar
    placed: list[_Laid] = []
    for _ in range(config.ARENA_ATTEMPTS):
        if len(placed) >= wanted:
            break
        radius = rng.uniform(config.ARENA_PATCH_MIN, config.ARENA_PATCH_MAX)
        angle = rng.uniform(0.0, math.tau)
        reach = rng.uniform(0.0, temple.radius - config.ARENA_WALL - radius)
        spot = temple.pos + pygame.Vector2(math.cos(angle) * reach, math.sin(angle) * reach)
        # Never over the altar: walking back to a plinth under a lava pool
        # would be a cruel joke.
        if spot.distance_to(altar) <= radius + config.ARENA_ALTAR_CLEAR:
            continue
        if any(spot.distance_to(p.pos) <= radius + p.radius for p in placed):
            continue
        placed.append(_make(temple, spot, radius))
    for thing in placed:
        _stow(ground, thing)


def _make(temple: Temple, spot: pygame.Vector2, radius: float) -> _Laid:
    if temple.biome is BURNT_FOREST:
        return LavaPool(pos=spot, radius=radius)
    if temple.biome is SNOWFIELD:
        return IceSheet(pos=spot, radius=radius)
    if temple.biome is WIND_PLATEAU:
        return Chasm(pos=spot, radius=radius)
    return Mire(pos=spot, radius=radius)


def _stow(ground: Ground, thing: _Laid) -> None:
    if isinstance(thing, LavaPool):
        ground.lava.append(thing)
    elif isinstance(thing, IceSheet):
        ground.ice.append(thing)
    elif isinstance(thing, Chasm):
        ground.chasms.append(thing)
    else:
        ground.mires.append(thing)
