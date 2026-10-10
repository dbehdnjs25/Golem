"""World<->screen transform with two modes: LOCKED follows the player;
FREE pans when the mouse hits a screen edge (League-of-Legends style, toggled
with Y). Pure math given its inputs, so it is fully testable headlessly."""

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

    def world_to_screen(self, point: pygame.Vector2) -> pygame.Vector2:
        return pygame.Vector2(point) - self.offset

    def screen_to_world(self, point: pygame.Vector2) -> pygame.Vector2:
        return pygame.Vector2(point) + self.offset

    def _clamp(self) -> None:
        view_w, view_h = self.view_size
        world_w, world_h = self.world_size
        self.offset.x = max(0.0, min(world_w - view_w, self.offset.x))
        self.offset.y = max(0.0, min(world_h - view_h, self.offset.y))

    def center_on(self, point: pygame.Vector2) -> None:
        view_w, view_h = self.view_size
        self.offset = pygame.Vector2(point) - pygame.Vector2(view_w / 2, view_h / 2)
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
