"""The hand: strokes going down, and the pause that finishes them.

Pure state over an injected timestep, like the rest of ``systems/``. It knows
nothing about keys -- the scene turns an arrow into a direction -- and nothing
about casting. It says only what was drawn and, when the hand stops, what that
was.

A PAUSE ends a shape rather than an exact match. Resolving the instant a
sequence matched would make every long shape unreachable, because each rung
opens with the shape of the rung below: nobody who knew ㄱ could ever draw the
four-stroke cut that begins with it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game.items import strokes
from game.items.glyphs import Glyph


@dataclass
class Drawing:
    drawn: tuple[str, ...] = ()
    still: float = 0.0  # seconds since the last stroke

    _settle: float = field(default=strokes.SETTLE, repr=False)

    def stroke(self, way: str) -> None:
        """Add a direction. The same one twice running is one stroke.

        Holding the key, or tapping it again, draws a longer line rather than
        a second corner -- and a longer line is not something the player can
        see on the shape they are copying.
        """
        self.still = 0.0
        if self.drawn and self.drawn[-1] == way:
            return
        self.drawn = (*self.drawn, way)

    def clear(self) -> None:
        self.drawn = ()
        self.still = 0.0

    def update(self, dt: float) -> Glyph | None:
        """Count the stillness, and hand back what the shape was when it ends.

        None while the hand is still moving, and None for a shape nobody
        wrote -- in which case the slate is wiped all the same, so a mistake
        costs the drawing rather than leaving half of it to poison the next.
        """
        if not self.drawn:
            return None
        self.still += dt
        if self.still < self._settle:
            return None
        found = strokes.glyph_for(self.drawn)
        self.clear()
        return found
