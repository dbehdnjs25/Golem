"""Something the player put down on purpose: one slot's worth, on the ground.

Apart from ``LootPile``, which is a whole pack lost to a death and carries the
pack itself. This is a single slot -- a stack, or a tool exactly as it sat --
and walking back over it picks it up again.

Not until the player has stepped away once, though. Dropped at their feet, it
would otherwise be back in their hands on the very next frame.

It waits as long as a death's pile does, and like one, a core shard never
rots: the world makes exactly as many as the core asks for and no more.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config
from game.inventory.stack import Stack
from game.items.item_kinds import CORE_SHARD


@dataclass
class Dropped:
    pos: pygame.Vector2
    item: object  # a Stack, or a tool object as it sat in its slot
    armed: bool = False  # the player has stepped away since it was dropped
    ttl: float = config.LOOT_LIFETIME

    @property
    def keeps(self) -> bool:
        return isinstance(self.item, Stack) and self.item.kind is CORE_SHARD

    @property
    def is_gone(self) -> bool:
        return self.ttl <= 0 and not self.keeps

    def update(self, dt: float, player_pos: pygame.Vector2) -> None:
        if not self.armed and player_pos.distance_to(self.pos) > config.DROP_PICKUP_RADIUS:
            self.armed = True
        if not self.keeps:
            self.ttl = max(0.0, self.ttl - dt)

    def can_take(self, player_pos: pygame.Vector2) -> bool:
        """Armed, and the player is standing on it."""
        return self.armed and player_pos.distance_to(self.pos) <= config.DROP_PICKUP_RADIUS
