"""A boss temple: a room with a chest by the door and an altar deeper in.

The inside is redrawn every time someone walks in. Three rules keep that
honest:

- only after actually LEAVING, so nobody stands in the doorway rerolling the
  room until the layout suits them
- the entrance goes on the side the player is arriving from, or a wall
  materialises where they are standing
- the dice are the temple's own. Drawing from the world's shared generator
  would shift every later roll, so one visit would change the weather and the
  ore for the rest of the run

What a visit REMEMBERS lives apart from the geometry. An opened chest means the
next layout has no chest at all -- never an opened chest somewhere it has
never been.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from game import config
from game.world.biomes import Biome


@dataclass(frozen=True)
class Layout:
    """One drawing of a temple's inside."""

    door: pygame.Vector2
    altar: pygame.Vector2
    chest: pygame.Vector2 | None  # None once it has been opened
    guards: tuple[pygame.Vector2, ...]  # empty once they are down

    def __eq__(self, other: object) -> bool:
        # Vector2 compares by value, but tuples of them need help; and two
        # drawings are "the same room" only if everything in them matches.
        if not isinstance(other, Layout):
            return NotImplemented
        return (
            self.door == other.door
            and self.altar == other.altar
            and self.chest == other.chest
            and len(self.guards) == len(other.guards)
            and all(a == b for a, b in zip(self.guards, other.guards, strict=True))
        )

    def __hash__(self) -> int:  # pragma: no cover - present for completeness
        return hash((tuple(self.door), tuple(self.altar), len(self.guards)))


@dataclass
class Temple:
    pos: pygame.Vector2
    biome: Biome
    salt: int  # this temple's own seed, drawn once when the world is built
    radius: float = config.TEMPLE_RADIUS

    # What a visit remembers. Kept apart from the geometry on purpose.
    chest_opened: bool = False
    guards_down: bool = False
    boss_killed: bool = False

    visits: int = 0
    inside: bool = False
    layout: Layout | None = None

    # --- coming and going -------------------------------------------------
    def contains(self, point: pygame.Vector2) -> bool:
        return self.pos.distance_to(point) < self.radius

    def enter(self, from_pos: pygame.Vector2) -> None:
        """Walk in, and draw the room. A no-op if already inside."""
        if self.inside:
            return
        self.inside = True
        self.visits += 1
        self.layout = self._draw(from_pos)

    def leave(self) -> None:
        self.inside = False

    # --- drawing the inside ------------------------------------------------
    def _draw(self, from_pos: pygame.Vector2) -> Layout:
        """Lay out a room, with the door facing ``from_pos``.

        Seeded from this temple's salt and the visit number, so the same visit
        of the same temple in the same world draws the same room -- and the
        world's own generator is never touched.
        """
        # Folded into one number: Random takes a scalar seed, and a tuple of
        # (salt, visit) is not one. The stride is wide enough that two
        # temples cannot land on the same stream by visiting enough times.
        rng = random.Random(self.salt * config.TEMPLE_SEED_STRIDE + self.visits)

        approach = from_pos - self.pos
        if approach.length_squared() == 0:
            approach = pygame.Vector2(1, 0)
        door_angle = math.atan2(approach.y, approach.x)
        door = self._at(door_angle, self.radius * 0.95)

        # The altar sits away from the door, the chest between them. Nearer the
        # door than the altar is: tasting the element has to come before being
        # hit with it, and the altar is what has a guard standing over it.
        altar_angle = door_angle + math.pi + rng.uniform(-0.5, 0.5)
        altar = self._at(altar_angle, self.radius * rng.uniform(0.35, 0.6))

        chest = None
        if not self.chest_opened:
            chest_angle = door_angle + rng.uniform(-1.1, 1.1)
            chest = self._at(chest_angle, self.radius * rng.uniform(0.35, 0.62))

        guards: tuple[pygame.Vector2, ...] = ()
        if not self.guards_down:
            guards = self._ring(altar, rng)
        return Layout(door=door, altar=altar, chest=chest, guards=guards)

    def _ring(self, altar: pygame.Vector2, rng: random.Random) -> tuple[pygame.Vector2, ...]:
        """Guards standing around the altar, spread evenly and then jostled."""
        count = rng.randint(config.GUARDS_MIN, config.GUARDS_MAX)
        start = rng.uniform(0.0, math.tau)
        spots: list[pygame.Vector2] = []
        for i in range(count):
            angle = start + i * math.tau / count
            reach = config.GUARD_RING * rng.uniform(0.55, 0.95)
            spot = altar + pygame.Vector2(math.cos(angle) * reach, math.sin(angle) * reach)
            # Pulled back inside if the ring would push one through the wall.
            if self.pos.distance_to(spot) >= self.radius * 0.9:
                spot = self.pos + (spot - self.pos).normalize() * (self.radius * 0.85)
            spots.append(spot)
        return tuple(spots)

    def _at(self, radians: float, reach: float) -> pygame.Vector2:
        return self.pos + pygame.Vector2(math.cos(radians) * reach, math.sin(radians) * reach)
