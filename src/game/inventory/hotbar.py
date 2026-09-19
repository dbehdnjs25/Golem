"""The five-slot hotbar. It holds tools AND materials, and it is the only thing
death does not take -- so what sits in it is the player's decision, not the
game's. Pickups never fill it while a backpack exists.

A slot holds a tool, a ``Stack``, or nothing. ``active_tool`` and
``active_stack`` each answer for one of those and None for the other, so callers
never test the type themselves.
"""

from __future__ import annotations

from dataclasses import dataclass

from game import config
from game.inventory.stack import Stack
from game.items.item_kinds import ItemKind


@dataclass
class Hotbar:
    slots: list[object | None]
    selected: int = 0

    @classmethod
    def create(cls) -> Hotbar:
        return cls(slots=[None] * config.HOTBAR_SLOTS)

    def select(self, index: int) -> None:
        if 0 <= index < len(self.slots):
            self.selected = index

    @property
    def active_tool(self) -> object | None:
        held = self.slots[self.selected]
        return None if isinstance(held, Stack) else held

    @property
    def active_stack(self) -> Stack | None:
        held = self.slots[self.selected]
        return held if isinstance(held, Stack) else None

    def _stacks(self, kind: ItemKind) -> list[Stack]:
        return [s for s in self.slots if isinstance(s, Stack) and s.kind is kind]

    def count(self, kind: ItemKind) -> int:
        return sum(s.count for s in self._stacks(kind))

    def has_room_for(self, kind: ItemKind) -> bool:
        """Whether one more of ``kind`` would fit, without putting it anywhere."""
        if any(not s.is_full for s in self._stacks(kind)):
            return True
        return any(slot is None for slot in self.slots)

    def add(self, kind: ItemKind, n: int = 1) -> int:
        """Top up open stacks, then take empty slots. Tools are never displaced."""
        left = n
        for stack in self._stacks(kind):
            if left == 0:
                break
            left -= stack.merge(Stack(kind, min(left, kind.stack_max)))
        for index, slot in enumerate(self.slots):
            if left == 0:
                break
            if slot is None:
                take = min(left, kind.stack_max)
                self.slots[index] = Stack(kind, take)
                left -= take
        return n - left

    def remove(self, kind: ItemKind, n: int = 1) -> int:
        left = min(n, self.count(kind))
        removed = left
        for index in range(len(self.slots) - 1, -1, -1):
            if left == 0:
                break
            slot = self.slots[index]
            if not isinstance(slot, Stack) or slot.kind is not kind:
                continue
            left -= slot.split(left).count
            if slot.count == 0:
                self.slots[index] = None
        return removed - left

    def take(self, index: int) -> object | None:
        lifted = self.slots[index]
        self.slots[index] = None
        return lifted

    def put(self, index: int, held: object) -> object | None:
        """Drop something into a slot. Return what was displaced or left over."""
        slot = self.slots[index]
        if isinstance(slot, Stack) and isinstance(held, Stack) and slot.kind is held.kind:
            slot.merge(held)
            return held if held.count else None
        self.slots[index] = held
        return slot
