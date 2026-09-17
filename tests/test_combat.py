import pygame
import pytest

from game import config
from game.entities.core import Core
from game.entities.enemy import Golem
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.inventory.storage import Container
from game.items.item_kinds import CORE_SHARD, ItemKind
from game.items.tools import MiningTool, WeaponTool
from game.systems import combat
from game.world.map import WorldMap

# A second kind, used only to prove apply_death_penalty halves per row rather
# than per total (see test_death_penalty_cannot_shelter_one_kind_by_dropping_another).
HEAVY = ItemKind(key="heavy", name="벌크", stack_max=10, color=(1, 2, 3))

WORLD = WorldMap()
CENTRE = WORLD.center
# Most combat tests predate the ward; an unlit core shelters nothing.
UNLIT = Core(pos=pygame.Vector2(CENTRE))


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
    enemy = Golem(pos=pygame.Vector2(CENTRE), hp=5)
    shot = Projectile(pos=pygame.Vector2(CENTRE), vel=pygame.Vector2(0, 0), damage=5)
    projectiles = [shot]
    enemies = [enemy]
    combat.update_projectiles(0.016, projectiles, enemies, WORLD)
    assert projectiles == []  # consumed on hit
    assert enemies == []  # died at 0 hp


def test_projectile_misses_and_survives():
    enemy = Golem(pos=CENTRE + pygame.Vector2(900, 900), hp=5)
    shot = Projectile(pos=pygame.Vector2(CENTRE), vel=pygame.Vector2(10, 0), damage=5, ttl=1.0)
    projectiles = [shot]
    enemies = [enemy]
    combat.update_projectiles(0.016, projectiles, enemies, WORLD)
    assert len(projectiles) == 1
    assert len(enemies) == 1


def test_expired_projectile_removed():
    shot = Projectile(pos=pygame.Vector2(CENTRE), vel=pygame.Vector2(0, 0), damage=5, ttl=0.01)
    projectiles = [shot]
    combat.update_projectiles(0.02, projectiles, [], WORLD)
    assert projectiles == []


def test_enemy_contact_damages_player():
    player = Player(pos=pygame.Vector2(CENTRE))
    enemy = Golem(pos=pygame.Vector2(CENTRE))
    combat.update_enemies(0.5, [enemy], player, WORLD, UNLIT)
    assert player.hp == config.PLAYER_MAX_HP - config.GOLEM_CONTACT_DPS * 0.5


def test_invulnerable_player_takes_no_contact_damage():
    player = Player(pos=pygame.Vector2(CENTRE), iframe_timer=1.0)
    enemy = Golem(pos=pygame.Vector2(CENTRE))
    combat.update_enemies(0.5, [enemy], player, WORLD, UNLIT)
    assert player.hp == config.PLAYER_MAX_HP


def test_distant_enemy_deals_no_damage():
    player = Player(pos=pygame.Vector2(CENTRE))
    enemy = Golem(pos=CENTRE + pygame.Vector2(1800, 0))
    combat.update_enemies(0.5, [enemy], player, WORLD, UNLIT)
    assert player.hp == config.PLAYER_MAX_HP


@pytest.mark.parametrize(
    "start,kept",
    [(32, 16), (7, 3), (5, 2), (2, 1), (1, 0), (0, 0)],
)
def test_death_penalty_drops_the_rounded_up_half(start, kept):
    # Rounding up on the DROPPED amount means a lone rare item is lost, which is
    # what makes the five hotbar slots a real decision every trip.
    backpack = Container(slots=100)
    backpack.add(CORE_SHARD, start)
    combat.apply_death_penalty(backpack)
    assert backpack.count(CORE_SHARD) == kept


def test_death_penalty_cannot_shelter_one_kind_by_dropping_another(monkeypatch):
    # rows() only surfaces kinds listed in CATALOGUE, which normally holds just
    # CORE_SHARD. To exercise the per-row-vs-per-total distinction we need a
    # second visible kind, so we patch the name storage.py bound at import time
    # (`from game.items.item_kinds import CATALOGUE`) rather than the catalogue
    # module itself. Do not delete this patch as "unnecessary" -- without it
    # HEAVY's row is invisible to apply_death_penalty and the test degrades
    # back into test_death_penalty_halves_round_up.
    monkeypatch.setattr("game.inventory.storage.CATALOGUE", (CORE_SHARD, HEAVY))

    backpack = Container(slots=100)
    backpack.add(CORE_SHARD, 5)
    backpack.add(HEAVY, 1)
    combat.apply_death_penalty(backpack)

    # Per-row: each kind drops its own rounded-up half (5 -> 3 dropped, 2 kept;
    # 1 -> 1 dropped, 0 kept). A per-total implementation would instead halve the
    # combined count and could spare the smaller HEAVY row entirely to get there,
    # which is exactly the "sheltering" the per-row rule prevents.
    assert backpack.count(CORE_SHARD) == 2
    assert backpack.count(HEAVY) == 0


def test_golems_cannot_enter_the_ward():
    core = Core(pos=pygame.Vector2(CENTRE))
    core.ignite()
    player = Player(pos=pygame.Vector2(CENTRE))  # standing at the core
    golem = Golem(pos=CENTRE + pygame.Vector2(core.ward_radius + 5, 0))
    for _ in range(200):
        combat.update_enemies(config.FIXED_DT, [golem], player, WORLD, core)
    # It chases the player, but the ward holds it on the rim.
    assert CENTRE.distance_to(golem.pos) >= core.ward_radius - 1e-6


def test_an_unlit_core_shelters_nothing():
    core = Core(pos=pygame.Vector2(CENTRE))  # never ignited
    player = Player(pos=pygame.Vector2(CENTRE))
    golem = Golem(pos=CENTRE + pygame.Vector2(200, 0))
    combat.update_enemies(1.0, [golem], player, WORLD, core)
    assert CENTRE.distance_to(golem.pos) < 200  # walked straight in
