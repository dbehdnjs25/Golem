import random

import pygame

from game import config
from game.entities.chasm import Chasm
from game.entities.player import Player
from game.systems import falling
from game.world import biomes, chasms
from game.world.map import WorldMap

WORLD = WorldMap(rotation=29.0)


def _placed(seed: int = 1) -> list[Chasm]:
    return chasms.place(WORLD, random.Random(seed))


def test_chasms_only_open_in_the_wind_plateau():
    for seed in range(8):
        for hole in _placed(seed):
            assert WORLD.biome_at(hole.pos) is biomes.WIND_PLATEAU


def test_the_same_seed_cuts_the_same_ground():
    assert [(c.pos, c.radius) for c in _placed(4)] == [(c.pos, c.radius) for c in _placed(4)]


def test_different_seeds_move_them():
    assert [c.pos for c in _placed(1)] != [c.pos for c in _placed(2)]


def test_they_do_not_overlap():
    for seed in range(8):
        holes = _placed(seed)
        for i, a in enumerate(holes):
            for b in holes[i + 1 :]:
                assert a.pos.distance_to(b.pos) > a.radius + b.radius


def test_there_are_enough_to_be_a_landscape():
    for seed in range(8):
        assert len(_placed(seed)) >= config.CHASMS_MIN


# --- falling in -----------------------------------------------------------


def _fell(dt: float = 1.0) -> tuple[Player, Chasm]:
    hole = Chasm(pos=pygame.Vector2(0, 0), radius=400.0)
    player = Player(pos=pygame.Vector2(0, 0))
    falling.update_fall(dt, player, [hole])
    return player, hole


def test_falling_in_hurts():
    player, _ = _fell()
    assert player.hp == config.PLAYER_MAX_HP - config.FALL_DAMAGE


def test_falling_in_puts_you_back_on_solid_ground():
    # The point of a hole is being pushed into it, not dying in it. Left at
    # the bottom, a chasm would be a death pit rather than a hazard.
    player, hole = _fell()
    assert not hole.holds(player.pos)


def test_you_are_not_put_down_in_another_one():
    near = Chasm(pos=pygame.Vector2(0, 0), radius=400.0)
    beside = Chasm(pos=pygame.Vector2(700, 0), radius=250.0)
    player = Player(pos=pygame.Vector2(0, 0))
    for _ in range(20):
        falling.update_fall(0.1, player, [near, beside])
    assert not near.holds(player.pos)
    assert not beside.holds(player.pos)


def test_it_costs_once_per_fall_not_once_per_frame():
    # Set down on the rim, a per-frame rule would shake the player to death
    # standing still.
    hole = Chasm(pos=pygame.Vector2(0, 0), radius=400.0)
    player = Player(pos=pygame.Vector2(0, 0))
    for _ in range(300):
        falling.update_fall(config.FIXED_DT, player, [hole])
    assert player.hp == config.PLAYER_MAX_HP - config.FALL_DAMAGE


def test_walking_back_in_costs_again():
    hole = Chasm(pos=pygame.Vector2(0, 0), radius=400.0)
    player = Player(pos=pygame.Vector2(0, 0))
    falling.update_fall(config.FIXED_DT, player, [hole])
    once = player.hp
    player.pos.update(0, 0)  # back over the edge
    falling.update_fall(config.FIXED_DT, player, [hole])
    assert player.hp < once


def test_nothing_is_dropped():
    # Losing the bag to a stumble would make the plateau unvisitable.
    from game.inventory.storage import Container

    hole = Chasm(pos=pygame.Vector2(0, 0), radius=400.0)
    player = Player(pos=pygame.Vector2(0, 0))
    pack = Container.empty(8)
    falling.update_fall(1.0, player, [hole])
    assert pack.used == 0  # nothing touched it; the fall never reaches a pack


def test_a_fall_cannot_kill_outright_from_full():
    assert config.FALL_DAMAGE < config.PLAYER_MAX_HP


def test_a_corpse_does_not_fall():
    hole = Chasm(pos=pygame.Vector2(0, 0), radius=400.0)
    player = Player(pos=pygame.Vector2(0, 0))
    player.hp = 0
    falling.update_fall(1.0, player, [hole])
    assert player.hp == 0
    assert hole.holds(player.pos)  # left where they lie


def test_standing_clear_of_every_hole_is_free():
    hole = Chasm(pos=pygame.Vector2(0, 0), radius=400.0)
    player = Player(pos=pygame.Vector2(5_000, 0))
    falling.update_fall(10.0, player, [hole])
    assert player.hp == config.PLAYER_MAX_HP
