"""A temple on the map: a door, and the building remembered behind it.

What used to be here tested a single round room that was redrawn on every
visit -- a door, an altar, a chest and a ring of guards, rolled fresh each
time somebody walked in. A temple is thirteen rooms now (see
``world/dungeon``), and almost all of that moved with them.

What is left is small and worth keeping honest: a temple is a place on the
map with a way in, and the building behind that way in is drawn ONCE.
"""

import pygame

from game import config
from game.entities.temple import Temple
from game.world.biomes import BURNT_FOREST, SNOWFIELD

HOME = pygame.Vector2(5000, 5000)


def _temple(salt: int = 3, biome=BURNT_FOREST) -> Temple:
    return Temple(pos=pygame.Vector2(HOME), biome=biome, salt=salt)


def test_a_temple_is_a_place_with_a_way_in():
    temple = _temple()
    assert temple.contains(HOME)
    assert temple.contains(HOME + pygame.Vector2(config.TEMPLE_RADIUS * 0.5, 0))
    assert not temple.contains(HOME + pygame.Vector2(config.TEMPLE_RADIUS * 2, 0))


def test_nothing_is_built_until_somebody_walks_in():
    # A world with five temples should not pay for five buildings nobody has
    # opened.
    assert not _temple().opened


def test_walking_in_draws_the_building():
    temple = _temple()
    place = temple.interior()
    assert temple.opened
    assert len(place.rooms) >= config.DUNGEON_ROOMS


def test_the_building_is_drawn_once_and_remembered():
    # It used to be redrawn on every visit, which was right when a temple was
    # one room and is wrong now: a player who cleared nine rooms and stepped
    # out for a potion would come back to a place that had never heard of them.
    temple = _temple()
    first = temple.interior()
    first.rooms[0].standing = 7
    second = temple.interior()
    assert second is first
    assert second.rooms[0].standing == 7


def test_two_temples_are_two_different_buildings():
    one = _temple(salt=3).interior()
    two = _temple(salt=9, biome=SNOWFIELD).interior()
    assert [r.kind for r in one.rooms] != [r.kind for r in two.rooms] or [
        r.doors for r in one.rooms
    ] != [r.doors for r in two.rooms]


def test_the_same_temple_is_the_same_building_in_two_runs():
    assert [r.kind for r in _temple(salt=5).interior().rooms] == [
        r.kind for r in _temple(salt=5).interior().rooms
    ]


def test_a_fresh_temple_has_not_been_beaten():
    assert not _temple().boss_killed
    assert not _temple().inside
