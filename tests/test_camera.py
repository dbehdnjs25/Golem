import pygame
import pytest

from game import config
from game.systems.camera import Camera

VIEW = (960, 540)
WORLD = (2400, 1600)


def _cam():
    return Camera(offset=pygame.Vector2(500, 400), view_size=VIEW, world_size=WORLD)


def test_screen_world_roundtrip():
    cam = _cam()
    p = pygame.Vector2(123, 456)
    assert cam.screen_to_world(cam.world_to_screen(p)) == p


def test_update_centers_on_the_player():
    cam = _cam()
    cam.update(1 / 60, pygame.Vector2(1200, 800))
    assert cam.offset == pygame.Vector2(1200 - 480, 800 - 270)


def test_offset_clamped_to_world():
    # Following a player standing in the top-left corner would put the view's
    # own corner outside the world.
    cam = Camera(offset=pygame.Vector2(0, 0), view_size=VIEW, world_size=WORLD)
    cam.update(1.0, pygame.Vector2(0, 0))
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


# --- zoom -----------------------------------------------------------------


def test_zoom_one_changes_nothing():
    cam = _cam()
    assert cam.zoom == 1.0
    assert cam.field_size == VIEW


def test_zooming_out_shows_more_world():
    # Half the zoom means twice the world across, which is the whole point.
    cam = _cam()
    cam.set_zoom(0.5)
    assert cam.field_size == (VIEW[0] * 2, VIEW[1] * 2)


