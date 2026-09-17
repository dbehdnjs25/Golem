"""Slot-limited storage.

Three instances are used by the game: the carried inventory, the backpack that
extends it, and the store at the core.

A container is a grid of slots. One slot holds up to a kind's ``stack_max`` of
that kind, so 100 stone at a stack of 64 costs two slots. The limit is how many
different things you can carry home, not how heavy they are -- there is no
weight system.

``reserved_slots`` is space promised to a transfer that is still in flight. It
is subtracted from ``free_slots``, so mining and other transfers cannot take the
landing space out from under a job that has already left its source container.
Topping up an already-open stack is exempt: it consumes no new slot, so it
cannot eat a reservation.

Rows are keyed by the ``ItemKind`` itself (it is frozen, therefore hashable),
not by its ``key`` string: counting the contents then needs no catalogue lookup
and cannot fail on an unlisted kind. Saving writes ``kind.key`` -- that is the
save format's business, not this module's.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game.items.item_kinds import CATALOGUE, ItemKind


@dataclass
class Container:
    slots: int
    items: dict[ItemKind, int] = field(default_factory=dict)
    reserved_slots: int = 0

    @property
    def slots_used(self) -> int:
        return sum((n + kind.stack_max - 1) // kind.stack_max for kind, n in self.items.items())

    @property
    def free_slots(self) -> int:
        return self.slots - self.slots_used - self.reserved_slots

    def count(self, kind: ItemKind) -> int:
        return self.items.get(kind, 0)

    def fits(self, kind: ItemKind, n: int) -> int:
        """How many of ``n`` would actually go in right now.

        The open stack's room comes first and is exempt from the reservation,
        since filling it opens no new slot. Whatever is left needs fresh slots.
        """
        open_room = (-self.count(kind)) % kind.stack_max
        room = open_room + max(0, self.free_slots) * kind.stack_max
        return max(0, min(n, room))

    def add(self, kind: ItemKind, n: int = 1) -> int:
        """Add up to ``n``, bounded by free space. Return the number added."""
        added = self.fits(kind, n)
        if added:
            self.items[kind] = self.count(kind) + added
        return added

    def remove(self, kind: ItemKind, n: int = 1) -> int:
        """Remove up to ``n``, bounded by what is stored. Return the number removed."""
        removed = max(0, min(n, self.count(kind)))
        if removed:
            left = self.count(kind) - removed
            if left:
                self.items[kind] = left
            else:
                del self.items[kind]  # an empty row frees its slot
        return removed

    def rows(self) -> list[tuple[ItemKind, int]]:
        """``(kind, count)`` in catalogue order, empties omitted.

        A kind absent from ``CATALOGUE`` is invisible here. Every kind the game
        actually creates is in the catalogue; leaving one out is a bug in the
        table, not a case to handle.
        """
        return [(kind, self.items[kind]) for kind in CATALOGUE if self.items.get(kind)]

    def reserve(self, slots: int) -> None:
        self.reserved_slots += slots

    def release(self, slots: int) -> None:
        self.reserved_slots = max(0, self.reserved_slots - slots)
