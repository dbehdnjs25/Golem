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
    # Grown by the tree spawner. Counted against its own cap, not the node
    # spawner's, and let go once the player is far enough away.
    grove: bool = False

    # Full health when it was first struck. Trees and ore are not worth the
    # same number of swings, and a bar has to be a share of something.
    whole: float = config.FRAGMENT_HP

    @property
    def is_depleted(self) -> bool:
        return self.hp <= 0

    @property
    def worked(self) -> float:
        """How much of it has been taken, 0 to 1. Nothing shown at 0."""
        if self.whole <= 0:
            return 0.0
        return max(0.0, min(1.0, 1.0 - self.hp / self.whole))

    def damage(self, amount: float) -> bool:
        """Reduce hp by ``amount``. Return True only on the call that depletes it."""
        if self.is_depleted:
            return False
        self.whole = max(self.whole, self.hp)
        self.hp -= amount
        return self.is_depleted
