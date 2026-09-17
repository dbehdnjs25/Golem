"""The central core the player assembles, ignites, and defends.

The ward is the core's state, not the map's: the map is terrain that was always
there, and the ward is the one thing the player grows. Upgrading it is the only
source of safety, of healing, and (later) of build space.

Level 0 is an unlit core with no ward at all -- there is nowhere to heal before
ignition, which is the pressure that gets the core built.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config


@dataclass
class Core:
    pos: pygame.Vector2
    radius: float = config.CORE_RADIUS
    sync_radius: float = config.CORE_SYNC_RADIUS
    level: int = 0  # 0 = not yet ignited
    bosses_killed: int = 0

    def is_in_sync_range(self, point: pygame.Vector2) -> bool:
        return self.pos.distance_to(point) <= self.sync_radius

    # --- ignition and levels ---------------------------------------------
    @property
    def ignited(self) -> bool:
        return self.level >= 1

    def ignite(self) -> None:
        """Place the assembled core. Day one starts here. A no-op once lit."""
        if not self.ignited:
            self.level = 1

    @property
    def level_cap(self) -> int:
        """How high this core can go until another boss drop arrives."""
        index = min(self.bosses_killed, len(config.CORE_LEVEL_CAPS) - 1)
        return config.CORE_LEVEL_CAPS[index]

    @property
    def can_upgrade(self) -> bool:
        return self.ignited and self.level < self.level_cap

    def upgrade(self) -> bool:
        """Raise the level by one. Return False when the cap blocks it."""
        if not self.can_upgrade:
            return False
        self.level += 1
        return True

    # --- the ward ---------------------------------------------------------
    @property
    def ward_radius(self) -> float:
        if not self.ignited:
            return 0.0
        return float(config.WARD_RADIUS_BASE * config.WARD_GROWTH ** (self.level - 1))

    def is_in_ward(self, point: pygame.Vector2) -> bool:
        return self.ignited and self.pos.distance_to(point) <= self.ward_radius
