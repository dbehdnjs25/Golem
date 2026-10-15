"""A ruin standing in the world with a drawing inside it.

Three sorts, which are the spec's first three sources of magic:

- a grassland ruin, open to anyone, holding the weak cut
- a grassland vault with a golem over it, holding the strong cut of the same
  gimmick -- the lesson that a guarded site is worth the fight, taught in the
  safe land before any biome asks the player to believe it
- a biome ruin, holding that biome's basic glyph

Opened once and then it is scenery. The drawing is learned permanently, so
there is nothing left to come back for.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config
from game.items.glyphs import Glyph

GRASS_RUIN = "grass_ruin"
GRASS_VAULT = "grass_vault"
BIOME_RUIN = "biome_ruin"

# Only the vault is watched. The others are a reward for walking, which is the
# whole point of putting them out in the ring.
GUARDED = frozenset({GRASS_VAULT})


@dataclass
class Structure:
    pos: pygame.Vector2
    kind: str
    glyph: Glyph
    opened: bool = False

    @property
    def guarded(self) -> bool:
        return self.kind in GUARDED

    @property
    def radius(self) -> float:
        return config.STRUCTURE_RADIUS * (1.4 if self.guarded else 1.0)

    def in_reach(self, point: pygame.Vector2) -> bool:
        return self.pos.distance_to(point) < config.STRUCTURE_REACH

    def open(self) -> Glyph | None:
        """Take what is inside. None if someone already has."""
        if self.opened:
            return None
        self.opened = True
        return self.glyph
