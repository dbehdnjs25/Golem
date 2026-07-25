import random

import pygame

from game import config
from game.entities.core import Core
from game.entities.enemy import Virus
from game.systems.enemy_spawner import EnemySpawner


def _core():
    return Core(pos=pygame.Vector2(config.WORLD_WIDTH / 2, config.WORLD_HEIGHT / 2))


def test_no_spawn_before_interval():
    spawner = EnemySpawner()
    enemies: list[Virus] = []
    assert spawner.update(0.1, enemies, pygame.Vector2(10, 10), _core(), random.Random(1)) is None
    assert enemies == []


def test_spawns_after_interval():
    spawner = EnemySpawner()
    enemies: list[Virus] = []
    result = spawner.update(
        config.VIRUS_SPAWN_INTERVAL, enemies, pygame.Vector2(10, 10), _core(), random.Random(1)
    )
    assert isinstance(result, Virus)
    assert len(enemies) == 1


def test_respects_max_cap():
    spawner = EnemySpawner(max_enemies=1)
    enemies = [Virus(pos=pygame.Vector2(10, 10))]
    result = spawner.update(
        config.VIRUS_SPAWN_INTERVAL, enemies, pygame.Vector2(10, 10), _core(), random.Random(1)
    )
    assert result is None
    assert len(enemies) == 1


def test_spawn_avoids_core_sync_zone_and_player():
    spawner = EnemySpawner()
    enemies: list[Virus] = []
    core = _core()
    player_pos = pygame.Vector2(100, 100)
    v = spawner.update(config.VIRUS_SPAWN_INTERVAL, enemies, player_pos, core, random.Random(7))
    assert v is not None
    assert core.pos.distance_to(v.pos) >= core.sync_radius
    assert player_pos.distance_to(v.pos) >= 300
