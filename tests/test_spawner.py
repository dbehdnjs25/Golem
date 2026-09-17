import random

import pygame

from game import config
from game.entities.core import Core
from game.entities.fragment import Fragment
from game.systems.spawner import Spawner
from game.world.map import WorldMap

WORLD = WorldMap()
CORE = Core(pos=WORLD.center)


def test_no_spawn_before_interval():
    sp = Spawner()
    frags = []
    assert sp.update(0.1, frags, CORE, random.Random(1), WORLD) is None
    assert frags == []


def test_spawns_after_interval():
    sp = Spawner()
    frags = []
    result = sp.update(config.SPAWN_INTERVAL, frags, CORE, random.Random(1), WORLD)
    assert result is not None
    assert frags == [result]


def test_respects_max_fragments():
    sp = Spawner(max_fragments=2)
    frags = [
        Fragment(pos=pygame.Vector2(100, 100)),
        Fragment(pos=pygame.Vector2(200, 200)),
    ]  # already at cap
    assert sp.update(config.SPAWN_INTERVAL, frags, CORE, random.Random(1), WORLD) is None
    assert len(frags) == 2


def test_deterministic_with_seed():
    a = Spawner().update(config.SPAWN_INTERVAL, [], CORE, random.Random(42), WORLD)
    b = Spawner().update(config.SPAWN_INTERVAL, [], CORE, random.Random(42), WORLD)
    assert a.pos == b.pos


def test_spawn_avoids_core_sync_zone():
    sp = Spawner()
    for seed in range(50):
        frags = []
        frag = sp.update(config.SPAWN_INTERVAL, frags, CORE, random.Random(seed), WORLD)
        if frag is not None:
            assert CORE.pos.distance_to(frag.pos) >= CORE.sync_radius


def test_spawned_nodes_carry_an_ore_kind_that_varies():
    # The ore table decides what a node yields, so nodes are no longer all the
    # same thing -- and the outward spawn bias means they span several bands.
    fragments = []
    spawner = Spawner()
    rng = random.Random(21)
    for _ in range(40):
        spawner.update(config.SPAWN_INTERVAL, fragments, CORE, rng, WORLD)
    assert fragments, "the spawner should have produced something in 40 attempts"
    assert all(f.kind is not None for f in fragments)
    assert len({f.kind for f in fragments}) > 1
