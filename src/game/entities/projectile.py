"""A weapon projectile. Logic-only: straight-line travel with a lifetime, so it
is unit-testable headlessly."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config


@dataclass
class Projectile:
    pos: pygame.Vector2
    vel: pygame.Vector2
    damage: float
    radius: float = config.PROJECTILE_RADIUS
    ttl: float = config.PROJECTILE_TTL
    # The gimmick a supreme glyph put on this shot, by key, or None. Carried on
    # the shot rather than looked up at the moment of impact: by then the
    # weapon may have been swapped, dropped, or carved over.
    gimmick: str | None = None

    @property
    def is_expired(self) -> bool:
        return self.ttl <= 0

    def update(self, dt: float) -> None:
        self.pos += self.vel * dt
        self.ttl -= dt
