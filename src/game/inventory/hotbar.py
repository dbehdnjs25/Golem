"""The five-slot hotbar. The selected slot's item is the active tool driving the
left mouse button. Everything in it survives death; the inventory does not."""

from __future__ import annotations

from dataclasses import dataclass

from game import config


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
        return self.slots[self.selected]
