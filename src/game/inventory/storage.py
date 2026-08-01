"""Capacity-limited storage, measured in megabytes.

Two instances are used by the game: a small field backpack (fills while mining,
forces return trips) and the larger ``/Documents`` drive store at the core.

A folder is a list of rows, not a grid of slots — the game's material is a file
system, so ``12 fragments`` is one line, and the limit is megabytes rather than
a slot count. Kinds with different sizes therefore compete for the same space.

``reserved_mb`` is space promised to a transfer that is still in flight. It is
subtracted from ``free_mb``, so mining and other transfers cannot take the
landing space out from under a job that has already left its source folder.

Rows are keyed by the ``ItemKind`` itself (it is frozen, therefore hashable), not
by its ``key`` string: sizing the contents then needs no catalogue lookup and
cannot fail on an unlisted kind. Saving writes ``kind.key`` — that is the save
format's business, not this module's.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game.items.item_kinds import CATALOGUE, ItemKind


@dataclass
class Folder:
    cap_mb: int
    items: dict[ItemKind, int] = field(default_factory=dict)
    reserved_mb: int = 0

    @property
    def used_mb(self) -> int:
        return sum(kind.mb * n for kind, n in self.items.items())

    @property
    def free_mb(self) -> int:
        return self.cap_mb - self.used_mb - self.reserved_mb

    def count(self, kind: ItemKind) -> int:
        return self.items.get(kind, 0)

    def fits(self, kind: ItemKind, n: int) -> int:
        """How many of ``n`` would actually go in right now."""
        return max(0, min(n, self.free_mb // kind.mb))

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
                del self.items[kind]  # an empty row leaves the list
        return removed

    def rows(self) -> list[tuple[ItemKind, int]]:
        """``(kind, count)`` in catalogue order, empties omitted.

        A kind absent from ``CATALOGUE`` is invisible here. Every kind the game
        actually creates is in the catalogue; leaving one out is a bug in the
        table, not a case to handle.
        """
        return [(kind, self.items[kind]) for kind in CATALOGUE if self.items.get(kind)]

    def reserve(self, mb: int) -> None:
        self.reserved_mb += mb

    def release(self, mb: int) -> None:
        self.reserved_mb = max(0, self.reserved_mb - mb)
