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
    """Keeps the ground around the player wooded.

    Trees come in clumps of a few, each its biome's own timber, never closer
    than ``TREE_GAP`` to anything else on the ground. New clumps grow out of
    sight; trees left far behind are dropped so the count follows the player
    rather than piling up where they have been.
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
        for _ in range(self.max_trees * 3):
            if self._nearby(fragments, player_pos) >= self.max_trees:
                return
            self._grow_clump(fragments, core, rng, world, player_pos, hidden=0.0)

    def update(
        self,
        dt: float,
        fragments: list[Fragment],
        core: Core,
        rng: random.Random,
        world: WorldMap,
        player_pos: pygame.Vector2,
    ) -> int:
        """Forget the far trees and, if there is room, grow a clump. Returns how many grew."""
        if not self.is_due(dt):
            return 0
        fragments[:] = [
            f
            for f in fragments
            if not (f.grove and f.pos.distance_to(player_pos) > config.TREE_FORGET_RADIUS)
        ]
        if self._nearby(fragments, player_pos) >= self.max_trees:
            return 0
        return self._grow_clump(
            fragments, core, rng, world, player_pos, hidden=config.TREE_HIDDEN_RADIUS
        )

    def _nearby(self, fragments: list[Fragment], player_pos: pygame.Vector2) -> int:
        return sum(
            1 for f in fragments if f.grove and f.pos.distance_to(player_pos) <= config.SPAWN_RADIUS
        )

    def _grow_clump(
        self,
        fragments: list[Fragment],
        core: Core,
        rng: random.Random,
        world: WorldMap,
        player_pos: pygame.Vector2,
        hidden: float,
    ) -> int:
        center = None
        for _ in range(SPAWN_ATTEMPTS):
            point = near_player(player_pos, rng, world)
            if point is not None and point.distance_to(player_pos) >= hidden:
                center = point
                break
        if center is None:
            return 0
        size = rng.randint(*config.TREE_CLUMP)
        grown = 0
        for attempt in range(size * 6):
            if grown >= size:
                break
            spot = pygame.Vector2(center)
            if attempt:
                spread = config.TREE_CLUMP_SPREAD
                spot += pygame.Vector2(rng.uniform(-spread, spread), rng.uniform(-spread, spread))
            if not self._room_for(spot, fragments, core, world):
                continue
            biome = world.biome_at(spot)
            timber = biome.timber if biome is not None else WOOD
            fragments.append(Fragment(pos=spot, kind=timber, grove=True))
            grown += 1
        return grown

    @staticmethod
    def _room_for(
        spot: pygame.Vector2, fragments: list[Fragment], core: Core, world: WorldMap
    ) -> bool:
        if not world.contains(spot):
            return False
        if spot.distance_to(core.pos) < core.sync_radius + config.TREE_GAP:
            return False
        return all(f.pos.distance_to(spot) >= config.TREE_GAP for f in fragments)
