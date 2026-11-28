"""What a death leaves on the ground, and how long it waits.

Piles stack up: a second death does not erase the first. Each carries its own
clock instead, so the pressure is a deadline rather than a rule about not dying
twice -- several can be outstanding at once, and losing one is a matter of
running out of time rather than of bad luck.

The pile holds the pack as well as its contents, so recovering it restores the
slots and not just the goods. Everything outside the hotbar is in here: with no
base inventory there is nowhere else for it to have been.

One exception to the clock: a pile holding a core shard or a boss's sigil
waits forever. There are exactly as many of each as the run needs and no way
to make another -- five shards scattered once, one sigil per boss -- so
either of them rotting on the ground would leave a run that can never be
finished, with nothing to tell the player why. A deadline is pressure; a
deadline that can quietly end the run is a bug with a timer on it.

It matters more than it did. Cargo cannot be parked on the hotbar any more,
so there is no longer a slot a careful player can keep them in.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config
from game.inventory.storage import Container
from game.items.item_kinds import CORE_SHARD, CORE_SIGIL, ItemKind


@dataclass
class LootPile:
    pos: pygame.Vector2
    contents: Container
    pack: ItemKind | None = None
    ttl: float = config.LOOT_LIFETIME

    @property
    def keeps(self) -> bool:
        """Whether this pile holds something the run cannot go on without."""
        return any(self.contents.count(kind) > 0 for kind in (CORE_SHARD, CORE_SIGIL))

    @property
    def is_gone(self) -> bool:
        return self.ttl <= 0 and not self.keeps

    def update(self, dt: float) -> None:
        if self.keeps:
            return
        self.ttl = max(0.0, self.ttl - dt)
