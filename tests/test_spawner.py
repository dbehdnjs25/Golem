import random

import pygame

from game import config
from game.entities.core import Core
from game.entities.fragment import Fragment
from game.systems.spawner import Spawner
from game.world.map import WorldMap

WORLD = WorldMap()
CORE = Core(pos=WORLD.center)
# Standing clear of the core's sync zone so spawns are not all rejected.
PLAYER = CORE.pos + pygame.Vector2(1_000, 0)


def test_no_spawn_before_interval():
    sp = Spawner()
    frags = []
    assert sp.update(0.1, frags, CORE, random.Random(1), WORLD, PLAYER) is None
    assert frags == []


def test_spawns_after_interval():
    sp = Spawner()
    frags = []
    result = sp.update(config.SPAWN_INTERVAL, frags, CORE, random.Random(1), WORLD, PLAYER)
    assert result is not None
    assert frags == [result]


def test_respects_max_fragments():
    sp = Spawner(max_fragments=2)
    frags = [
        Fragment(pos=pygame.Vector2(100, 100)),
        Fragment(pos=pygame.Vector2(200, 200)),
    ]  # already at cap
    assert sp.update(config.SPAWN_INTERVAL, frags, CORE, random.Random(1), WORLD, PLAYER) is None
    assert len(frags) == 2


def test_deterministic_with_seed():
    a = Spawner().update(config.SPAWN_INTERVAL, [], CORE, random.Random(42), WORLD, PLAYER)
    b = Spawner().update(config.SPAWN_INTERVAL, [], CORE, random.Random(42), WORLD, PLAYER)
    assert a.pos == b.pos


def test_spawn_avoids_core_sync_zone():
    sp = Spawner()
    for seed in range(50):
        frags = []
        frag = sp.update(config.SPAWN_INTERVAL, frags, CORE, random.Random(seed), WORLD, PLAYER)
        if frag is not None:
            assert CORE.pos.distance_to(frag.pos) >= CORE.sync_radius


def test_spawned_nodes_carry_an_ore_kind_that_varies():
    # The ore table decides what a node yields, so nodes are no longer all the
    # same thing -- and the outward spawn bias means they span several bands.
    fragments = []
    spawner = Spawner()
    rng = random.Random(21)
    for _ in range(40):
        spawner.update(config.SPAWN_INTERVAL, fragments, CORE, rng, WORLD, PLAYER)
    assert fragments, "the spawner should have produced something in 40 attempts"
    assert all(f.kind is not None for f in fragments)
    assert len({f.kind for f in fragments}) > 1


def test_nodes_spawn_within_reach_of_the_player():
    # The map is 676x bigger than it was. Scattering a fixed handful of nodes
    # over all of it would leave nothing to find, so spawns follow the player.
    fragments = []
    spawner = Spawner()
    rng = random.Random(3)
    player_pos = CORE.pos + pygame.Vector2(20_000, 0)
    for _ in range(30):
        spawner.update(config.SPAWN_INTERVAL, fragments, CORE, rng, WORLD, player_pos)
    assert fragments
    assert all(player_pos.distance_to(f.pos) <= config.SPAWN_RADIUS for f in fragments)
    assert all(WORLD.contains(f.pos) for f in fragments)
