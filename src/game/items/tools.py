"""Usable tools. The weapon tool fires projectiles; upgrades are new WeaponTool values."""

from __future__ import annotations

from dataclasses import dataclass

from game import config


@dataclass(frozen=True)
class MiningTool:
    range: float = config.MINING_RANGE
    dps: float = config.MINING_DPS
    name: str = "Mining Beam"


@dataclass(frozen=True)
class WeaponTool:
    damage: float = config.WEAPON_DAMAGE
    fire_rate: float = config.WEAPON_FIRE_RATE  # shots per second
    projectile_speed: float = config.PROJECTILE_SPEED
    projectile_ttl: float = config.PROJECTILE_TTL
    projectile_radius: float = config.PROJECTILE_RADIUS
    name: str = "Pulse Gun"
