"""The open belongings screen, as pure state.

It holds whatever the cursor has picked up and nothing else -- where the slots
are drawn is the scene's business, and this never touches a surface. So the
whole of "click here, then click there" is testable headlessly.

Tools stay on the hotbar. Letting one into the pack would let a death take the
pickaxe, and not being able to lose your tools is what the hotbar is for.

Closing with something in hand puts it back rather than dropping it on the
floor. Losing goods to a keystroke is not a decision anyone made.
"""

from __future__ import annotations

from dataclasses import dataclass

from game.inventory.hotbar import Hotbar
from game.inventory.stack import Stack
from game.inventory.storage import Container

HOTBAR = "hotbar"
PACK = "pack"


@dataclass
class Grid:
    held: object | None = None

    def click(self, where: str, index: int, backpack: Container | None, hotbar: Hotbar) -> None:
        if where == HOTBAR:
            self._click_hotbar(index, hotbar)
        elif backpack is not None:
            self._click_pack(index, backpack)

    def _click_hotbar(self, index: int, hotbar: Hotbar) -> None:
        self.held = hotbar.take(index) if self.held is None else hotbar.put(index, self.held)

    def _click_pack(self, index: int, backpack: Container) -> None:
        held = self.held
        if held is None:
            self.held = backpack.take(index)
        elif isinstance(held, Stack):
            self.held = backpack.put(index, held)
        # a tool stays in hand: it cannot go into the pack

    def close(self, backpack: Container | None, hotbar: Hotbar) -> None:
        """Put whatever is in hand back somewhere it fits."""
        held = self.held
        if held is None:
            return
        if isinstance(held, Stack):
            if backpack is not None:
                held.count -= backpack.add(held.kind, held.count)
            if held.count:
                held.count -= hotbar.add(held.kind, held.count)
            self.held = held if held.count else None
            return
        for index, slot in enumerate(hotbar.slots):
            if slot is None:
                hotbar.slots[index] = held
                self.held = None
                return
