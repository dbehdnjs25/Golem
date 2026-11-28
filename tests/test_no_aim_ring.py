"""Walking up to a tree or a rock draws nothing extra around it.

A ring used to mark every node in reach -- white when the tool could take it,
red when not -- and with the ground evenly wooded it lit up around the player
wherever they walked.
"""

import pygame

from game import config
from game.entities.fragment import Fragment
from game.items.item_kinds import STONE, WOOD
from game.scenes.play import PlayScene


def _around_node(kind, facing: pygame.Vector2) -> pygame.Surface:
    scene = PlayScene()
    scene.fragments.clear()
    scene.enemies.clear()
    scene.beasts.clear()
    node = Fragment(pos=scene.player.pos + pygame.Vector2(60, 0), kind=kind)
    scene.fragments.append(node)
    scene.facing = facing
    surface = pygame.Surface(config.SCREEN_SIZE)
    scene.draw(surface)
    at = scene.camera.world_to_screen(node.pos)
    box = pygame.Rect(0, 0, 40, 40)
    box.center = (int(at.x), int(at.y))
    return surface.subsurface(box).copy()


def _same(a: pygame.Surface, b: pygame.Surface) -> bool:
    return all(
        a.get_at((x, y)) == b.get_at((x, y))
        for x in range(a.get_width())
        for y in range(a.get_height())
    )


def test_a_rock_in_reach_gets_no_ring():
    toward = _around_node(STONE, pygame.Vector2(1, 0))
    away = _around_node(STONE, pygame.Vector2(-1, 0))
    assert _same(toward, away)


def test_a_tree_in_reach_gets_no_ring():
    toward = _around_node(WOOD, pygame.Vector2(1, 0))
    away = _around_node(WOOD, pygame.Vector2(-1, 0))
    assert _same(toward, away)
