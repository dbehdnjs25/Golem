"""Combat systems: firing, projectile/enemy resolution, contact damage, and the
death penalty. All pure functions operating on injected state, so they are
unit-testable headlessly. Rendering lives in the scene, never here."""

from __future__ import annotations

import pygame

from game import config
from game.entities.enemy import Golem
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.inventory.storage import Folder
from game.items.tools import WeaponTool


def fire_weapon(
    dt: float,
    *,
    weapon: object | None,
    held: bool,
    aim_world: pygame.Vector2,
    player_pos: pygame.Vector2,
    fire_timer: float,
) -> tuple[float, list[Projectile]]:
    fire_timer -= dt
    if not held or not isinstance(weapon, WeaponTool):
        return fire_timer, []
    if fire_timer > 0:
        return fire_timer, []
    aim = aim_world - player_pos
    if aim.length_squared() == 0:
        return fire_timer, []
    velocity = aim.normalize() * weapon.projectile_speed
    shot = Projectile(
        pos=pygame.Vector2(player_pos),
        vel=velocity,
        damage=weapon.damage,
        radius=weapon.projectile_radius,
        ttl=weapon.projectile_ttl,
    )
    return 1.0 / weapon.fire_rate, [shot]


def _in_bounds(pos: pygame.Vector2, bounds: tuple[int, int]) -> bool:
    width, height = bounds
    return 0 <= pos.x <= width and 0 <= pos.y <= height


def _first_hit(shot: Projectile, enemies: list[Golem]) -> Golem | None:
    for enemy in enemies:
        if not enemy.is_dead and shot.pos.distance_to(enemy.pos) <= shot.radius + enemy.radius:
            return enemy
    return None


def update_projectiles(
    dt: float,
    projectiles: list[Projectile],
    enemies: list[Golem],
    bounds: tuple[int, int],
) -> None:
    surviving: list[Projectile] = []
    any_killed = False
    for shot in projectiles:
        shot.update(dt)
        if shot.is_expired or not _in_bounds(shot.pos, bounds):
            continue
        hit = _first_hit(shot, enemies)
        if hit is not None:
            hit.damage(shot.damage)
            any_killed = any_killed or hit.is_dead
            continue  # projectile consumed
        surviving.append(shot)
    projectiles[:] = surviving
    if any_killed:  # skip rebuilding the list on the common no-kill frame
        enemies[:] = [e for e in enemies if not e.is_dead]


def update_enemies(
    dt: float,
    enemies: list[Golem],
    player: Player,
    bounds: tuple[int, int],
) -> None:
    for enemy in enemies:
        enemy.update(dt, player.pos, bounds)
        if player.invulnerable:
            continue
        if enemy.pos.distance_to(player.pos) <= enemy.radius + player.radius:
            player.hp -= config.GOLEM_CONTACT_DPS * dt


def apply_death_penalty(backpack: Folder) -> None:
    """Drop half of every row, keeping the rounded-up half. Documents are untouched.

    Per-row rather than per-total so no kind can be sheltered by dropping another.
    ``rows()`` returns a fresh list, so mutating during the loop is safe.
    """
    for kind, n in backpack.rows():
        backpack.remove(kind, n // 2)
