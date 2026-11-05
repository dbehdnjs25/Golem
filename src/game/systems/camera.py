"""World<->screen transform with two modes: LOCKED follows the player;
FREE pans when the mouse hits a screen edge (League-of-Legends style, toggled
with Y). Pure math given its inputs, so it is fully testable headlessly.

Zoom is a scale between the FIELD -- the stretch of world being drawn -- and the
screen it ends up on. ``view_size`` stays the screen; ``field_size`` is what the
zoom makes of it, and that is the surface the world is drawn onto before being
scaled down to the window. So ``world_to_screen`` answers in field pixels and
``screen_to_world`` takes real screen pixels, undoing the zoom itself: mining and
the free camera both read the mouse, and both would aim at the wrong spot if
that division lived at the call sites.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config

FREE = "free"
LOCKED = "locked"


@dataclass
class Camera:
    offset: pygame.Vector2  # world coord shown at the view's top-left
    view_size: tuple[int, int]
    world_size: tuple[int, int]
    mode: str = LOCKED
    zoom: float = 1.0

    # The zoom only ever REDUCES how much world is on screen. 1.0 draws the
    # field at the window's own size and hands it over untouched; 2.0 draws
    # half of that and doubles it, which is exact.
    #
    # There is deliberately nothing below 1.0. Showing more means drawing a
    # field bigger than the window and squeezing it down, and a squeeze throws
    # pixels away -- different ones from frame to frame as the camera moves,
    # which is what makes a wall of tiles crawl while you walk. Starting the
    # window large is how you get a wide view instead.
    ZOOM_STEPS = (1.0, 2.0)

    @property
    def field_size(self) -> tuple[int, int]:
        """The stretch of world being drawn, in pixels, before scaling."""
        return (round(self.view_size[0] / self.zoom), round(self.view_size[1] / self.zoom))

    def world_to_screen(self, point: pygame.Vector2) -> pygame.Vector2:
        """Where ``point`` falls on the FIELD -- what the world is drawn onto."""
        return pygame.Vector2(point) - self.offset

    def world_to_view(self, point: pygame.Vector2) -> pygame.Vector2:
        """Where ``point`` falls on the WINDOW, after the field is scaled.

        Anything drawn over the scaled field rather than into it needs this:
        the compass pins its markers to the window's edge, and comparing a
        field coordinate against the window's size put the marker in a corner
        while the thing it pointed at sat in the middle of the screen.
        """
        return self.world_to_screen(point) * self.zoom

    def screen_to_world(self, point: pygame.Vector2) -> pygame.Vector2:
        return pygame.Vector2(point) / self.zoom + self.offset

    def set_zoom(self, zoom: float) -> None:
        """Change the zoom, keeping whatever is in the middle of the view there.

        Without that the ground lurches sideways on every notch of the wheel.
        """
        middle = self.offset + pygame.Vector2(self.field_size) / 2
        self.zoom = zoom
        self.center_on(middle)

    def zoom_by(self, notches: int) -> None:
        """Walk ``notches`` along the steps, stopping at either end."""
        steps = self.ZOOM_STEPS
        where = min(range(len(steps)), key=lambda i: abs(steps[i] - self.zoom))
        self.set_zoom(steps[max(0, min(len(steps) - 1, where + notches))])

    def _clamp(self) -> None:
        field_w, field_h = self.field_size
        world_w, world_h = self.world_size
        self.offset.x = max(0.0, min(world_w - field_w, self.offset.x))
        self.offset.y = max(0.0, min(world_h - field_h, self.offset.y))
        # Whole pixels. The floor is blitted at chunk - offset and a blit
        # truncates, so a fractional offset snaps the ground a pixel at a time
        # while everything standing on it moves smoothly -- the two then swim
        # against each other. The player walks 3.33 pixels a step, so this is
        # never not fractional otherwise.
        self.offset.x = float(int(self.offset.x))
        self.offset.y = float(int(self.offset.y))

    def center_on(self, point: pygame.Vector2) -> None:
        field_w, field_h = self.field_size
        self.offset = pygame.Vector2(point) - pygame.Vector2(field_w / 2, field_h / 2)
        self._clamp()

    def toggle_lock(self, player_pos: pygame.Vector2) -> None:
        if self.mode == LOCKED:
            self.mode = FREE
        else:
            self.mode = LOCKED
            self.center_on(player_pos)

    def update(
        self,
        dt: float,
        player_pos: pygame.Vector2,
        mouse_screen: tuple[int, int] | pygame.Vector2,
        mining_held: bool,
    ) -> None:
        if self.mode == LOCKED:
            self.center_on(player_pos)
            return
        if mining_held:
            return  # sharing the mouse with mining: don't pan while channelling
        view_w, view_h = self.view_size
        margin = config.CAMERA_EDGE_MARGIN
        mouse_x, mouse_y = mouse_screen[0], mouse_screen[1]
        direction = pygame.Vector2(0, 0)
        if mouse_x < margin:
            direction.x = -1
        elif mouse_x > view_w - margin:
            direction.x = 1
        if mouse_y < margin:
            direction.y = -1
        elif mouse_y > view_h - margin:
            direction.y = 1
        if direction.length_squared() > 0:
            self.offset += direction * config.CAMERA_PAN_SPEED * dt
            self._clamp()


def edge_marker(
    target: pygame.Vector2, view_size: tuple[int, int], margin: float
) -> pygame.Vector2 | None:
    """Where to pin a pointer to something off screen, or None if it is on it.

    The world is far larger than a window -- the grassland alone is seventy-five
    screens across -- so anything out of sight may as well not exist unless the
    edge of the view says which way it lies.

    The pin sits where the ray from the view's centre to the target crosses a
    rectangle inset by ``margin``, which keeps the direction honest: up and to
    the right comes back up and to the right.
    """
    view_w, view_h = view_size
    half_w, half_h = view_w / 2 - margin, view_h / 2 - margin
    center = pygame.Vector2(view_w / 2, view_h / 2)
    offset = target - center
    if abs(offset.x) <= half_w and abs(offset.y) <= half_h:
        return None
    scales = [half / abs(axis) for axis, half in ((offset.x, half_w), (offset.y, half_h)) if axis]
    if not scales:
        return None
    return center + offset * min(scales)
