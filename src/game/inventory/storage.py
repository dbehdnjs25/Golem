"""Capacity-limited storage for the single data-fragment resource.

Two instances are used by the game: a small field ``Backpack`` (fills while
mining, forces return trips) and the larger ``/Documents`` drive store the
backpack is transferred into at the core. Both are plain ``Folder`` objects.
"""

from __future__ import annotations

from dataclasses import dataclass

from game import config


@dataclass
class Folder:
    cap_mb: int
    count: int = 0
    mb_per_item: int = config.FRAGMENT_MB

    @property
    def used_mb(self) -> int:
        return self.count * self.mb_per_item

    @property
    def free_mb(self) -> int:
        return self.cap_mb - self.used_mb

    @property
    def is_full(self) -> bool:
        return self.free_mb < self.mb_per_item

    def add(self, n: int = 1) -> int:
        """Add up to ``n`` items, bounded by capacity. Return the number added."""
        capacity_left = self.free_mb // self.mb_per_item
        added = max(0, min(n, capacity_left))
        self.count += added
        return added

    def remove(self, n: int = 1) -> int:
        """Remove up to ``n`` items, bounded by what is stored. Return the number removed."""
        removed = max(0, min(n, self.count))
        self.count -= removed
        return removed


def transfer(src: Folder, dst: Folder) -> int:
    """Move as many items as fit from ``src`` into ``dst``. Return count moved."""
    moved = dst.add(src.count)
    src.count -= moved
    return moved
