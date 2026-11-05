"""Drawing the tiled floor.

A naive tile loop is five hundred blits a frame plus five hundred biome
lookups, every frame, for a floor that never changes. So the floor is built in
CHUNKS of 8x8 cells, each one drawn once onto its own surface and then kept.
Walking across the world costs one chunk build at a time; standing still costs
twelve blits.

Which tile goes where is not decided here -- ``world/tiles`` answers that with
pure arithmetic, so a chunk rebuilt after being evicted comes back identical.
This module only loads the atlases and moves pixels.

The rim gets a mask rather than a ragged edge. Tiles overhang the map circle on
purpose and a single filled shape with a hole punched in it trims them back to a
smooth arc; the alternative, dropping cells whose centre has left the circle,
leaves void showing through a staircase of 32-pixel steps.
"""

from __future__ import annotations

import pygame

from game import config
from game.systems.camera import Camera
from game.world import tiles
from game.world.map import WorldMap

CHUNK = 8  # cells per chunk side
CHUNK_PX = CHUNK * config.TILE_SIZE

# Enough for a screenful and the ring around it, several times over. Past this
# the cache is dropped whole: an LRU would spend more thought than a chunk
# costs to rebuild.
CACHE_LIMIT = 48


class Floor:
    """The tiled floor, cached in chunks. One of these per scene.

    Named apart from ``systems.arena.Ground``, which is the hazard floor an
    arena lays when a boss is called -- a different thing entirely.
    """

    def __init__(self, world: WorldMap) -> None:
        self.world = world
        self._atlas: dict[str, pygame.Surface] = {}
        self._chunks: dict[tuple[int, int], pygame.Surface] = {}
        self.builds = 0  # chunks built since the scene opened; for diagnostics

    # --- atlases ---------------------------------------------------------
    def _sheet_surface(self, key: str) -> pygame.Surface:
        """One biome's atlas, loaded on first use and kept."""
        if key not in self._atlas:
            image = pygame.image.load(str(tiles.SHEETS[key].image))
            # convert() needs a display MODE, not just an initialised display
            # subsystem -- pygame.init() gives the second without the first,
            # which is exactly the headless case. Unconverted still blits
            # correctly, only slower.
            if pygame.display.get_surface() is not None:
                image = image.convert()
            self._atlas[key] = image
        return self._atlas[key]

    # --- chunks ----------------------------------------------------------
    def _chunk(self, chunk_x: int, chunk_y: int) -> pygame.Surface:
        key = (chunk_x, chunk_y)
        if key in self._chunks:
            return self._chunks[key]
        if len(self._chunks) >= CACHE_LIMIT:
            self._chunks.clear()

        surface = pygame.Surface((CHUNK_PX, CHUNK_PX))
        surface.fill(config.VOID_COLOR)
        for row in range(CHUNK):
            for column in range(CHUNK):
                cell_x = chunk_x * CHUNK + column
                cell_y = chunk_y * CHUNK + row
                biome = tiles.biome_for_cell(self.world, cell_x, cell_y)
                if biome is None:
                    continue  # past the rim; the void fill stands
                sheet = tiles.SHEETS[biome.key]
                surface.blit(
                    self._sheet_surface(biome.key),
                    (column * config.TILE_SIZE, row * config.TILE_SIZE),
                    sheet.rect(tiles.pick(sheet, cell_x, cell_y)),
                )
        self._chunks[key] = surface
        self.builds += 1
        return surface

    # --- drawing ---------------------------------------------------------
    def draw(self, surface: pygame.Surface, camera: Camera) -> None:
        view_w, view_h = surface.get_size()
        first_x = int(camera.offset.x // CHUNK_PX)
        first_y = int(camera.offset.y // CHUNK_PX)
        last_x = int((camera.offset.x + view_w) // CHUNK_PX)
        last_y = int((camera.offset.y + view_h) // CHUNK_PX)

        for chunk_y in range(first_y, last_y + 1):
            for chunk_x in range(first_x, last_x + 1):
                at = pygame.Vector2(chunk_x * CHUNK_PX, chunk_y * CHUNK_PX) - camera.offset
                surface.blit(self._chunk(chunk_x, chunk_y), at)
        self._trim_rim(surface, camera)

    def _trim_rim(self, surface: pygame.Surface, camera: Camera) -> None:
        """Cut the overhanging tiles back to a smooth map edge.

        Skipped entirely unless the rim actually crosses the view, which for a
        map this size is almost never -- so the usual frame pays one distance
        check for it.
        """
        view_w, view_h = surface.get_size()
        corners = [
            camera.screen_to_world(pygame.Vector2(x, y)) for x in (0, view_w) for y in (0, view_h)
        ]
        reach = [self.world.center.distance_to(corner) for corner in corners]
        if max(reach) <= self.world.radius:
            return  # the whole view is inside the circle

        mask = pygame.Surface((view_w, view_h), pygame.SRCALPHA)
        mask.fill(config.VOID_COLOR)
        # Drawing writes rather than blends, so a zero-alpha circle punches a
        # hole. The radius is enormous; SDL clips it to the surface.
        pygame.draw.circle(
            mask,
            (0, 0, 0, 0),
            camera.world_to_screen(self.world.center),
            self.world.radius,
        )
        surface.blit(mask, (0, 0))
