import pygame

from game import config
from game.entities.enemy import Golem


def test_moves_toward_target():
    v = Golem(pos=pygame.Vector2(50, 50))
    v.update(1.0, pygame.Vector2(150, 50), (2400, 1600))
    assert v.pos.x == 50 + config.GOLEM_SPEED
    assert v.pos.y == 50


def test_does_not_move_when_on_target():
    v = Golem(pos=pygame.Vector2(50, 50))
    v.update(1.0, pygame.Vector2(50, 50), (2400, 1600))
    assert v.pos == pygame.Vector2(50, 50)


def test_damage_and_death():
    v = Golem(pos=pygame.Vector2(0, 0), hp=10)
    assert v.is_dead is False
    v.damage(10)
    assert v.is_dead is True
