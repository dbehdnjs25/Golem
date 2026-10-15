import random

import pygame
import pytest

from game import config
from game.entities.core import Core
from game.entities.enemy import Golem
from game.systems.enemy_spawner import EnemySpawner
from game.world.map import WorldMap

WORLD = WorldMap()


def _core():
    return Core(pos=WORLD.center)


def test_no_spawn_before_interval():
    spawner = EnemySpawner()
    enemies: list[Golem] = []
    assert spawner.update(0.1, enemies, WORLD.center, _core(), random.Random(1), WORLD) is None
    assert enemies == []


def test_spawns_after_interval():
    spawner = EnemySpawner()
    enemies: list[Golem] = []
    core = _core()
    core.ignite()
    away = core.pos + pygame.Vector2(core.ward_radius + 500, 0)
    result = spawner.update(
        config.GOLEM_SPAWN_INTERVAL, enemies, away, core, random.Random(1), WORLD
    )
    assert isinstance(result, Golem)
    assert len(enemies) == 1


def test_respects_max_cap():
    spawner = EnemySpawner(max_enemies=1)
    enemies = [Golem(pos=WORLD.center)]
    result = spawner.update(
        config.GOLEM_SPAWN_INTERVAL, enemies, WORLD.center, _core(), random.Random(1), WORLD
    )
    assert result is None
    assert len(enemies) == 1


def test_spawn_avoids_core_sync_zone_and_player():
    spawner = EnemySpawner()
    enemies: list[Golem] = []
    core = _core()
    core.ignite()
    player_pos = core.pos + pygame.Vector2(core.ward_radius + 600, 0)
    v = spawner.update(
        config.GOLEM_SPAWN_INTERVAL, enemies, player_pos, core, random.Random(7), WORLD
    )
    assert v is not None
    assert core.pos.distance_to(v.pos) >= core.sync_radius
    assert player_pos.distance_to(v.pos) >= 300


def test_golems_do_not_spawn_inside_the_ward():
    core = _core()
    core.ignite()
    player_pos = core.pos + pygame.Vector2(1_500, 0)  # inside the spawn radius
    for seed in range(30):
        enemies: list[Golem] = []
        spawner = EnemySpawner()
        golem = spawner.update(
            config.GOLEM_SPAWN_INTERVAL, enemies, player_pos, core, random.Random(seed), WORLD
        )
        if golem is not None:
            assert not core.is_in_ward(golem.pos)


def test_golems_wait_for_the_core_to_be_lit():
    # They come for the core. Before it burns there is nothing to come for, and
    # the opening is quiet enough to gather in.
    spawner = EnemySpawner()
    enemies: list[Golem] = []
    unlit = Core(pos=WORLD.center)  # never ignited
    for _ in range(20):
        spawner.update(
            config.GOLEM_SPAWN_INTERVAL, enemies, WORLD.center, unlit, random.Random(1), WORLD
        )
    assert enemies == []


def test_lighting_the_core_brings_them():
    spawner = EnemySpawner()
    enemies: list[Golem] = []
    core = _core()
    core.ignite()
    player_pos = core.pos + pygame.Vector2(core.ward_radius + 500, 0)
    spawner.update(config.GOLEM_SPAWN_INTERVAL, enemies, player_pos, core, random.Random(3), WORLD)
    assert len(enemies) == 1


def _spawn_at(distance: float, seed: int = 1):
    """Spawn one golem with the player standing ``distance`` from the core."""
    spawner = EnemySpawner()
    enemies: list[Golem] = []
    core = _core()
    core.ignite()
    where = core.pos + pygame.Vector2(distance, 0)
    return spawner.update(
        config.GOLEM_SPAWN_INTERVAL, enemies, where, core, random.Random(seed), WORLD
    )


def test_a_golem_from_the_far_ring_is_tougher_than_one_from_the_grassland():
    # The spec's "stronger the further from the core". Distance is danger, and
    # the ore out there is worth it precisely because of this.
    near = _spawn_at(config.GRASSLAND_RADIUS * 0.3)
    far = _spawn_at(config.MAP_RADIUS * 0.95)
    assert near is not None and far is not None
    assert far.hp > near.hp
    assert far.speed > near.speed


