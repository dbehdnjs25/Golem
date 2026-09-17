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


def test_clamp_keeps_a_body_inside_the_circle():
    world = WorldMap()
    p = _at(world, 30, world.radius * 2)
    world.clamp(p, 14)
    assert world.contains(p)
    assert world.center.distance_to(p) == pytest.approx(world.radius - 14)


def test_random_points_all_land_inside_the_map():
    world = WorldMap()
    rng = random.Random(3)
    points = [world.random_point(rng) for _ in range(500)]
    assert all(world.contains(p) for p in points)
    assert all(world.biome_at(p) is not None for p in points)


def test_random_points_are_reproducible_from_a_seed():
    world = WorldMap()
    a = [world.random_point(random.Random(11)) for _ in range(3)]
    b = [world.random_point(random.Random(11)) for _ in range(3)]
    assert a == b


def test_uniform_random_points_do_not_bunch_at_the_centre():
    # Sampling radius uniformly would put half the points inside 0.5R, which is
    # only a quarter of the area. Area-uniform sampling gives a mean radius of
    # 2R/3, and that is what this pins down.
    world = WorldMap()
    rng = random.Random(5)
    radii = [world.center.distance_to(world.random_point(rng)) for _ in range(4000)]
    mean = sum(radii) / len(radii)
    assert abs(mean / world.radius - 2 / 3) < 0.03


def test_outward_sampling_pushes_points_towards_the_edge():
    # Resources get denser away from the core, so the spawner needs a sampler
    # that is biased outward. Density proportional to radius gives a mean of
    # 3R/4, measurably further out than the flat 2R/3.
    world = WorldMap()
    rng = random.Random(5)
    radii = [world.center.distance_to(world.random_point(rng, outward=True)) for _ in range(4000)]
    mean = sum(radii) / len(radii)
    assert abs(mean / world.radius - 3 / 4) < 0.03


def test_there_is_one_temple_per_biome_in_ring_order():
    world = WorldMap(rotation=41.0)
    sites = world.temple_sites(random.Random(2))
    assert len(sites) == len(biomes.RING_BIOMES)
    for site, biome in zip(sites, biomes.RING_BIOMES, strict=True):
        assert world.biome_at(site) is biome


def test_temples_avoid_the_inner_and_outer_edges_of_the_ring():
    # The spec asks for margin at both ends so a temple never looks like it is
    # falling off the map or leaking into the grassland.
    world = WorldMap()
    for seed in range(20):
        for site in world.temple_sites(random.Random(seed)):
            distance = world.center.distance_to(site)
            assert config.TEMPLE_BAND_INNER <= distance <= config.TEMPLE_BAND_OUTER
            assert world.grassland_radius < distance < world.radius


def test_temples_are_reproducible_from_a_seed():
    world = WorldMap(rotation=41.0)
    assert world.temple_sites(random.Random(9)) == world.temple_sites(random.Random(9))


def test_different_seeds_move_the_temples():
    world = WorldMap(rotation=41.0)
    assert world.temple_sites(random.Random(1)) != world.temple_sites(random.Random(2))


def test_temples_stay_clear_of_the_sector_seams():
    # A temple sitting on a boundary reads as belonging to the neighbour, so it
    # is inset from both edges of its own sector.
    world = WorldMap(rotation=0.0)
    inset = config.TEMPLE_ANGLE_INSET
    for seed in range(20):
        for i, site in enumerate(world.temple_sites(random.Random(seed))):
            offset = site - world.center
            degrees = math.degrees(math.atan2(offset.y, offset.x)) % 360.0
            within = (degrees - i * world.sector_degrees) % 360.0
            assert inset <= within <= world.sector_degrees - inset
