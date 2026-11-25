"""A boss temple: a door on the map, and a building behind it.

What stands in the world is a circle with a way in. What is BEHIND that way in
is ``world/dungeon`` -- thirteen rooms at least, joined into a tree, with the
boss at the far end of it. The temple's job here is small: hold the place, the
biome, the dice, and the building once it has been drawn.

The inside is drawn ONCE and then remembered. It used to be redrawn on every
visit, which was right when a temple was a single room and is wrong now: a
player who cleared nine rooms and stepped out for a potion would come back to
a building that had never heard of them.

The dice are the temple's own. Drawing from the world's shared generator would
shift every later roll, so one visit would change the weather and the ore for
the rest of the run.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config
from game.world.biomes import Biome
from game.world.dungeon import Dungeon, build


@dataclass
class Temple:
    pos: pygame.Vector2
    biome: Biome
    salt: int  # this temple's own seed, drawn once when the world is built
    radius: float = config.TEMPLE_RADIUS

    boss_killed: bool = False
    inside: bool = False  # whether the player is in the building right now
    rooms: Dungeon | None = None  # drawn on the first visit, then kept

    def contains(self, point: pygame.Vector2) -> bool:
        return self.pos.distance_to(point) < self.radius

    def interior(self) -> Dungeon:
        """The building, drawn the first time anybody asks for it."""
        if self.rooms is None:
            self.rooms = build(self.salt)
        return self.rooms

    @property
    def opened(self) -> bool:
        """Whether anybody has ever been inside."""
        return self.rooms is not None
