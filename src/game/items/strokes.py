"""Glyphs as shapes, and the shapes as runs of arrow keys.

The shape IS the spell. Nothing is carved and nothing is chosen from a list:
the player draws ㄱ and fire comes out, because they know ㄱ means fire. What
grows over a run is how many shapes they have found and whether their hand
remembers them.

Two rules give the table its order, and both are for the player's memory rather
than the code's convenience:

- the FIRST stroke says which element it is. Learn one rung of the burnt
  forest and you already know how the other two begin
- the LENGTH says which rung: three, four, five. Five strokes for a supreme
  is the fight asking for something under pressure, not a number being
  larger. None of them simply alternates, because a shape that does is one
  the hand learns without the player ever looking at it

And each rung OPENS the next, so the ladder is drawn as well as described: ㄱ
is the first half of the greater cut, which is the first half of the supreme.
A player who knows the basic is already most of the way through the hand they
will need later.

Fire and lightning both open to the right, because there are four directions
and five elements. They part on the second stroke, and part the right way
round: fire turns down, lightning turns up.
"""

from __future__ import annotations

import pygame

from game.items.glyphs import GLYPHS, Glyph

UP = "up"
DOWN = "down"
LEFT = "left"
RIGHT = "right"

# Seconds of stillness that end a shape. Long enough to think between strokes,
# short enough that a spell follows the hand rather than trailing it.
SETTLE = 0.35

_BY_KEY = {
    pygame.K_UP: UP,
    pygame.K_DOWN: DOWN,
    pygame.K_LEFT: LEFT,
    pygame.K_RIGHT: RIGHT,
}


def of_key(key: int) -> str | None:
    """The direction an arrow key means, or None for any other key."""
    return _BY_KEY.get(key)


# One opening per element, then two strokes added a rung at a time. Written out
# rather than generated: these are things a player has to remember, and a table
# you can read is a table you can tune when one of them feels wrong.
SHAPES: dict[str, tuple[str, ...]] = {
    # 불 -- turns down first, the way fire falls
    "burnt_forest_basic": (RIGHT, DOWN, LEFT),
    "burnt_forest_greater": (RIGHT, DOWN, LEFT, UP),
    "burnt_forest_supreme": (RIGHT, DOWN, LEFT, UP, RIGHT),
    # 얼음
    "snowfield_basic": (DOWN, RIGHT, UP),
    "snowfield_greater": (DOWN, RIGHT, UP, LEFT),
    "snowfield_supreme": (DOWN, RIGHT, UP, LEFT, DOWN),
    # 바람
    "wind_plateau_basic": (UP, RIGHT, DOWN),
    "wind_plateau_greater": (UP, RIGHT, DOWN, RIGHT),
    "wind_plateau_supreme": (UP, RIGHT, DOWN, RIGHT, UP),
    # 독
    "bog_basic": (LEFT, DOWN, RIGHT),
    "bog_greater": (LEFT, DOWN, RIGHT, UP),
    "bog_supreme": (LEFT, DOWN, RIGHT, UP, LEFT),
    # 번개 -- turns up first, the way lightning goes
    "wasteland_basic": (RIGHT, UP, LEFT),
    "wasteland_greater": (RIGHT, UP, LEFT, DOWN),
    "wasteland_supreme": (RIGHT, UP, LEFT, DOWN, RIGHT),
}

_BY_SHAPE: dict[tuple[str, ...], Glyph] = {
    SHAPES[glyph.key]: glyph for glyph in GLYPHS if glyph.key in SHAPES
}


def glyph_for(drawn: tuple[str, ...]) -> Glyph | None:
    """The glyph a finished shape means, or None for a shape nobody wrote."""
    return _BY_SHAPE.get(drawn)
