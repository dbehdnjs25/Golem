"""World<->screen transform. It follows the player, and that is all.

There used to be a second mode that panned when the mouse touched a screen
edge. It went with the key that turned it on: reachable no other way, every
line of it was unreachable the moment that binding left.

Pure math given its inputs, so it is fully testable headlessly.

Zoom is a scale between the FIELD -- the stretch of world being drawn -- and the
screen it ends up on. ``view_size`` stays the screen; ``field_size`` is what the
zoom makes of it, and that is the surface the world is drawn onto before being
scaled down to the window. So ``world_to_screen`` answers in field pixels and
``screen_to_world`` takes real screen pixels, undoing the zoom itself: mining
reads the mouse, and it would aim at the wrong spot if that division lived at
the call site.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config


@dataclass
class Camera:
    offset: pygame.Vector2  # world coord shown at the view's top-left
    view_size: tuple[int, int]
    world_size: tuple[int, int]
    # What the world is being drawn at right now, and what the wheel last
    # asked for. They are the same number except for the tenth of a second
    # after a notch, and that tenth of a second is the whole point: a view
    # that snaps between two sizes reads as the picture breaking rather than
    # as the camera moving.
    zoom: float = 1.0
    wanted: float = 1.0
    # The journey itself: where it set off from, how long it has been going,
    # and the world point to keep in the middle while it does. The anchor is
    # held rather than re-read each frame because ``center_on`` lands on whole
    # pixels, and half a pixel of rounding per frame adds up to the ground
    # sliding away under a wheel that was only supposed to zoom.
    _from: float = 1.0
    _travelled: float = 0.0
    _anchor: pygame.Vector2 | None = None

    # The zoom only ever REDUCES how much world is on screen. 1.0 draws the
    # field at the window's own size and hands it over untouched; 2.0 draws
    # half of that and doubles it. Those two are exact: every source pixel
    # becomes exactly one, or exactly four.
    #
    # The quarters between them are not, and that is a choice rather than an
    # oversight. At 1.25 a source pixel becomes one dot or two depending on
    # where it falls, so edges thicken unevenly and a tiled wall shimmers
    # slightly as the camera moves over it. What they buy is a view that can
    # be set to what the moment wants instead of being thrown between two
    # sizes, and the ends are still there for anyone who wants them crisp.
    #
    # There is deliberately nothing below 1.0. Showing more means drawing a
    # field bigger than the window and squeezing it down, and a squeeze throws
    # pixels away rather than doubling them -- different ones from frame to
    # frame, which is a crawl rather than a shimmer. Starting the window large
    # is how you get a wide view instead.
    ZOOM_STEPS = (1.0, 1.25, 1.5, 1.75, 2.0)

    @property
    def field_size(self) -> tuple[int, int]:
        """The stretch of world being drawn, in pixels, before scaling."""
        return (round(self.view_size[0] / self.zoom), round(self.view_size[1] / self.zoom))

    def world_to_screen(self, point: pygame.Vector2) -> pygame.Vector2:
        """Where ``point`` falls on the FIELD -- what the world is drawn onto.

        Snapped to whole pixels HERE, which is the only place it can be done
        once for everything. Half a pixel does not exist on a screen, so
        somebody rounds either way: pygame truncates whatever it is handed,
        and it truncates each thing on its own. With the ground blitted from
        one sum and a body drawn from another, the two rounded apart and
        ground and body swam against each other a pixel at a time -- worst
        going diagonally, where both axes did it at once.

        Rounded from the SAME fractional offset, everything shifts together.
        And because the camera is centred on the player, the player's own
        fraction cancels out: they sit on exactly the same pixel every frame
        however they walk.
        """
        return pygame.Vector2(round(point.x - self.offset.x), round(point.y - self.offset.y))

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

    @property
    def middle(self) -> pygame.Vector2:
        """The world point in the middle of the view."""
        return self.offset + pygame.Vector2(self.field_size) / 2

    def set_zoom(self, zoom: float) -> None:
        """Put the camera at a zoom immediately, with nothing to travel.

        Keeps whatever is in the middle of the view there; without that the
        ground lurches sideways. Used where there is no clock to glide on --
        setting up a scene, and tests.
        """
        middle = self.middle
        self.zoom = self.wanted = self._from = zoom
        self._anchor = None
        self._travelled = 0.0
        self.center_on(middle)

    def zoom_by(self, notches: int) -> None:
        """Ask for a step ``notches`` along, stopping at either end.

        Only ASKS. The camera travels there over the next few frames, which is
        what a wheel notch is supposed to feel like.
        """
        steps = self.ZOOM_STEPS
        where = min(range(len(steps)), key=lambda i: abs(steps[i] - self.wanted))
        asked = steps[max(0, min(len(steps) - 1, where + notches))]
        if asked == self.wanted:
            return  # already going there, or already there; do not restart it
        self.wanted = asked
        self._from = self.zoom
        self._travelled = 0.0
        self._anchor = self.middle

    def _glide(self, dt: float) -> None:
        """Close most of the distance to what the wheel asked for.

        A journey of a known length, eased at both ends: it leaves and
        arrives the way a hand would move a lens rather than starting and
        stopping dead. Measured against ``dt``, so a slow frame travels as far
        as the time it took rather than as far as one tick.

        It LANDS. The steps are exact on purpose -- 1.0 hands the field over
        untouched and 2.0 doubles it, and both are sharp -- so the last
        fraction is snapped away rather than approached forever. Everything in
        between is only ever passed through.
        """
        if self._anchor is None:
            return
        self._travelled += dt
        share = min(1.0, self._travelled / config.ZOOM_GLIDE)
        # Slow at both ends: it leaves and arrives the way a hand would move
        # a lens, rather than starting and stopping dead.
        eased = share * share * (3 - 2 * share)
        self.zoom = self._from + (self.wanted - self._from) * eased
        anchor = self._anchor
        if share >= 1.0:
            self.zoom = self.wanted
            self._anchor = None
        self.center_on(anchor)

    def _clamp(self) -> None:
        field_w, field_h = self.field_size
        world_w, world_h = self.world_size
        self.offset.x = max(0.0, min(world_w - field_w, self.offset.x))
        self.offset.y = max(0.0, min(world_h - field_h, self.offset.y))
        # Left fractional on purpose. It used to be snapped to whole pixels
        # here, which steadied the ground and left everything standing on it
        # jittering against it; the snapping belongs at the point of drawing,
        # where one rule can cover the ground and the bodies alike. See
        # ``world_to_screen``.

    def center_on(self, point: pygame.Vector2) -> None:
        field_w, field_h = self.field_size
        self.offset = pygame.Vector2(point) - pygame.Vector2(field_w / 2, field_h / 2)
        self._clamp()

    def update(self, dt: float, player_pos: pygame.Vector2) -> None:
        """Travel whatever the wheel asked for, then follow the player."""
        self._glide(dt)
        self.center_on(player_pos)


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
