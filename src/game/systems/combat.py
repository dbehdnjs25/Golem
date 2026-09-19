"""Combat systems: firing, projectile/enemy resolution, contact damage, and the
death penalty. All pure functions operating on injected state, so they are
unit-testable headlessly. Rendering lives in the scene, never here."""

from __future__ import annotations

import pygame

from game import config
from game.entities.core import Core
from game.entities.enemy import Golem
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.inventory.storage import Container
from game.items.tools import WeaponTool
from game.world.map import WorldMap


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


def _first_hit(shot: Projectile, enemies: list[Golem]) -> Golem | None:
    for enemy in enemies:
        if not enemy.is_dead and shot.pos.distance_to(enemy.pos) <= shot.radius + enemy.radius:
            return enemy
    return None


def update_projectiles(
    dt: float,
    projectiles: list[Projectile],
    enemies: list[Golem],
    world: WorldMap,
) -> None:
    surviving: list[Projectile] = []
    any_killed = False
    for shot in projectiles:
        shot.update(dt)
        if shot.is_expired or not world.contains(shot.pos):
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
    world: WorldMap,
    core: Core,
) -> None:
    for enemy in enemies:
        enemy.update(dt, player.pos, world)
        _hold_outside_ward(enemy, core)
        if player.invulnerable:
            continue
        if enemy.pos.distance_to(player.pos) <= enemy.radius + player.radius:
            player.hp -= config.GOLEM_CONTACT_DPS * dt


_WARD_MARGIN = 0.5  # px clear of the rim; invisible, but keeps the check honest


def _hold_outside_ward(enemy: Golem, core: Core) -> None:
    """Push a golem back to the ward's rim. The ward is what the core buys.

    On raid nights this will be lifted -- that is the whole point of a raid --
    but the exception belongs with the raid scheduler, not here.
    """
    if not core.is_in_ward(enemy.pos):
        return
    offset = enemy.pos - core.pos
    distance = offset.length()
    if distance == 0:
        offset = pygame.Vector2(1, 0)
        distance = 1.0
    # Just outside, not exactly on, the rim: is_in_ward is inclusive, so landing
    # them on it would leave "no golem is inside the ward" reading as false.
    reach = core.ward_radius + _WARD_MARGIN
    enemy.pos.update(core.pos + offset * (reach / distance))


def apply_death_penalty(backpack: Container | None) -> None:
    """Drop the rounded-up half of every row. The store at the core is untouched.

    Per-row rather than per-total so no kind can be sheltered by dropping another.
    Rounding up on the dropped side means a count of 1 drops -- rare singles are
    not protected, which is what gives the hotbar its job. ``rows()`` returns a
    fresh list, so mutating during the loop is safe.
    """
    if backpack is None:
        return  # nothing to take: the hotbar is not the penalty's business
    for kind, n in backpack.rows():
        backpack.remove(kind, (n + 1) // 2)
