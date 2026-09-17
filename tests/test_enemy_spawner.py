import random

import pygame

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
    result = spawner.update(
        config.GOLEM_SPAWN_INTERVAL, enemies, WORLD.center, _core(), random.Random(1), WORLD
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
    player_pos = core.pos + pygame.Vector2(600, 0)  # inside the map, off the core
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
