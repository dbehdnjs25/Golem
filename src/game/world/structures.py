"""Where the ruins stand.

Placement is driven by the GLYPHS rather than by a count: every basic drawing
has to be findable or that biome is shut, and the surest way to guarantee that
is to walk the list of drawings and give each one a home. A count-first
placement would eventually roll a world with no frost glyph in it, and nothing
about reading the code would show that.

Reproducible from a seed, like the temples.
"""

from __future__ import annotations

import math
import random

import pygame

from game import config
from game.entities.structure import BIOME_RUIN, GRASS_RUIN, GRASS_VAULT, Structure
from game.items import glyphs
from game.items.glyphs import Glyph
from game.world.biomes import Biome
from game.world.map import WorldMap

_ATTEMPTS = 60


def place(world: WorldMap, rng: random.Random) -> list[Structure]:
    """One home for every basic glyph, plus spares out in the ring.

    The grassland pair goes down first because it is the tutorial: an open
    ruin and a watched vault, holding two cuts of one gimmick.
    """
    sites: list[Structure] = []
    weak, strong = sorted(glyphs.glyphs_of(None), key=lambda g: g.power)
    _add(sites, world, rng, GRASS_RUIN, weak, None)
    _add(sites, world, rng, GRASS_VAULT, strong, None)
    for glyph in glyphs.basic_glyphs():
        if glyph.biome is None:
            continue  # the grassland pair, placed above
        # Two chances each, so one awkward sector is not a shut biome.
        for _ in range(config.STRUCTURES_PER_BIOME):
            _add(sites, world, rng, BIOME_RUIN, glyph, glyph.biome)
    return sites


def _spot(world: WorldMap, rng: random.Random, biome: Biome | None) -> pygame.Vector2:
    """A candidate point: in the grassland for ``None``, out in the ring else.

    The angle is uniform rather than aimed at the wanted sector, because the
    sector a given angle lands in moves with the map's rotation -- the caller
    retries instead, which is cheaper than re-deriving the sector maths here.
    """
    if biome is None:
        reach = rng.uniform(config.STRUCTURE_MIN_FROM_CORE, world.grassland_radius * 0.95)
    else:
        reach = world.grassland_radius + world.ring_width * rng.uniform(0.15, 0.9)
    radians = math.radians(rng.uniform(0.0, 360.0))
    offset = pygame.Vector2(math.cos(radians) * reach, math.sin(radians) * reach)
    return pygame.Vector2(world.center + offset)


def _add(
    sites: list[Structure],
    world: WorldMap,
    rng: random.Random,
    kind: str,
    glyph: Glyph,
    biome: Biome | None,
) -> None:
    """Try for a legal spot; give up quietly rather than loop forever."""
    for _ in range(_ATTEMPTS):
        spot = _spot(world, rng, biome)
        if biome is not None and world.biome_at(spot) is not biome:
            continue
        if any(s.pos.distance_to(spot) <= config.STRUCTURE_SPACING for s in sites):
            continue
        sites.append(Structure(pos=spot, kind=kind, glyph=glyph))
        return
