"""Small movement helpers shared by entities. Pure maths on vectors -- no pygame
display, no entity imports -- so any entity can use it without an import cycle."""

from __future__ import annotations

import pygame


def clamp_to_circle(
    pos: pygame.Vector2,
    radius: float,
    center: pygame.Vector2,
    limit: float,
) -> None:
    """Clamp ``pos`` in place so a body of ``radius`` stays inside the circle.

    A body larger than the circle, or one sitting exactly on the centre, has no
    valid rim to sit on -- both land on the centre, which is the only point that
    is always inside.
    """
    reach = limit - radius
    offset = pos - center
    distance = offset.length()
    if distance <= reach:
        return
    if reach <= 0 or distance == 0:
        pos.update(center)
        return
    pos.update(center + offset * (reach / distance))
