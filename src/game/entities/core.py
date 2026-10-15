"""The central core the player assembles, ignites, and defends.

The ward is the core's state, not the map's: the map is terrain that was always
there, and the ward is the one thing the player grows. Upgrading it is the only
source of safety, of healing, and (later) of build space.

Level 0 is an unlit core with no ward at all -- there is nowhere to heal before
ignition, which is the pressure that gets the core built.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from game import config


@dataclass
class Core:
    pos: pygame.Vector2
    radius: float = config.CORE_RADIUS
    sync_radius: float = config.CORE_SYNC_RADIUS
    level: int = 0  # 0 = not yet ignited
    hp: float = 0.0
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
            self.hp = self.max_hp

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
        gained = self.max_hp
        self.level += 1
        # The new headroom is given, not merely unlocked. A level that raised a
        # ceiling the player then had to pay again to fill would be a worse
        # core than the one they had the moment before.
        self.hp += self.max_hp - gained
        return True

    # --- the ward ---------------------------------------------------------
    @property
    def ward_radius(self) -> float:
        """How far the ward reaches. Full at ``WARD_MAX_LEVEL`` and flat after.

        The ward finishes growing before the level cap does on purpose: the
        last stretch of the ladder has to buy something other than ground.
        """
        if not self.ignited:
            return 0.0
        steps = min(self.level, config.WARD_MAX_LEVEL) - 1
        return float(config.WARD_RADIUS_BASE * config.WARD_GROWTH**steps)

    def is_in_ward(self, point: pygame.Vector2) -> bool:
        return self.ignited and self.pos.distance_to(point) <= self.ward_radius

    # --- hit points -------------------------------------------------------
    @property
    def max_hp(self) -> float:
        """Zero until lit. A pedestal with a health bar promises a fight that
        cannot happen yet -- nothing marches on an unlit core.

        Grows per level, which is what the top of the ladder buys. The ward
        stops widening at ``WARD_MAX_LEVEL``, so without this the last fifteen
        levels would purchase nothing at all.
        """
        if not self.ignited:
            return 0.0
        return config.CORE_BASE_HP + (self.level - 1) * config.CORE_HP_PER_LEVEL

    @property
    def is_destroyed(self) -> bool:
        return self.ignited and self.hp <= 0

    def damage(self, amount: float) -> None:
        """Take a hit. Floors at zero -- a negative bar draws backwards."""
        self.hp = max(0.0, self.hp - amount)

    def repair(self, available: int) -> int:
        """Mend with up to ``available`` units. Return how many were spent.

        Whole units only, and never more than the damage needs, so topping up
        a nearly-whole core does not swallow a stack.
        """
        missing = self.max_hp - self.hp
        if missing <= 0:
            return 0
        spent = min(available, math.ceil(missing / config.CORE_REPAIR_PER_ITEM))
        self.hp = min(self.max_hp, self.hp + spent * config.CORE_REPAIR_PER_ITEM)
        return spent
