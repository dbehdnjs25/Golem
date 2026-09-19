"""What sits in one slot: a kind and a count.

Mutable on purpose -- a slot's contents change as things are poured in and out,
and the alternative is rebuilding a frozen object on every pickup.

A stack never holds more than its kind's ``stack_max``. Checked on construction
rather than trusted, because an over-full stack would quietly break every slot
count that reads it.
"""

from __future__ import annotations

from dataclasses import dataclass

from game.items.item_kinds import ItemKind


@dataclass
class Stack:
    kind: ItemKind
    count: int

    def __post_init__(self) -> None:
        if not 0 <= self.count <= self.kind.stack_max:
            raise ValueError(f"{self.kind.key} cannot stack to {self.count}")

    @property
    def room(self) -> int:
        return self.kind.stack_max - self.count

    @property
    def is_full(self) -> bool:
        return self.room == 0

    def merge(self, other: Stack) -> int:
        """Pour what fits from ``other`` into this one. Return how much moved."""
        if other.kind is not self.kind:
            return 0
        moved = min(self.room, other.count)
        self.count += moved
        other.count -= moved
        return moved

    def split(self, n: int) -> Stack:
        """Take up to ``n`` out into a new stack."""
        taken = max(0, min(n, self.count))
        self.count -= taken
        return Stack(self.kind, taken)
