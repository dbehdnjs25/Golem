import pygame

from game import config
from game.systems import aim

ORIGIN = pygame.Vector2(0, 0)
RIGHT = pygame.Vector2(1, 0)


def test_walking_sets_the_facing():
    assert aim.face(pygame.Vector2(0, -1), RIGHT) == pygame.Vector2(0, -1)


def test_a_diagonal_facing_is_unit_length():
    assert abs(aim.face(pygame.Vector2(1, 1), RIGHT).length() - 1) < 1e-9


def test_standing_still_keeps_the_last_facing():
    assert aim.face(pygame.Vector2(0, 0), RIGHT) == RIGHT


def test_straight_ahead_is_in_the_fan():
    assert aim.in_fan(ORIGIN, RIGHT, pygame.Vector2(50, 0), reach=100)


def test_behind_is_not():
    assert not aim.in_fan(ORIGIN, RIGHT, pygame.Vector2(-50, 0), reach=100)


def test_the_fan_edge_is_the_half_angle():
    import math

    inside = math.radians(config.AIM_HALF_ANGLE - 5)
    outside = math.radians(config.AIM_HALF_ANGLE + 5)
    at = lambda a: pygame.Vector2(math.cos(a), math.sin(a)) * 50  # noqa: E731
    assert aim.in_fan(ORIGIN, RIGHT, at(inside), reach=100)
    assert not aim.in_fan(ORIGIN, RIGHT, at(outside), reach=100)


def test_beyond_reach_is_not():
    assert not aim.in_fan(ORIGIN, RIGHT, pygame.Vector2(150, 0), reach=100)


def test_a_body_overlapping_the_player_counts_from_any_side():
    assert aim.in_fan(ORIGIN, RIGHT, pygame.Vector2(-5, 0), reach=100, pad=10)


def test_in_front_lists_nearest_first():
    class Dot:
        def __init__(self, x: float) -> None:
            self.pos = pygame.Vector2(x, 0)

    far, near, behind = Dot(80), Dot(20), Dot(-20)
    assert aim.in_front(ORIGIN, RIGHT, [far, behind, near], reach=100) == [near, far]


def test_ahead_is_in_front():
    assert aim.ahead(ORIGIN, RIGHT, 30) == pygame.Vector2(30, 0)
