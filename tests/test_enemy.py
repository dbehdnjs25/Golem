import pygame

from game import config
from game.entities.enemy import Golem
from game.world.map import WorldMap

WORLD = WorldMap()
CENTRE = WORLD.center


def test_moves_toward_target():
    g = Golem(pos=pygame.Vector2(CENTRE))
    g.update(1.0, CENTRE + pygame.Vector2(100, 0), WORLD)
    assert g.pos.x == CENTRE.x + config.GOLEM_SPEED
    assert g.pos.y == CENTRE.y


def test_does_not_move_when_on_target():
    g = Golem(pos=pygame.Vector2(CENTRE))
    g.update(1.0, pygame.Vector2(CENTRE), WORLD)
    assert g.pos == CENTRE


def test_chasing_past_the_rim_stops_at_the_rim():
    # A golem told to walk off the map is pulled back like anything else.
    g = Golem(pos=CENTRE + pygame.Vector2(WORLD.radius - 10, 0))
    g.update(1.0, CENTRE + pygame.Vector2(WORLD.radius * 2, 0), WORLD)
    assert WORLD.contains(g.pos)


def test_damage_and_death():
    g = Golem(pos=pygame.Vector2(CENTRE), hp=10)
    assert g.is_dead is False
    g.damage(10)
    assert g.is_dead is True
