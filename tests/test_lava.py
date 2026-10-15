import random

import pygame

from game import config
from game.entities.lava import LavaPool
from game.entities.player import Player
from game.world import biomes, lava
from game.world.map import WorldMap

WORLD = WorldMap(rotation=31.0)


def _pools(seed: int = 1) -> list[LavaPool]:
    return lava.place(WORLD, random.Random(seed))


def test_lava_only_stands_in_the_burnt_forest():
    # It is what the burnt forest IS. Anywhere else it would be a hazard with
    # no story behind it.
    for seed in range(8):
        for pool in _pools(seed):
            assert WORLD.biome_at(pool.pos) is biomes.BURNT_FOREST


def test_the_same_seed_pours_the_same_lava():
    assert [(p.pos, p.radius) for p in _pools(4)] == [(p.pos, p.radius) for p in _pools(4)]


def test_different_seeds_move_it():
    assert [p.pos for p in _pools(1)] != [p.pos for p in _pools(2)]


def test_pools_do_not_overlap():
    # Two merged pools read as one strangely-shaped pool, and the obsidian
    # belt around them would double up in the seam.
    for seed in range(8):
        pools = _pools(seed)
        for i, a in enumerate(pools):
            for b in pools[i + 1 :]:
                assert a.pos.distance_to(b.pos) > a.radius + b.radius


def test_there_is_enough_of_it_to_find():
    # The only source of obsidian hangs off these. Too few and the biome is a
    # long walk for nothing.
    for seed in range(8):
        assert len(_pools(seed)) >= config.LAVA_POOLS_MIN


def test_standing_in_it_is_standing_in_it():
    pool = LavaPool(pos=pygame.Vector2(0, 0), radius=200.0)
    assert lava.burns(pygame.Vector2(0, 0), [pool])
    assert lava.burns(pygame.Vector2(199, 0), [pool])
    assert not lava.burns(pygame.Vector2(201, 0), [pool])


def test_nothing_burns_where_there_is_no_lava():
    assert not lava.burns(pygame.Vector2(0, 0), [])


def test_walking_in_hurts_and_walking_out_stops_it():
    from game.systems import survival

    pool = LavaPool(pos=pygame.Vector2(0, 0), radius=200.0)
    player = Player(pos=pygame.Vector2(0, 0))
    survival.update_lava(1.0, player, [pool])
    hurt = player.hp
    assert hurt < config.PLAYER_MAX_HP

    player.pos.update(1000, 0)
    survival.update_lava(1.0, player, [pool])
    assert player.hp == hurt


def test_it_is_a_hazard_not_an_execution():
    # A visible, stationary hazard you can choose to cross. Instant death would
    # make it a wall, and a wall is not a decision.
    from game.systems import survival

    pool = LavaPool(pos=pygame.Vector2(0, 0), radius=200.0)
    player = Player(pos=pygame.Vector2(0, 0))
    crossing = 2 * pool.radius / config.PLAYER_SPEED
    survival.update_lava(crossing, player, [pool])
    assert player.hp > 0


def test_a_long_paddle_does_kill_you():
    from game.systems import survival

    pool = LavaPool(pos=pygame.Vector2(0, 0), radius=200.0)
    player = Player(pos=pygame.Vector2(0, 0))
    survival.update_lava(20.0, player, [pool])
    assert player.hp <= 0


def test_the_ward_does_not_hold_lava_back():
    # It is ground, not a creature. Nothing about a ward says the floor stops
    # being hot -- and no lava stands in the grassland anyway.
    from game.entities.core import Core
    from game.systems import survival

    core = Core(pos=pygame.Vector2(0, 0))
    core.ignite()
    pool = LavaPool(pos=pygame.Vector2(0, 0), radius=200.0)
    player = Player(pos=pygame.Vector2(0, 0))
    survival.update_lava(1.0, player, [pool])
    assert player.hp < config.PLAYER_MAX_HP


# --- the obsidian belt ----------------------------------------------------


def _belt(seed: int = 1):
    pools = _pools(seed)
    return pools, lava.obsidian_sites(pools, random.Random(seed))


def test_obsidian_stone_stands_only_around_a_pool():
    # The whole point of the change. Mining obsidian means standing next to
    # the hazard; scattered across the biome it cost nothing at all.
    for seed in range(6):
        pools, sites = _belt(seed)
        for spot in sites:
            assert min(p.pos.distance_to(spot) - p.radius for p in pools) <= config.OBSIDIAN_BELT


def test_none_of_it_stands_in_the_lava():
    # An unreachable vein is the same as no vein.
    for seed in range(6):
        pools, sites = _belt(seed)
        for spot in sites:
            assert not lava.burns(spot, pools)


def test_every_pool_is_worth_walking_to():
    for seed in range(6):
        pools, sites = _belt(seed)
        for pool in pools:
            near = [
                s for s in sites if pool.pos.distance_to(s) <= pool.radius + config.OBSIDIAN_BELT
            ]
            assert near, f"seed {seed}: a pool with nothing around it"


def test_the_belt_is_reproducible_from_a_seed():
    assert _belt(4)[1] == _belt(4)[1]


def test_the_ordinary_ground_never_yields_obsidian_any_more():
    import random as rnd

    from game.items.item_kinds import OBSIDIAN
    from game.world.resources import node_at

    for biome in (biomes.BURNT_FOREST, biomes.BOG, None):
        rng = rnd.Random(3)
        drawn = {node_at(0.8, rng, biome) for _ in range(4000)}
        assert OBSIDIAN not in drawn, biome
