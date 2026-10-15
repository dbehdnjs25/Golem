"""Combat systems: firing, projectile/enemy resolution, contact damage, and the
death penalty. All pure functions operating on injected state, so they are
unit-testable headlessly. Rendering lives in the scene, never here."""

from __future__ import annotations

import random

import pygame

from game import config
from game.entities.beast import Beast
from game.entities.core import Core
from game.entities.enemy import TARGET_PLAYER, Creature, Golem
from game.entities.fragment import Fragment
from game.entities.loot import LootPile
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.inventory.storage import Container
from game.items.item_kinds import ItemKind
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
    raid: bool = False,
) -> None:
    """Move the golems, let them chew what they reach.

    On a raid night the ward stops turning them away -- that is what a raid IS.
    The healing keeps working through it: it is the golems that get through,
    not the hearth that goes out, and a raid fought with no way to recover is
    not survived so much as endured.
    """
    for enemy in enemies:
        enemy.update(dt, _what_it_is_after(enemy, player, core), world)
        if not raid:
            _hold_outside_ward(enemy, core)
        elif core.ignited and enemy.pos.distance_to(core.pos) <= enemy.radius + core.radius:
            core.damage(config.CORE_CONTACT_DPS * dt)
        if player.invulnerable or player.hp <= 0:
            continue  # i-frames, or already down -- a corpse takes no more
        if enemy.pos.distance_to(player.pos) <= enemy.radius + player.radius:
            player.hp -= enemy.contact_dps * dt  # from its kind, not a global


def _what_it_is_after(enemy: Golem, player: Player, core: Core) -> pygame.Vector2:
    """Where this one is walking, which its kind decides.

    A golem marches on the core and will walk straight past you to reach it;
    standing in the way is a choice, and that is what makes defending the core
    a job rather than a chase. Anything after the player hunts instead.

    Until this existed the ``target`` column was decoration -- the table said
    core and every golem walked at the player anyway.
    """
    if enemy.kind.target == TARGET_PLAYER:
        return player.pos
    return core.pos


_WARD_MARGIN = 0.5  # px clear of the rim; invisible, but keeps the check honest


def _hold_outside_ward(enemy: Creature, core: Core) -> None:
    """Push a creature back to the ward's rim. The ward is what the core buys.

    Animals are held out as well as golems. The spec has them gathering AROUND
    the ward, and a wolf that strolls in cancels the healing the whole ward
    exists to give -- the safe ground would stop being safe and step 3's reason
    to light the core with it.

    On raid nights this is lifted for golems -- that is the whole point of a
    raid -- but the exception belongs with the raid scheduler, not here.
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


def apply_death_penalty(
    pos: pygame.Vector2,
    backpack: Container | None,
    worn: ItemKind | None,
) -> LootPile | None:
    """Drop the pack and everything in it. Return the pile, or None if bare.

    The whole pack, not half of it. An earlier rule dropped half of each stack
    and kept the rest, which only made sense while a base inventory existed for
    the kept half to sit in. There is none now: what the player keeps is the
    hotbar, and what they lose is everything else until they walk back for it.

    The store at the core is untouched -- it was never carried.
    """
    if backpack is None:
        return None  # nothing to take: the hotbar is not the penalty's business
    return LootPile(pos=pygame.Vector2(pos), contents=backpack, pack=worn)


def update_beasts(
    dt: float,
    beasts: list[Beast],
    player: Player,
    world: WorldMap,
    core: Core,
    rng: random.Random,
    drops: list[Fragment],
) -> None:
    """Move the animals, bite what they catch, and leave what they were made of.

    The ward holds them out as it holds out golems: they gather AROUND it, and
    one that strolls in would cancel the healing the ward exists to give.

    What a dead one leaves is dropped on the ground as an ordinary node rather
    than pushed into the pack, so a kill with no room is not a kill wasted.
    """
    for beast in beasts:
        beast.update(dt, player.pos, world)
        _hold_outside_ward(beast, core)
        if player.invulnerable or player.hp <= 0 or not beast.contact_dps:
            continue
        if beast.pos.distance_to(player.pos) <= beast.radius + player.radius:
            player.hp -= beast.contact_dps * dt
    fallen = [b for b in beasts if b.is_dead]
    if not fallen:
        return
    for beast in fallen:
        for kind, count in beast.kind.drops:
            for _ in range(count):
                spot = beast.pos + pygame.Vector2(rng.uniform(-30, 30), rng.uniform(-30, 30))
                world.clamp(spot)
                drops.append(Fragment(pos=spot, kind=kind, hp=1.0))
    beasts[:] = [b for b in beasts if not b.is_dead]
