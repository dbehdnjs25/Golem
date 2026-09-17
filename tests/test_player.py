import pygame
import pytest

from game import config
from game.entities.player import Player
from game.world.map import WorldMap

WORLD = WorldMap()
CENTRE = WORLD.center


def _player(offset=(0, 0)) -> Player:
    return Player(pos=CENTRE + pygame.Vector2(offset))


def test_moves_in_direction():
    p = _player()
    start = pygame.Vector2(p.pos)
    p.update(1.0, pygame.Vector2(1, 0), WORLD)
    assert p.pos.x == start.x + config.PLAYER_SPEED
    assert p.pos.y == start.y


def test_diagonal_is_normalized():
    p = _player()
    start = pygame.Vector2(p.pos)
    p.update(1.0, pygame.Vector2(1, 1), WORLD)
    assert p.pos.distance_to(start) == pytest.approx(config.PLAYER_SPEED)


def test_zero_direction_does_not_move():
    p = _player((300, -200))
    start = pygame.Vector2(p.pos)
    p.update(1.0, pygame.Vector2(0, 0), WORLD)
    assert p.pos == start


def test_clamped_to_the_map_rim():
    # Standing just inside the rim and walking straight out: the body's radius
    # keeps the whole circle on the map, so it stops short of the edge.
    p = Player(pos=CENTRE + pygame.Vector2(WORLD.radius - 1, 0))
    p.update(1.0, pygame.Vector2(1, 0), WORLD)
    assert CENTRE.distance_to(p.pos) == pytest.approx(WORLD.radius - config.PLAYER_RADIUS)
    assert WORLD.contains(p.pos)


def test_the_square_corner_is_off_the_map():
    # The world box's corner is outside the inscribed circle, so a player put
    # there is pulled back onto the rim rather than left standing in the void.
    p = Player(pos=pygame.Vector2(0, 0))
    p.update(1.0, pygame.Vector2(0, 0), WORLD)
    assert WORLD.contains(p.pos)


def test_dodge_grants_iframes_and_cooldown():
    p = _player()
    assert p.invulnerable is False
    p.update(0.0, pygame.Vector2(0, 0), WORLD, dodge_pressed=True)
    assert p.invulnerable is True
    assert p.dodge_cooldown_timer == config.DODGE_COOLDOWN


def test_dodge_iframes_expire():
    p = _player()
    p.update(0.0, pygame.Vector2(0, 0), WORLD, dodge_pressed=True)
    p.update(config.DODGE_IFRAMES, pygame.Vector2(0, 0), WORLD)
    assert p.invulnerable is False


def test_dodge_dashes_faster_when_moving():
    normal = _player()
    normal.update(config.DODGE_DURATION, pygame.Vector2(1, 0), WORLD)
    dashed = _player()
    dashed.update(config.DODGE_DURATION, pygame.Vector2(1, 0), WORLD, dodge_pressed=True)
    assert dashed.pos.x > normal.pos.x


def test_dodge_blocked_during_cooldown():
    p = _player()
    p.update(0.0, pygame.Vector2(0, 0), WORLD, dodge_pressed=True)
    p.update(config.DODGE_IFRAMES, pygame.Vector2(0, 0), WORLD)  # iframes end, still cooling
    assert p.invulnerable is False
    p.update(0.0, pygame.Vector2(0, 0), WORLD, dodge_pressed=True)  # re-press mid-cooldown
    assert p.invulnerable is False  # blocked
