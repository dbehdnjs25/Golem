"""Time-based fragment spawner. Spawn spots avoid the core's sync zone and
existing fragments; the cadence, the retry cap and the random point rule come
from ``spawn_common`` and are shared with the golem spawner."""

from __future__ import annotations

import random
from dataclasses import dataclass

import pygame

from game import config
from game.entities.core import Core
from game.entities.fragment import Fragment
from game.items.item_kinds import WOOD, ItemKind
from game.systems.spawn_common import SPAWN_ATTEMPTS, TimedSpawner, near_player
from game.world.biomes import BIOMES
from game.world.map import WorldMap
from game.world.resources import node_at


@dataclass
class Spawner(TimedSpawner):
    interval: float = config.SPAWN_INTERVAL
    max_fragments: int = config.SPAWN_MAX

    def update(
        self,
        dt: float,
        fragments: list[Fragment],
        core: Core,
        rng: random.Random,
        world: WorldMap,
        player_pos: pygame.Vector2,
    ) -> Fragment | None:
        if not self.is_due(dt):
            return None
        # Only its own. Fixed nodes are terrain the world placed, and counting
        # them would let a busy lava field starve the rest of the map of ore.
        # Grove trees are not its either: they keep their own count.
        if sum(1 for f in fragments if not f.fixed and not f.grove) >= self.max_fragments:
            return None
        spot = self._find_spot(fragments, core, rng, world, player_pos)
        if spot is None:
            return None
        fragment = Fragment(
            pos=spot,
            kind=node_at(world.distance_fraction(spot), rng, world.biome_at(spot)),
        )
        fragments.append(fragment)
        return fragment

    def _find_spot(
        self,
        fragments: list[Fragment],
        core: Core,
        rng: random.Random,
        world: WorldMap,
        player_pos: pygame.Vector2,
    ) -> pygame.Vector2 | None:
        for _ in range(SPAWN_ATTEMPTS):
            point = near_player(player_pos, rng, world)
            if point is None:
                continue
            if core.pos.distance_to(point) < core.sync_radius + config.FRAGMENT_RADIUS:
                continue
            too_close = any(
                f.pos.distance_to(point) < config.FRAGMENT_RADIUS * 2 for f in fragments
            )
            if too_close:
                continue
            return point
        return None


_TIMBER = frozenset(biome.timber for biome in BIOMES)


def is_tree(kind: ItemKind) -> bool:
    """Whether ``kind`` is a standing tree (some biome's timber)."""
    return kind in _TIMBER


@dataclass
class TreeSpawner(TimedSpawner):
    """Keeps the ground around the player evenly wooded.

    Each tree is planted in the best of ``TREE_CANDIDATES`` random spots: the
    one furthest from the trees already standing (best-candidate sampling).
    That spreads them evenly -- no clumps, no bare patches -- without the
    stiffness of a grid. Each is its biome's own timber, never nearer another
    tree than ``TREE_SPACING`` nor anything else than ``TREE_GAP``.

    New trees grow out of sight; trees left far behind are dropped, so the
    count follows the player rather than piling up where they have been.
    """

    interval: float = config.TREE_SPAWN_INTERVAL
    max_trees: int = config.TREE_SPAWN_MAX

    def fill(
        self,
        fragments: list[Fragment],
        core: Core,
        rng: random.Random,
        world: WorldMap,
        player_pos: pygame.Vector2,
    ) -> None:
        """Wood the whole neighbourhood at once, in view or not -- for a new run."""
        near = _Neighbours(fragments)
        planted = self._nearby(fragments, player_pos)
        misses = 0
        # A miss is only a handful of unlucky spots; it takes a run of them in
        # a row to mean the ground is as full as the spacing allows.
        while planted < self.max_trees and misses < 30:
            if self._plant(fragments, near, core, rng, world, player_pos, hidden=0.0):
                planted += 1
                misses = 0
            else:
                misses += 1

    def update(
        self,
        dt: float,
        fragments: list[Fragment],
        core: Core,
        rng: random.Random,
        world: WorldMap,
        player_pos: pygame.Vector2,
    ) -> int:
        """Forget the far trees and, if there is room, plant a few. Returns how many grew."""
        if not self.is_due(dt):
            return 0
        fragments[:] = [
            f
            for f in fragments
            if not (f.grove and f.pos.distance_to(player_pos) > config.TREE_FORGET_RADIUS)
        ]
        room = min(config.TREE_PER_TICK, self.max_trees - self._nearby(fragments, player_pos))
        if room <= 0:
            return 0
        near = _Neighbours(fragments)
        grown = 0
        for _ in range(room):
            hidden = config.TREE_HIDDEN_RADIUS
            if self._plant(fragments, near, core, rng, world, player_pos, hidden):
                grown += 1
        return grown

    def _nearby(self, fragments: list[Fragment], player_pos: pygame.Vector2) -> int:
        return sum(
            1 for f in fragments if f.grove and f.pos.distance_to(player_pos) <= config.SPAWN_RADIUS
        )

    def _plant(
        self,
        fragments: list[Fragment],
        near: _Neighbours,
        core: Core,
        rng: random.Random,
        world: WorldMap,
        player_pos: pygame.Vector2,
        hidden: float,
    ) -> bool:
        """Plant one tree in the roomiest of a few spots. False if none had room."""
        best: pygame.Vector2 | None = None
        best_room = -1.0
        for _ in range(config.TREE_CANDIDATES):
            spot = near_player(player_pos, rng, world)
            if spot is None or spot.distance_to(player_pos) < hidden:
                continue
            if spot.distance_to(core.pos) < core.sync_radius + config.TREE_GAP:
                continue
            room = near.room(spot)
            if room > best_room:
                best, best_room = spot, room
        if best is None or best_room < config.TREE_SPACING:
            return False
        biome = world.biome_at(best)
        timber = biome.timber if biome is not None else WOOD
        tree = Fragment(pos=best, kind=timber, grove=True)
        fragments.append(tree)
        near.add(tree)
        return True


class _Neighbours:
    """What stands near a spot, without measuring against every node on the map.

    Nodes are binned into square cells; a spot only looks at the cells around
    it. ``room`` is the distance to the nearest tree, capped at a few spacings
    (beyond that, a spot is simply roomy) -- or zero when anything that is not
    a tree stands within ``TREE_GAP``.
    """

    REACH = 3  # cells looked at in each direction

    def __init__(self, fragments: list[Fragment]) -> None:
        self.cell = config.TREE_SPACING
        self.bins: dict[tuple[int, int], list[Fragment]] = {}
        for fragment in fragments:
            self.add(fragment)

    def _key(self, point: pygame.Vector2) -> tuple[int, int]:
        return int(point.x // self.cell), int(point.y // self.cell)

    def add(self, fragment: Fragment) -> None:
        self.bins.setdefault(self._key(fragment.pos), []).append(fragment)

    def room(self, spot: pygame.Vector2) -> float:
        cx, cy = self._key(spot)
        nearest = self.cell * self.REACH
        for x in range(cx - self.REACH, cx + self.REACH + 1):
            for y in range(cy - self.REACH, cy + self.REACH + 1):
                for other in self.bins.get((x, y), ()):
                    gap = other.pos.distance_to(spot)
                    if not is_tree(other.kind) and gap < config.TREE_GAP:
                        return 0.0  # standing on a rock or a twig
                    if is_tree(other.kind):
                        nearest = min(nearest, gap)
        return nearest
