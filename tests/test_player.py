import pygame
import pytest

from game import config
from game.entities.player import Player


def test_moves_in_direction():
    p = Player(pos=pygame.Vector2(100, 100))
    p.update(1.0, pygame.Vector2(1, 0), (2400, 1600))
    assert p.pos.x == 100 + config.PLAYER_SPEED
    assert p.pos.y == 100


def test_diagonal_is_normalized():
    p = Player(pos=pygame.Vector2(500, 500))
    p.update(1.0, pygame.Vector2(1, 1), (2400, 1600))
    travelled = p.pos.distance_to(pygame.Vector2(500, 500))
    assert travelled == pytest.approx(config.PLAYER_SPEED)


def test_zero_direction_does_not_move():
    p = Player(pos=pygame.Vector2(300, 300))
    p.update(1.0, pygame.Vector2(0, 0), (2400, 1600))
    assert p.pos == pygame.Vector2(300, 300)


def test_clamped_to_bounds():
    p = Player(pos=pygame.Vector2(5, 5))
    p.update(1.0, pygame.Vector2(-1, -1), (2400, 1600))
    assert p.pos.x == config.PLAYER_RADIUS
    assert p.pos.y == config.PLAYER_RADIUS


def test_dodge_grants_iframes_and_cooldown():
    p = Player(pos=pygame.Vector2(500, 500))
    assert p.invulnerable is False
    p.update(0.0, pygame.Vector2(0, 0), (2400, 1600), dodge_pressed=True)
    assert p.invulnerable is True
    assert p.dodge_cooldown_timer == config.DODGE_COOLDOWN


def test_dodge_iframes_expire():
    p = Player(pos=pygame.Vector2(500, 500))
    p.update(0.0, pygame.Vector2(0, 0), (2400, 1600), dodge_pressed=True)
    p.update(config.DODGE_IFRAMES, pygame.Vector2(0, 0), (2400, 1600))
    assert p.invulnerable is False


def test_dodge_dashes_faster_when_moving():
    normal = Player(pos=pygame.Vector2(500, 500))
    normal.update(config.DODGE_DURATION, pygame.Vector2(1, 0), (2400, 1600))
    dashed = Player(pos=pygame.Vector2(500, 500))
    dashed.update(config.DODGE_DURATION, pygame.Vector2(1, 0), (2400, 1600), dodge_pressed=True)
    assert dashed.pos.x > normal.pos.x


def test_dodge_blocked_during_cooldown():
    p = Player(pos=pygame.Vector2(500, 500))
    p.update(0.0, pygame.Vector2(0, 0), (2400, 1600), dodge_pressed=True)
    p.update(config.DODGE_IFRAMES, pygame.Vector2(0, 0), (2400, 1600))  # iframes end, still cooling
    assert p.invulnerable is False
    p.update(0.0, pygame.Vector2(0, 0), (2400, 1600), dodge_pressed=True)  # re-press mid-cooldown
    assert p.invulnerable is False  # blocked
