import random

import pygame
import pytest

from game import config
from game.entities.ice_sheet import IceSheet
from game.entities.player import Player
from game.world import biomes, ice
from game.world.map import WorldMap

WORLD = WorldMap(rotation=13.0)
# Start from the middle of the map. At the origin every step is clamped back
# onto the world circle, which quietly swamps anything these tests measure.
HOME = WORLD.center
EAST = pygame.Vector2(1, 0)
NORTH = pygame.Vector2(0, -1)


def _placed(seed: int = 1) -> list[IceSheet]:
    return ice.place(WORLD, random.Random(seed))


def test_ice_only_forms_in_the_snowfield():
    for seed in range(8):
        for sheet in _placed(seed):
            assert WORLD.biome_at(sheet.pos) is biomes.SNOWFIELD


def test_the_same_seed_freezes_the_same_ground():
    assert [(s.pos, s.radius) for s in _placed(4)] == [(s.pos, s.radius) for s in _placed(4)]


def test_different_seeds_move_them():
    assert [s.pos for s in _placed(1)] != [s.pos for s in _placed(2)]


def test_sheets_do_not_overlap():
    for seed in range(8):
        sheets = _placed(seed)
        for i, a in enumerate(sheets):
            for b in sheets[i + 1 :]:
                assert a.pos.distance_to(b.pos) > a.radius + b.radius


def test_there_is_enough_of_it_to_be_a_landscape():
    for seed in range(8):
        assert len(_placed(seed)) >= config.ICE_MIN


def test_standing_on_it_is_standing_on_it():
    sheet = IceSheet(pos=pygame.Vector2(HOME), radius=300.0)
    assert ice.holds(pygame.Vector2(HOME), [sheet])
    assert not ice.holds(HOME + pygame.Vector2(301, 0), [sheet])


# --- sliding --------------------------------------------------------------


def _skating(steps: int, move, slippery: bool = True) -> Player:
    player = Player(pos=pygame.Vector2(HOME))
    for _ in range(steps):
        player.update(config.FIXED_DT, move, WORLD, slippery=slippery)
    return player


def test_setting_off_on_ice_takes_a_moment():
    # Grip is what you push against. With none, the first stride goes nowhere
    # near as far as it would on ground.
    on_ice = _skating(12, EAST)
    on_ground = _skating(12, EAST, slippery=False)
    assert on_ice.pos.x < on_ground.pos.x


def test_letting_go_does_not_stop_you():
    # The whole gimmick. Everywhere else, no input means standing still.
    player = _skating(120, EAST)
    was = pygame.Vector2(player.pos)
    for _ in range(30):
        player.update(config.FIXED_DT, pygame.Vector2(0, 0), WORLD, slippery=True)
    assert player.pos.x > was.x + 10


def test_on_ground_letting_go_stops_you_dead():
    player = _skating(120, EAST, slippery=False)
    was = pygame.Vector2(player.pos)
    player.update(config.FIXED_DT, pygame.Vector2(0, 0), WORLD, slippery=False)
    assert player.pos == was


def test_you_do_eventually_stop():
    # Sliding forever would be a bug, not a hazard.
    player = _skating(120, EAST)
    for _ in range(int(20.0 / config.FIXED_DT)):
        player.update(config.FIXED_DT, pygame.Vector2(0, 0), WORLD, slippery=True)
    assert player.slide.length() < 1.0


def test_turning_on_ice_carries_you_wide():
    # Pushed north after running east, a skater keeps going east for a while.
    player = _skating(120, EAST)
    player.slide.update(config.PLAYER_SPEED, 0)
    for _ in range(12):
        player.update(config.FIXED_DT, NORTH, WORLD, slippery=True)
    assert player.slide.x > 0  # still drifting the old way


def test_turning_on_ground_is_instant():
    player = _skating(120, EAST, slippery=False)
    player.update(config.FIXED_DT, NORTH, WORLD, slippery=False)
    assert player.slide.x == 0


def test_a_dodge_on_ice_carries_further_than_one_on_ground():
    def dashed(slippery: bool) -> float:
        player = Player(pos=pygame.Vector2(HOME))
        player.update(config.FIXED_DT, EAST, WORLD, dodge_pressed=True, slippery=slippery)
        for _ in range(int(1.2 / config.FIXED_DT)):
            player.update(config.FIXED_DT, pygame.Vector2(0, 0), WORLD, slippery=slippery)
        return player.pos.x

    assert dashed(True) > dashed(False)


def test_stepping_off_the_ice_lets_you_plant_your_feet():
    player = _skating(120, EAST)
    player.update(config.FIXED_DT, pygame.Vector2(0, 0), WORLD, slippery=False)
    was = pygame.Vector2(player.pos)
    player.update(config.FIXED_DT, pygame.Vector2(0, 0), WORLD, slippery=False)
    assert player.pos == was


def test_top_speed_is_the_same_on_ice_as_anywhere():
    # It is harder to start and harder to stop, not faster or slower.
    on_ice = _skating(int(6.0 / config.FIXED_DT), EAST)
    on_ground = _skating(int(6.0 / config.FIXED_DT), EAST, slippery=False)
    assert on_ice.slide.length() == pytest.approx(config.PLAYER_SPEED, rel=0.05)
    assert on_ice.pos.x < on_ground.pos.x  # still behind, from the slow start
