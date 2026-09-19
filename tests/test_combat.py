import pygame

from game import config
from game.entities.core import Core
from game.entities.enemy import Golem
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.inventory.storage import Container
from game.items.item_kinds import CORE_SHARD, WORN_PACK, ItemKind
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


def test_golems_cannot_enter_the_ward():
    core = Core(pos=pygame.Vector2(CENTRE))
    core.ignite()
    player = Player(pos=pygame.Vector2(CENTRE))  # standing at the core
    golem = Golem(pos=CENTRE + pygame.Vector2(core.ward_radius + 5, 0))
    for _ in range(200):
        combat.update_enemies(config.FIXED_DT, [golem], player, WORLD, core)
    # It chases the player, but the ward holds it just outside the rim -- and
    # "outside" has to read as outside, since is_in_ward's boundary is inclusive.
    assert CENTRE.distance_to(golem.pos) > core.ward_radius
    assert core.is_in_ward(golem.pos) is False


def test_an_unlit_core_shelters_nothing():
    core = Core(pos=pygame.Vector2(CENTRE))  # never ignited
    player = Player(pos=pygame.Vector2(CENTRE))
    golem = Golem(pos=CENTRE + pygame.Vector2(200, 0))
    combat.update_enemies(1.0, [golem], player, WORLD, core)
    assert CENTRE.distance_to(golem.pos) < 200  # walked straight in


def test_death_drops_the_whole_pack_and_everything_in_it():
    # With no base inventory there is nowhere for a "kept half" to sit, so the
    # pack goes whole. What the player keeps is the hotbar, and only that.
    pack = Container.empty(4)
    pack.add(CORE_SHARD, 7)
    pack.add(HEAVY, 1)
    pile = combat.apply_death_penalty(pygame.Vector2(CENTRE), pack, WORN_PACK)
    assert pile is not None
    assert pile.contents.count(CORE_SHARD) == 7
    assert pile.contents.count(HEAVY) == 1
    assert pile.pack is WORN_PACK
    assert pile.pos == CENTRE


def test_dying_with_no_backpack_leaves_nothing_behind():
    assert combat.apply_death_penalty(pygame.Vector2(CENTRE), None, None) is None


def test_the_penalty_cannot_reach_the_hotbar():
    # Pinned so the signature cannot quietly grow one later.
    import inspect

    assert "hotbar" not in inspect.signature(combat.apply_death_penalty).parameters
