"""Usable tools.

A gathering tool is a family and a grade: the family decides what it can be
swung at, the grade decides whether the node yields and how fast. Both come
from ``items/grades``, so the ladder is described in one place and the tool
just carries a position on it.

``dps`` and ``name`` are derived rather than stored -- a copper pickaxe is not
a separate thing to configure, it is the base rate times copper's speed.

The weapon is still a single flat thing; grading weapons belongs with combat.
"""

from __future__ import annotations

from dataclasses import dataclass

from game import config
from game.items.grades import AXE, PICKAXE, WOOD_G, Grade

_FAMILY_NAMES = {PICKAXE: "곡괭이", AXE: "도끼"}


@dataclass(frozen=True)
class MiningTool:
    family: str = PICKAXE
    grade: Grade = WOOD_G
    range: float = config.MINING_RANGE

    @property
    def dps(self) -> float:
        return config.MINING_DPS * self.grade.speed

    @property
    def name(self) -> str:
        return f"{self.grade.name} {_FAMILY_NAMES[self.family]}"


def pickaxe(grade: Grade) -> MiningTool:
    return MiningTool(family=PICKAXE, grade=grade)


def axe(grade: Grade) -> MiningTool:
    return MiningTool(family=AXE, grade=grade)


@dataclass(frozen=True)
class WeaponTool:
    damage: float = config.WEAPON_DAMAGE
    fire_rate: float = config.WEAPON_FIRE_RATE  # shots per second
    projectile_speed: float = config.PROJECTILE_SPEED
    projectile_ttl: float = config.PROJECTILE_TTL
    projectile_radius: float = config.PROJECTILE_RADIUS
    name: str = "Pulse Gun"
