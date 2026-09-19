"""What a death leaves on the ground, and how long it waits.

Piles stack up: a second death does not erase the first. Each carries its own
clock instead, so the pressure is a deadline rather than a rule about not dying
twice -- several can be outstanding at once, and losing one is a matter of
running out of time rather than of bad luck.

The pile holds the pack as well as its contents, so recovering it restores the
slots and not just the goods. Everything outside the hotbar is in here: with no
base inventory there is nowhere else for it to have been.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config
from game.inventory.storage import Container
from game.items.item_kinds import ItemKind


@dataclass
class LootPile:
    pos: pygame.Vector2
    contents: Container
    pack: ItemKind | None = None
    ttl: float = config.LOOT_LIFETIME

    @property
    def is_gone(self) -> bool:
        return self.ttl <= 0

    def update(self, dt: float) -> None:
        self.ttl = max(0.0, self.ttl - dt)
