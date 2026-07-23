import pygame

from game.entities.projectile import Projectile


def test_moves_along_velocity():
    p = Projectile(pos=pygame.Vector2(0, 0), vel=pygame.Vector2(100, 0), damage=5)
    p.update(0.5)
    assert p.pos == pygame.Vector2(50, 0)


def test_ttl_decreases_and_expires():
    p = Projectile(pos=pygame.Vector2(0, 0), vel=pygame.Vector2(0, 0), damage=5, ttl=0.3)
    assert p.is_expired is False
    p.update(0.3)
    assert p.is_expired is True
