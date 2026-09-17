"""A golem enemy. Logic-only: chases a target point each step, so it is
unit-testable headlessly. Contact damage is applied by systems/combat, not here."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config
from game.world.map import WorldMap


@dataclass
class Golem:
    pos: pygame.Vector2
    hp: float = config.GOLEM_HP
    speed: float = config.GOLEM_SPEED
    radius: float = config.GOLEM_RADIUS

    @property
    def is_dead(self) -> bool:
        return self.hp <= 0

    def damage(self, amount: float) -> None:
        self.hp -= amount

    def update(self, dt: float, target: pygame.Vector2, world: WorldMap) -> None:
        to_target = target - self.pos
        if to_target.length_squared() > 0:
            self.pos += to_target.normalize() * self.speed * dt
        world.clamp(self.pos, self.radius)
