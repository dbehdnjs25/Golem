import dataclasses
import math
import random

import pygame
import pytest

from game import config
from game.world import biomes
from game.world.map import WorldMap


def _at(world: WorldMap, degrees: float, dist: float) -> pygame.Vector2:
    """A world point ``dist`` from the centre, at ``degrees`` (0 = +x, y grows down)."""
    a = math.radians(degrees)
    return world.center + pygame.Vector2(math.cos(a), math.sin(a)) * dist


def test_the_centre_sits_at_the_middle_of_the_world_square():
    world = WorldMap()
    assert world.center == pygame.Vector2(config.MAP_RADIUS, config.MAP_RADIUS)
    assert config.WORLD_SIZE == (2 * config.MAP_RADIUS, 2 * config.MAP_RADIUS)


def test_the_grassland_is_about_a_third_of_the_map():
    world = WorldMap()
    ratio = (world.grassland_radius / world.radius) ** 2
    assert 0.28 < ratio < 0.40


def test_contains_is_the_circle_not_the_square():
    world = WorldMap()
    assert world.contains(world.center)
    assert world.contains(_at(world, 0, world.radius - 1))
    assert not world.contains(_at(world, 0, world.radius + 1))
    # a square corner is outside the inscribed circle
    assert not world.contains(pygame.Vector2(0, 0))


def test_the_centre_is_grassland():
    world = WorldMap()
    assert world.biome_at(world.center) is biomes.GRASSLAND
    assert world.biome_at(_at(world, 123, world.grassland_radius - 1)) is biomes.GRASSLAND


def test_outside_the_map_has_no_biome():
    world = WorldMap()
    assert world.biome_at(_at(world, 45, world.radius + 10)) is None


def test_the_ring_is_split_into_five_sectors_in_order():
    world = WorldMap(rotation=0.0)
    mid = (world.grassland_radius + world.radius) / 2
    for i, biome in enumerate(biomes.RING_BIOMES):
        degrees = i * 72 + 36  # the middle of sector i
        assert world.biome_at(_at(world, degrees, mid)) is biome


def test_rotation_turns_the_whole_ring():
    turned = WorldMap(rotation=72.0)
    mid = (turned.grassland_radius + turned.radius) / 2
    # sector 0 now starts at 72 degrees, so its middle is at 108
    assert turned.biome_at(_at(turned, 108, mid)) is biomes.RING_BIOMES[0]
    # and what used to be sector 0's middle now belongs to the last sector
    assert turned.biome_at(_at(turned, 36, mid)) is biomes.RING_BIOMES[-1]


def test_rotation_does_not_change_the_grassland():
    for rotation in (0.0, 37.0, 180.0, 359.0):
        world = WorldMap(rotation=rotation)
        assert world.biome_at(world.center) is biomes.GRASSLAND


def test_every_ring_point_lands_in_some_biome():
    world = WorldMap(rotation=17.0)
    mid = (world.grassland_radius + world.radius) / 2
    seen = {world.biome_at(_at(world, d, mid)) for d in range(0, 360, 3)}
    assert None not in seen
    assert seen == set(biomes.RING_BIOMES)


def test_create_randomises_the_rotation_reproducibly():
    a = WorldMap.create(random.Random(7))
    b = WorldMap.create(random.Random(7))
    c = WorldMap.create(random.Random(8))
    assert a == b  # same seed, same map
    assert a.rotation != c.rotation
    assert 0.0 <= a.rotation < 360.0


def test_distance_fraction_runs_zero_at_the_core_to_one_at_the_edge():
    world = WorldMap()
    assert world.distance_fraction(world.center) == 0.0
    assert world.distance_fraction(_at(world, 0, world.radius)) == pytest.approx(1.0)
    assert world.distance_fraction(_at(world, 0, world.radius * 2)) == 1.0  # clamped
    assert world.distance_fraction(_at(world, 0, world.radius / 2)) == pytest.approx(0.5)


def test_the_map_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        WorldMap().rotation = 1.0  # type: ignore[misc]
