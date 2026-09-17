"""A mineable core shard. Logic-only, so it is unit-testable headlessly."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config
from game.items.item_kinds import FRAGMENT, ItemKind


@dataclass
class Fragment:
    pos: pygame.Vector2
    hp: float = config.FRAGMENT_HP
    kind: ItemKind = FRAGMENT  # what mining it out yields

    @property
    def is_depleted(self) -> bool:
        return self.hp <= 0

    def damage(self, amount: float) -> bool:
        """Reduce hp by ``amount``. Return True only on the call that depletes it."""
        if self.is_depleted:
            return False
        self.hp -= amount
        return self.is_depleted
