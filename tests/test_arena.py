"""The door that shuts when a boss wakes.

This used to lay a biome's terrain across the floor as well -- lava in the
burnt forest, sheets in the snowfield. The boss's room is left bare now: the
fifteen attribute tricks put plenty on the floor between them, and a room
that starts full leaves the player nothing to read when the fight adds to it.

So one thing remains, and it is the thing that matters. Fought with a way
out, phase two is just something to retreat from.
"""

import pygame

from game.systems import arena

HOME = pygame.Vector2(2000, 2000)
REACH = 400.0


def test_a_room_starts_open():
    assert not arena.Ground().sealed


def test_waking_something_shuts_the_door():
    ground = arena.Ground()
    assert arena.seal(ground)
    assert ground.sealed


def test_a_shut_door_cannot_be_shut_twice():
    ground = arena.Ground()
    arena.seal(ground)
    assert not arena.seal(ground)


def test_the_door_opens_when_it_is_over():
    ground = arena.Ground()
    arena.seal(ground)
    arena.release(ground)
    assert not ground.sealed


def test_an_open_room_holds_nobody():
    ground = arena.Ground()
    away = pygame.Vector2(HOME) + pygame.Vector2(9000, 0)
    arena.hold(away, HOME, REACH, ground)
    assert away.x == HOME.x + 9000


def test_a_shut_room_holds_you_at_the_wall():
    ground = arena.Ground()
    arena.seal(ground)
    away = pygame.Vector2(HOME) + pygame.Vector2(9000, 0)
    arena.hold(away, HOME, REACH, ground)
    assert abs(HOME.distance_to(away) - REACH) < 0.01


def test_somebody_already_inside_is_left_alone():
    ground = arena.Ground()
    arena.seal(ground)
    here = pygame.Vector2(HOME) + pygame.Vector2(10, 0)
    arena.hold(here, HOME, REACH, ground)
    assert here == HOME + pygame.Vector2(10, 0)


def test_standing_on_the_very_middle_is_not_a_divide_by_nothing():
    ground = arena.Ground()
    arena.seal(ground)
    here = pygame.Vector2(HOME)
    arena.hold(here, HOME, REACH, ground)
    assert here == HOME
