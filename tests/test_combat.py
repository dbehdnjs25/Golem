import pygame
import pytest

from game import config
from game.entities.enemy import Golem
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.inventory.storage import Folder
from game.items.item_kinds import FRAGMENT, ItemKind
from game.items.tools import MiningTool, WeaponTool
from game.systems import combat

# A second kind, used only to prove apply_death_penalty halves per row rather
# than per total (see test_death_penalty_cannot_shelter_one_kind_by_dropping_another).
HEAVY = ItemKind(key="heavy", name="큰 파일", mb=10, color=(1, 2, 3))


def _fire(steps, dt, *, held=True, weapon=None):
    weapon = weapon or WeaponTool(fire_rate=2.0)  # interval 0.5s
    timer = 0.0
    shots = []
    for _ in range(steps):
        timer, new = combat.fire_weapon(
            dt,
            weapon=weapon,
            held=held,
            aim_world=pygame.Vector2(100, 0),
            player_pos=pygame.Vector2(0, 0),
            fire_timer=timer,
        )
        shots.extend(new)
    return shots


def test_fires_at_fire_rate_when_held():
    shots = _fire(steps=4, dt=0.5)  # dt == interval -> one shot per step
    assert len(shots) == 4
    assert all(isinstance(s, Projectile) for s in shots)


def test_projectile_aims_at_target():
    shots = _fire(steps=1, dt=0.5)
    assert shots[0].vel.x > 0 and shots[0].vel.y == 0


def test_no_fire_when_not_held():
    assert _fire(steps=4, dt=0.5, held=False) == []


def test_no_fire_with_non_weapon_tool():
    assert _fire(steps=4, dt=0.5, weapon=MiningTool()) == []


def test_no_fire_on_degenerate_aim():
    timer, shots = combat.fire_weapon(
        0.5,
        weapon=WeaponTool(fire_rate=2.0),
        held=True,
        aim_world=pygame.Vector2(0, 0),
        player_pos=pygame.Vector2(0, 0),
        fire_timer=0.0,
    )
    assert shots == []


def test_projectile_hits_and_kills_enemy():
    enemy = Golem(pos=pygame.Vector2(100, 100), hp=5)
    shot = Projectile(pos=pygame.Vector2(100, 100), vel=pygame.Vector2(0, 0), damage=5)
    projectiles = [shot]
    enemies = [enemy]
    combat.update_projectiles(0.016, projectiles, enemies, (2400, 1600))
    assert projectiles == []  # consumed on hit
    assert enemies == []  # died at 0 hp


def test_projectile_misses_and_survives():
    enemy = Golem(pos=pygame.Vector2(1000, 1000), hp=5)
    shot = Projectile(pos=pygame.Vector2(0, 0), vel=pygame.Vector2(10, 0), damage=5, ttl=1.0)
    projectiles = [shot]
    enemies = [enemy]
    combat.update_projectiles(0.016, projectiles, enemies, (2400, 1600))
    assert len(projectiles) == 1
    assert len(enemies) == 1


def test_expired_projectile_removed():
    shot = Projectile(pos=pygame.Vector2(0, 0), vel=pygame.Vector2(0, 0), damage=5, ttl=0.01)
    projectiles = [shot]
    combat.update_projectiles(0.02, projectiles, [], (2400, 1600))
    assert projectiles == []


def test_enemy_contact_damages_player():
    player = Player(pos=pygame.Vector2(500, 500))
    enemy = Golem(pos=pygame.Vector2(500, 500))
    combat.update_enemies(0.5, [enemy], player, (2400, 1600))
    assert player.hp == config.PLAYER_MAX_HP - config.GOLEM_CONTACT_DPS * 0.5


def test_invulnerable_player_takes_no_contact_damage():
    player = Player(pos=pygame.Vector2(500, 500), iframe_timer=1.0)
    enemy = Golem(pos=pygame.Vector2(500, 500))
    combat.update_enemies(0.5, [enemy], player, (2400, 1600))
    assert player.hp == config.PLAYER_MAX_HP


def test_distant_enemy_deals_no_damage():
    player = Player(pos=pygame.Vector2(0, 0))
    enemy = Golem(pos=pygame.Vector2(2000, 1500))
    combat.update_enemies(0.5, [enemy], player, (2400, 1600))
    assert player.hp == config.PLAYER_MAX_HP


@pytest.mark.parametrize("start,expected", [(5, 3), (4, 2), (1, 1), (0, 0)])
def test_death_penalty_halves_round_up(start, expected):
    backpack = Folder(cap_mb=1000)
    backpack.add(FRAGMENT, start)
    combat.apply_death_penalty(backpack)
    assert backpack.count(FRAGMENT) == expected


def test_death_penalty_cannot_shelter_one_kind_by_dropping_another(monkeypatch):
    # rows() only surfaces kinds listed in CATALOGUE, which normally holds just
    # FRAGMENT. To exercise the per-row-vs-per-total distinction we need a
    # second visible kind, so we patch the name storage.py bound at import time
    # (`from game.items.item_kinds import CATALOGUE`) rather than the catalogue
    # module itself. Do not delete this patch as "unnecessary" -- without it
    # HEAVY's row is invisible to apply_death_penalty and the test degrades
    # back into test_death_penalty_halves_round_up.
    monkeypatch.setattr("game.inventory.storage.CATALOGUE", (FRAGMENT, HEAVY))

    backpack = Folder(cap_mb=1000)
    backpack.add(FRAGMENT, 5)
    backpack.add(HEAVY, 1)
    combat.apply_death_penalty(backpack)

    # Per-row: each kind keeps its own rounded-up half (5 -> 3, 1 -> 1).
    # A per-total implementation would instead halve the combined count
    # (6 -> 3 kept) and could zero out the smaller HEAVY row entirely to get
    # there, which is exactly the "sheltering" the per-row rewrite prevents.
    assert backpack.count(FRAGMENT) == 3
    assert backpack.count(HEAVY) == 1