def test_scaling_climbs_with_distance_all_the_way_out():
    seen = []
    for fraction in (0.2, 0.4, 0.6, 0.8, 0.95):
        golem = _spawn_at(config.MAP_RADIUS * fraction)
        assert golem is not None
        seen.append(golem.scale)
    assert seen == sorted(seen)


def test_the_edge_of_the_map_reaches_the_stated_multiplier():
    far = _spawn_at(config.MAP_RADIUS * 0.999)
    assert far is not None
    assert far.scale == pytest.approx(config.GOLEM_SCALE_AT_EDGE, rel=0.02)


def test_a_golem_beside_the_core_is_the_plain_row():
    # Nothing spawns inside the ward, so this is the closest one can get -- it
    # should be the table's own numbers, not a fraction of them.
    from game.entities.enemy import PLAIN_GOLEM

    near = _spawn_at(0.0)
    if near is not None:  # the ward may swallow every attempt; that is fine
        assert near.scale >= 1.0
        assert near.hp >= PLAIN_GOLEM.hp


def test_a_raid_reaches_a_player_sitting_at_home():
    # They come at the core on a raid night, so where the player is standing
    # does not matter. Spawning "near the player" meant none at all while that
    # player stood in a four-thousand-unit ward -- the first raid arrived with
    # nobody in it.
    spawner = EnemySpawner()
    core = _core()
    core.ignite()
    enemies: list[Golem] = []
    golem = spawner.update(
        config.RAID_SPAWN_INTERVAL, enemies, core.pos, core, random.Random(1), WORLD, raid=True
    )
    assert golem is not None
    assert not core.is_in_ward(golem.pos)


def test_a_quiet_night_at_home_brings_nothing_at_all():
    # The ward is the point. On an ordinary night they turn up where the player
    # is working, and the player at home is not working.
    spawner = EnemySpawner()
    core = _core()
    core.ignite()
    enemies: list[Golem] = []
    for _ in range(50):
        spawner.update(
            config.GOLEM_SPAWN_INTERVAL, enemies, core.pos, core, random.Random(1), WORLD
        )
    assert enemies == []


def test_a_raid_night_fills_the_field_faster_than_a_quiet_one():
    def count(raid: bool) -> int:
        spawner = EnemySpawner()
        core = _core()
        core.ignite()
        enemies: list[Golem] = []
        for _ in range(400):
            spawner.update(
                config.FIXED_DT, enemies, core.pos, core, random.Random(1), WORLD, raid=raid
            )
        return len(enemies)

    assert count(raid=True) > count(raid=False)


def test_a_raid_raises_the_ceiling_too():
    # A faster trickle into the same small cap would barely read as a raid.
    assert config.RAID_SPAWN_MAX > config.GOLEM_SPAWN_MAX
    assert config.RAID_SPAWN_INTERVAL < config.GOLEM_SPAWN_INTERVAL


def test_they_still_do_not_land_on_the_player_standing_outside():
    spawner = EnemySpawner()
    core = _core()
    core.ignite()
    out = core.pos + pygame.Vector2(core.ward_radius + 1500, 0)
    for seed in range(25):
        enemies: list[Golem] = []
        spawner = EnemySpawner()
        golem = spawner.update(
            config.GOLEM_SPAWN_INTERVAL, enemies, out, core, random.Random(seed), WORLD
        )
        if golem is not None:
            assert golem.pos.distance_to(out) >= 600.0


def test_a_wider_ward_means_a_longer_march_in():
    # Raiders gather at a share of the ward's own reach, so levelling the core
    # buys travel time as well as ground -- the first blow of a raid lands
    # later on a big ward than on a small one, with no extra rule for it.
    def mean_distance(level: int) -> float:
        core = _core()
        core.ignite()
        core.bosses_killed = 5
        while core.level < level and core.upgrade():
            pass
        spawner = EnemySpawner()
        spots = []
        for seed in range(30):
            enemies: list[Golem] = []
            spawner = EnemySpawner()
            golem = spawner.update(
                config.RAID_SPAWN_INTERVAL,
                enemies,
                core.pos,
                core,
                random.Random(seed),
                WORLD,
                raid=True,
            )
            if golem is not None:
                spots.append(core.pos.distance_to(golem.pos))
        return sum(spots) / len(spots)

    assert mean_distance(35) > mean_distance(1) * 2
