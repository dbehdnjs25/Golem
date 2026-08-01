"""A mineable data fragment. Logic-only. The ``on_depleted`` hook exists so a
future disguised "Trojan" fragment can trigger an explosion when mined."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pygame

from game import config
from game.items.item_kinds import FRAGMENT, ItemKind


@dataclass
class Fragment:
    pos: pygame.Vector2
    hp: float = config.FRAGMENT_HP
    kind: ItemKind = FRAGMENT  # what mining it out yields
    on_depleted: Callable[[Fragment], None] | None = None

    @property
    def is_depleted(self) -> bool:
        return self.hp <= 0

    def damage(self, amount: float) -> bool:
        """Reduce hp by ``amount``. Return True only on the call that depletes it."""
        if self.is_depleted:
            return False
        self.hp -= amount
        if self.is_depleted:
            if self.on_depleted is not None:
                self.on_depleted(self)
            return True
        return False
