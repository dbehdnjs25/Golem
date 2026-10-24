"""Raising the five temples on the sites the map already chose.

``WorldMap.temple_sites`` has placed one per ring biome since step 2 -- in
``RING_BIOMES`` order, inset from both rims and both seams. This only puts a
building on each, and hands each one its own seed so a visit can redraw the
inside without touching the world's dice.
"""

from __future__ import annotations

import random

import pygame

from game.entities.temple import Temple
from game.world.biomes import RING_BIOMES
from game.world.map import WorldMap

_SALT_SPAN = 1_000_000


def place(world: WorldMap, sites: tuple[pygame.Vector2, ...], rng: random.Random) -> list[Temple]:
    """One temple per site, in ring order.

    The salt is drawn here, once, from the world's generator: after this a
    temple rolls its own rooms and the shared generator is left alone.
    """
    return [
        Temple(pos=pygame.Vector2(site), biome=biome, salt=rng.randrange(_SALT_SPAN))
        for site, biome in zip(sites, RING_BIOMES, strict=True)
    ]
