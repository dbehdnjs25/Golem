"""Walking must not make the player shiver on screen.

The camera used to follow the player BEFORE the player moved, so it was
always one step behind. The step is 3.33 px; the leftover fraction cycled
through thirds, and since drawing drops the fraction the body landed a
pixel left, right, left -- twenty times a second.
"""

import pygame

from game import config
from game.scenes.play import PlayScene


def _walk(key: int, steps: int = 45) -> list[tuple[int, int]]:
    scene = PlayScene()
    scene.fragments.clear()  # nothing to walk into
    scene.enemies.clear()
    scene.beasts.clear()
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
    seen = []
    for _ in range(steps):
        scene.update(config.FIXED_DT)
        at = scene.camera.world_to_screen(scene.player.pos)
        seen.append((int(at.x), int(at.y)))  # what a draw call lands on
    return seen[5:]  # past setting off


def test_walking_sideways_keeps_the_player_on_one_pixel():
    assert len(set(_walk(pygame.K_d))) == 1


def test_walking_up_keeps_the_player_on_one_pixel():
    assert len(set(_walk(pygame.K_w))) == 1


def test_the_player_stays_in_the_middle_while_walking():
    x, y = _walk(pygame.K_a)[-1]
    width, height = config.SCREEN_SIZE
    assert abs(x - width // 2) <= 1
    assert abs(y - height // 2) <= 1
