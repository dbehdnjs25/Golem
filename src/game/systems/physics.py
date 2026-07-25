"""Small movement helpers shared by entities. Pure maths on vectors — no pygame
display, no entity imports — so any entity can use it without an import cycle."""

from __future__ import annotations

import pygame


def clamp_to_bounds(pos: pygame.Vector2, radius: float, bounds: tuple[int, int]) -> None:
    """Clamp ``pos`` in place so a circle of ``radius`` stays inside ``bounds``."""
    width, height = bounds
    pos.x = max(radius, min(width - radius, pos.x))
    pos.y = max(radius, min(height - radius, pos.y))