def test_zooming_in_shows_less():
    cam = _cam()
    cam.set_zoom(2.0)
    assert cam.field_size == (VIEW[0] // 2, VIEW[1] // 2)


def test_the_centre_stays_put_when_the_zoom_changes():
    # Zooming around the middle of the view; otherwise the ground lurches
    # sideways every notch of the wheel.
    cam = _cam()
    middle = cam.screen_to_world(pygame.Vector2(VIEW[0] / 2, VIEW[1] / 2))
    cam.set_zoom(0.5)
    assert cam.screen_to_world(pygame.Vector2(VIEW[0] / 2, VIEW[1] / 2)) == middle


def test_the_mouse_still_lands_where_it_points():
    # Mining and the free camera both read the mouse, and both would aim at
    # the wrong place if the zoom were not undone first.
    cam = _cam()
    cam.set_zoom(0.5)
    corner = cam.screen_to_world(pygame.Vector2(0, 0))
    assert corner == cam.offset
    far = cam.screen_to_world(pygame.Vector2(VIEW[0], VIEW[1]))
    assert far == cam.offset + pygame.Vector2(cam.field_size)


def test_every_step_keeps_tiles_on_whole_pixels():
    # A tile drawn at 23.6 pixels shimmers as you walk. Every allowed step
    # multiplies 32 into a whole number.
    for step in Camera.ZOOM_STEPS:
        assert (config.TILE_SIZE * step) % 1 == 0


def test_the_wheel_walks_the_steps_and_stops_at_the_ends():
    # What the wheel sets is where the camera is GOING. Getting there takes a
    # fraction of a second -- see the journey tests at the foot of this file.
    cam = _cam()
    for _ in range(20):
        cam.zoom_by(-1)
    assert cam.wanted == min(Camera.ZOOM_STEPS)
    for _ in range(20):
        cam.zoom_by(1)
    assert cam.wanted == max(Camera.ZOOM_STEPS)


def test_a_zoomed_out_view_is_still_held_inside_the_world():
    cam = _cam()
    cam.set_zoom(0.5)
    cam.center_on(pygame.Vector2(0, 0))
    assert cam.offset.x >= 0 and cam.offset.y >= 0
    cam.center_on(pygame.Vector2(WORLD))
    assert cam.offset.x + cam.field_size[0] <= WORLD[0]
    assert cam.offset.y + cam.field_size[1] <= WORLD[1]


def test_the_offset_lands_on_whole_pixels():
    # The floor is blitted at chunk - offset, and a blit truncates. With a
    # fractional offset the ground snaps a pixel at a time while everything
    # standing on it moves smoothly, so the two swim against each other.
    cam = _cam()
    cam.center_on(pygame.Vector2(1200.4, 800.7))
    assert cam.offset.x == int(cam.offset.x)
    assert cam.offset.y == int(cam.offset.y)


def test_it_still_follows_a_player_standing_between_pixels():
    # Truncated rather than rounded, to match what a blit does with the same
    # number -- the point is that the ground and the camera agree, not which
    # of the two pixels they agree on.
    cam = _cam()
    cam.update(1 / 60, pygame.Vector2(1200.4, 800.7))
    assert cam.offset == pygame.Vector2(720, 530)


# --- the wheel asks; the camera travels -----------------------------------


def _wheeled(zoom: float = 1.0) -> Camera:
    camera = Camera(
        offset=pygame.Vector2(0, 0),
        view_size=config.SCREEN_SIZE,
        world_size=(100_000, 100_000),
    )
    camera.set_zoom(zoom)
    camera.center_on(pygame.Vector2(50_000, 50_000))
    return camera


def test_a_notch_does_not_move_the_view_on_its_own():
    # It asks. A view that snaps between two sizes reads as the picture
    # breaking rather than as the camera moving.
    camera = _wheeled()
    camera.zoom_by(1)
    assert camera.wanted == 2.0
    assert camera.zoom == 1.0


def test_the_camera_travels_towards_what_was_asked_for():
    camera = _wheeled()
    camera.zoom_by(1)
    camera.update(config.FIXED_DT, pygame.Vector2(50_000, 50_000))
    assert 1.0 < camera.zoom < 2.0


def test_it_arrives_exactly():
    # The steps are sharp and everything between them is not, so the last
    # fraction is snapped away rather than approached forever.
    camera = _wheeled()
    camera.zoom_by(1)
    for _ in range(int(1.0 / config.FIXED_DT)):
        camera.update(config.FIXED_DT, pygame.Vector2(50_000, 50_000))
    assert camera.zoom == 2.0


def test_it_arrives_quickly_enough_to_feel_like_a_wheel():
    # A fifth of a second. Long enough to read as movement, short enough that
    # nobody waits for it.
    assert config.ZOOM_GLIDE <= 0.25
    camera = _wheeled()
    camera.zoom_by(1)
    for _ in range(int(config.ZOOM_GLIDE / config.FIXED_DT) + 2):
        camera.update(config.FIXED_DT, pygame.Vector2(50_000, 50_000))
    assert camera.zoom == 2.0


def test_it_travels_back_down_as_well():
    camera = _wheeled(2.0)
    camera.zoom_by(-1)
    for _ in range(int(1.0 / config.FIXED_DT)):
        camera.update(config.FIXED_DT, pygame.Vector2(50_000, 50_000))
    assert camera.zoom == 1.0


def test_the_wheel_cannot_ask_past_the_ends():
    camera = _wheeled()
    camera.zoom_by(-3)
    assert camera.wanted == 1.0
    camera.zoom_by(9)
    assert camera.wanted == 2.0


def test_turning_back_mid_journey_is_obeyed():
    camera = _wheeled()
    camera.zoom_by(1)
    camera.update(config.FIXED_DT, pygame.Vector2(50_000, 50_000))
    camera.zoom_by(-1)
    assert camera.wanted == 1.0
    for _ in range(int(1.0 / config.FIXED_DT)):
        camera.update(config.FIXED_DT, pygame.Vector2(50_000, 50_000))
    assert camera.zoom == 1.0


def test_the_field_is_whole_pixels_the_whole_way():
    # It is a real surface every frame of the journey, and half a pixel of one
    # does not exist.
    camera = _wheeled()
    camera.zoom_by(1)
    for _ in range(int(0.5 / config.FIXED_DT)):
        camera.update(config.FIXED_DT, pygame.Vector2(50_000, 50_000))
        wide, high = camera.field_size
        assert wide == int(wide) and high == int(high)


def test_the_middle_stays_put_while_it_travels():
    camera = _wheeled()
    camera.center_on(pygame.Vector2(50_000, 50_000))
    camera.zoom_by(1)
    for _ in range(int(0.5 / config.FIXED_DT)):
        camera._glide(config.FIXED_DT)
    assert camera.middle.distance_to(pygame.Vector2(50_000, 50_000)) <= 2


def test_setting_a_zoom_outright_leaves_nothing_to_travel():
    camera = _wheeled()
    camera.set_zoom(2.0)
    assert camera.zoom == camera.wanted == 2.0
