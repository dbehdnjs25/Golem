"""A mineable core shard. Logic-only, so it is unit-testable headlessly."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config
from game.items.item_kinds import CORE_SHARD, ItemKind


@dataclass
class Fragment:
    pos: pygame.Vector2
    hp: float = config.FRAGMENT_HP
    kind: ItemKind = CORE_SHARD  # what it is; what it YIELDS can differ
    # Terrain rather than part of the drifting node population. The obsidian
    # stone around a lava pool is placed by the world and never comes back once
    # it is gone, so the spawner must not count it against its own cap.
    fixed: bool = False

    @property
    def is_depleted(self) -> bool:
        return self.hp <= 0

    def damage(self, amount: float) -> bool:
        """Reduce hp by ``amount``. Return True only on the call that depletes it."""
        if self.is_depleted:
            return False
        self.hp -= amount
        return self.is_depleted
