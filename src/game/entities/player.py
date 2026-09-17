"""Top-down player. Logic-only: movement (and the dodge dash) is a pure function
of dt and input, so it is unit-testable headlessly. Damage is applied by
systems/combat, which reads ``invulnerable`` and writes ``hp``."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config
from game.world.map import WorldMap


@dataclass
class Player:
    pos: pygame.Vector2
    radius: float = config.PLAYER_RADIUS
    speed: float = config.PLAYER_SPEED
    hp: float = config.PLAYER_MAX_HP
    max_hp: float = config.PLAYER_MAX_HP
    dodge_timer: float = 0.0  # dash movement remaining
    iframe_timer: float = 0.0  # invulnerability remaining
    dodge_cooldown_timer: float = 0.0  # time until dodge is available again

    @property
    def invulnerable(self) -> bool:
        return self.iframe_timer > 0

    def update(
        self,
        dt: float,
        move_dir: pygame.Vector2,
        world: WorldMap,
        dodge_pressed: bool = False,
    ) -> None:
        """Advance by ``dt`` along ``move_dir`` (unnormalized), clamped to the map circle.
        A dodge grants i-frames immediately (even when standing still) and a
        speed boost while the dash lasts."""
        if dodge_pressed and self.dodge_cooldown_timer <= 0:
            self.dodge_timer = config.DODGE_DURATION
            self.iframe_timer = config.DODGE_IFRAMES
            self.dodge_cooldown_timer = config.DODGE_COOLDOWN

        speed = self.speed * (config.DODGE_SPEED_MULT if self.dodge_timer > 0 else 1.0)
        if move_dir.length_squared() > 0:
            self.pos += move_dir.normalize() * speed * dt
        world.clamp(self.pos, self.radius)

        self.dodge_timer = max(0.0, self.dodge_timer - dt)
        self.iframe_timer = max(0.0, self.iframe_timer - dt)
        self.dodge_cooldown_timer = max(0.0, self.dodge_cooldown_timer - dt)
