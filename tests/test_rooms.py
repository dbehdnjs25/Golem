"""The shape of one room.

Every room in a temple is drawn in the same place -- centred on the temple's
own spot on the map -- and only its contents change. These are the sums that
make that work: where the walls are, where the doors are, and where a body
ends up after walking through one.
"""

import random

import pygame

from game import config
from game.world import rooms
from game.world.dungeon import EAST, NORTH, SOUTH, WEST

AT = pygame.Vector2(3000, 3000)


def test_a_room_is_one_screen():
    box = rooms.rect(AT)
    assert box.size == (config.ROOM_WIDTH, config.ROOM_HEIGHT)
    assert box.center == (AT.x, AT.y)


def test_the_walls_take_room_off_the_inside():
    assert rooms.inner(AT).width < rooms.rect(AT).width
    assert rooms.inner(AT).height < rooms.rect(AT).height


def test_every_wall_has_a_doorway_in_the_middle_of_it():
    box = rooms.rect(AT)
    assert rooms.doorway(AT, NORTH).centerx == box.centerx
    assert rooms.doorway(AT, SOUTH).centerx == box.centerx
    assert rooms.doorway(AT, WEST).centery == box.centery
    assert rooms.doorway(AT, EAST).centery == box.centery


def test_each_doorway_sits_in_its_own_wall():
    box = rooms.rect(AT)
    assert rooms.doorway(AT, NORTH).top == box.top
    assert rooms.doorway(AT, SOUTH).bottom == box.bottom
    assert rooms.doorway(AT, WEST).left == box.left
    assert rooms.doorway(AT, EAST).right == box.right


def test_standing_in_a_doorway_is_noticed():
    for way in (NORTH, SOUTH, EAST, WEST):
        middle = pygame.Vector2(rooms.doorway(AT, way).center)
        assert rooms.in_doorway(middle, AT, way)
        assert not rooms.in_doorway(AT, AT, way)


def test_arriving_puts_you_inside_the_door_you_came_by():
    for way in (NORTH, SOUTH, EAST, WEST):
        spot = rooms.arrival(AT, way)
        assert rooms.inner(AT).collidepoint(spot.x, spot.y)
        assert not rooms.in_doorway(spot, AT, way)


def test_arriving_by_the_north_door_puts_you_at_the_top():
    assert rooms.arrival(AT, NORTH).y < AT.y
    assert rooms.arrival(AT, SOUTH).y > AT.y
    assert rooms.arrival(AT, WEST).x < AT.x
    assert rooms.arrival(AT, EAST).x > AT.x


def test_a_body_is_held_inside_the_room():
    far = pygame.Vector2(AT) + pygame.Vector2(9000, 9000)
    rooms.hold(far, AT, config.PLAYER_RADIUS)
    assert rooms.inner(AT).collidepoint(far.x, far.y)


def test_a_body_is_held_by_its_own_edge_and_not_its_middle():
    far = pygame.Vector2(AT) + pygame.Vector2(9000, 0)
    rooms.hold(far, AT, 40)
    assert far.x == rooms.inner(AT).right - 40


def test_holding_leaves_somebody_already_inside_alone():
    here = pygame.Vector2(AT)
    rooms.hold(here, AT)
    assert here == AT


def test_the_arena_circle_fits_in_the_room():
    assert rooms.arena_radius() * 2 <= min(config.ROOM_WIDTH, config.ROOM_HEIGHT)


def test_golems_are_scattered_inside_the_room():
    spots = rooms.scatter(AT, 4, random.Random(3))
    assert len(spots) == 4
    for spot in spots:
        assert rooms.inner(AT).collidepoint(spot.x, spot.y)


def test_golems_are_not_all_in_one_heap():
    spots = rooms.scatter(AT, 4, random.Random(3))
    apart = [a.distance_to(b) for a in spots for b in spots if a is not b]
    assert min(apart) > config.GOLEM_RADIUS * 2


def test_nobody_to_scatter_is_no_spots():
    assert rooms.scatter(AT, 0, random.Random(1)) == []
