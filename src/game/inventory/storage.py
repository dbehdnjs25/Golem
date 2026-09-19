"""A grid of slots. One slot holds one ``Stack``; an empty slot holds ``None``.

The backpack is the only one of these the player carries -- there is no base
inventory. The limit is how many different things fit, never how heavy they
are; there is no weight system.

Slots are addressable because the player drags things between them. An earlier
version billed slots from a ``{kind: count}`` dict, which could say HOW MANY
slots were used but never WHICH, and a grid cannot be built on that.

Adding tops up open stacks before opening new ones, and removing drains from the
end, so a stack the player is looking at does not move under the cursor when
something is spent.
"""

from __future__ import annotations

from dataclasses import dataclass

from game.inventory.stack import Stack
from game.items.item_kinds import CATALOGUE, ItemKind


@dataclass
class Container:
    slots: list[Stack | None]

    @classmethod
    def empty(cls, size: int) -> Container:
        return cls(slots=[None] * size)

    @property
    def size(self) -> int:
        return len(self.slots)

    @property
    def used(self) -> int:
        return sum(1 for slot in self.slots if slot is not None)

    @property
    def free(self) -> int:
        return self.size - self.used

    def count(self, kind: ItemKind) -> int:
        return sum(s.count for s in self.slots if s is not None and s.kind is kind)

    def fits(self, kind: ItemKind, n: int) -> int:
        """How many of ``n`` would actually go in right now."""
        room = sum(s.room for s in self.slots if s is not None and s.kind is kind)
        return max(0, min(n, room + self.free * kind.stack_max))

    def add(self, kind: ItemKind, n: int = 1) -> int:
        """Add up to ``n``, topping up open stacks first. Return how many went in."""
        left = self.fits(kind, n)
        added = left
        for slot in self.slots:
            if left == 0:
                break
            if slot is not None and slot.kind is kind:
                left -= slot.merge(Stack(kind, min(left, kind.stack_max)))
        for index, slot in enumerate(self.slots):
            if left == 0:
                break
            if slot is None:
                take = min(left, kind.stack_max)
                self.slots[index] = Stack(kind, take)
                left -= take
        return added - left

    def remove(self, kind: ItemKind, n: int = 1) -> int:
        """Remove up to ``n``, draining the last slots first."""
        left = min(n, self.count(kind))
        removed = left
        for index in range(len(self.slots) - 1, -1, -1):
            if left == 0:
                break
            slot = self.slots[index]
            if slot is None or slot.kind is not kind:
                continue
            left -= slot.split(left).count
            if slot.count == 0:
                self.slots[index] = None
        return removed - left

    def take(self, index: int) -> Stack | None:
        """Lift a whole slot out, leaving it empty."""
        lifted = self.slots[index]
        self.slots[index] = None
        return lifted

    def put(self, index: int, stack: Stack) -> Stack | None:
        """Drop ``stack`` into a slot. Return what is left over or displaced.

        Onto the same kind it merges and hands back the remainder; onto a
        different kind it swaps, which is what a grid does.
        """
        slot = self.slots[index]
        if slot is None:
            self.slots[index] = stack
            return None
        if slot.kind is stack.kind:
            slot.merge(stack)
            return stack if stack.count else None
        self.slots[index] = stack
        return slot

    def rows(self) -> list[tuple[ItemKind, int]]:
        """``(kind, total)`` in catalogue order, for anything actually held."""
        return [(kind, self.count(kind)) for kind in CATALOGUE if self.count(kind)]
