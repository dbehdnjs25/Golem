import pygame

from game.systems.physics import clamp_to_circle

CENTRE = pygame.Vector2(100, 100)


def test_a_point_well_inside_is_left_alone():
    p = pygame.Vector2(110, 100)
    clamp_to_circle(p, 5, CENTRE, 50)
    assert p == pygame.Vector2(110, 100)


def test_a_point_outside_is_pulled_to_the_rim():
    p = pygame.Vector2(200, 100)
    clamp_to_circle(p, 5, CENTRE, 50)
    assert p == pygame.Vector2(145, 100)  # 50 - 5 from the centre


def test_the_body_radius_keeps_the_whole_circle_inside():
    p = pygame.Vector2(100, 148)
    clamp_to_circle(p, 10, CENTRE, 50)
    assert CENTRE.distance_to(p) == 40


def test_a_point_exactly_on_the_centre_is_left_alone():
    p = pygame.Vector2(100, 100)
    clamp_to_circle(p, 5, CENTRE, 50)
    assert p == CENTRE  # no direction to push it in, and none is needed


def test_a_body_bigger_than_the_circle_lands_on_the_centre():
    p = pygame.Vector2(200, 100)
    clamp_to_circle(p, 80, CENTRE, 50)
    assert p == CENTRE
