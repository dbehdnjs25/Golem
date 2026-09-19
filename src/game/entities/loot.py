"""What a death leaves on the ground.

One pile at a time. Dying again before recovering the last one erases it, which
puts immediate pressure on getting back without needing a timer to do it -- and
it forgives exactly one mistake.

The pile holds the pack as well as its contents, so recovering it restores the
slots and not just the goods. Everything outside the hotbar is in here: with no
base inventory there is nowhere else for it to have been.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game.inventory.storage import Container
from game.items.item_kinds import ItemKind


@dataclass
class LootPile:
    pos: pygame.Vector2
    contents: Container
    pack: ItemKind | None = None
