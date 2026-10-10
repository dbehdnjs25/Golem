import pygame
import pytest

from game import config
from game.systems.camera import FREE, LOCKED, Camera

VIEW = (960, 540)
WORLD = (2400, 1600)


def _cam(mode=LOCKED):
    return Camera(offset=pygame.Vector2(500, 400), view_size=VIEW, world_size=WORLD, mode=mode)


def test_screen_world_roundtrip():
    cam = _cam()
    p = pygame.Vector2(123, 456)
    assert cam.screen_to_world(cam.world_to_screen(p)) == p


def test_locked_update_centers_on_player():
    cam = _cam(LOCKED)
    cam.update(1 / 60, pygame.Vector2(1200, 800), (0, 0), False)
    assert cam.offset == pygame.Vector2(1200 - 480, 800 - 270)


def test_toggle_from_locked_to_free_keeps_offset():
    cam = _cam(LOCKED)
    before = pygame.Vector2(cam.offset)
    cam.toggle_lock(pygame.Vector2(1200, 800))
    assert cam.mode == FREE
    assert cam.offset == before


def test_toggle_to_locked_snaps_to_player():
    cam = _cam(FREE)
    cam.toggle_lock(pygame.Vector2(1200, 800))
    assert cam.mode == LOCKED
    assert cam.offset == pygame.Vector2(1200 - 480, 800 - 270)


def test_free_pan_at_left_edge_moves_offset_left():
    cam = _cam(FREE)
    cam.update(1.0, pygame.Vector2(1200, 800), (5, 300), False)  # mouse near left edge
    assert cam.offset.x == 500 - config.CAMERA_PAN_SPEED


def test_mining_held_suppresses_pan():
    cam = _cam(FREE)
    cam.update(1.0, pygame.Vector2(1200, 800), (5, 300), True)
    assert cam.offset == pygame.Vector2(500, 400)


def test_offset_clamped_to_world():
    cam = Camera(offset=pygame.Vector2(0, 0), view_size=VIEW, world_size=WORLD, mode=FREE)
    cam.update(1.0, pygame.Vector2(1200, 800), (5, 5), False)  # tries to pan up-left past 0
    assert cam.offset.x == 0
    assert cam.offset.y == 0


def test_a_target_on_screen_needs_no_marker():
    from game.systems.camera import edge_marker

    assert edge_marker(pygame.Vector2(480, 270), (960, 540), 30) is None


def test_a_target_off_screen_is_pinned_to_the_edge():
    from game.systems.camera import edge_marker

    marker = edge_marker(pygame.Vector2(5000, 270), (960, 540), 30)
    assert marker is not None
    assert marker.x == pytest.approx(960 - 30)  # pinned right, inside the margin
    assert marker.y == pytest.approx(270)  # straight out, so no vertical shift


def test_the_marker_keeps_the_direction_it_points():
    # Up and to the right must come back up and to the right, or the arrow
    # sends the player the wrong way.
    from game.systems.camera import edge_marker

    marker = edge_marker(pygame.Vector2(5000, -5000), (960, 540), 30)
    assert marker is not None
    assert marker.x > 480 and marker.y < 270


def test_the_marker_never_leaves_the_view():
    from game.systems.camera import edge_marker

    for point in ((9000, 20), (-9000, 400), (100, -9000), (700, 9000)):
        marker = edge_marker(pygame.Vector2(point), (960, 540), 30)
        assert marker is not None
        # A hair of float slack: the edge is computed, not clamped.
        assert 30 - 1e-6 <= marker.x <= 930 + 1e-6
        assert 30 - 1e-6 <= marker.y <= 510 + 1e-6


def test_a_target_exactly_on_the_centre_needs_no_marker():
    # No direction to point in, and none is needed.
    from game.systems.camera import edge_marker

    assert edge_marker(pygame.Vector2(480, 270), (960, 540), 30) is None
