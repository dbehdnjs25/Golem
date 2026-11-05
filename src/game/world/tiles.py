"""Which tile goes in which cell. Pure arithmetic -- no pygame surface here.

The atlases and their ``tileset.json`` are authored in ``assets/<biome>/tiles32``
by the map editor. This module reads those descriptions once and answers two
questions for the renderer:

- ``biome_for_cell`` -- whose ground is this cell?
- ``pick`` -- which tile of that biome's sheet?

Both are deterministic functions of the cell's coordinates, which matters more
than it sounds. The renderer caches chunks and throws them away when the camera
leaves; a cell that re-rolled would shimmer as you walked, and a chunk rebuilt
after eviction would no longer match the one beside it.

Seams are softened by sampling the biome from a point JITTERED within the cell
rather than from its exact centre. Deep inside a sector the jitter changes
nothing; within a tile or two of a seam it sometimes lands across it, so the two
biomes interlock. A razor-straight edge across a tiled floor reads as a drawing
mistake -- the flat-colour wedges this replaced could afford one because they had
no texture to contradict.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import pygame

from game import config
from game.world.biomes import BIOMES, Biome
from game.world.map import WorldMap

_ASSETS = Path(__file__).resolve().parents[3] / "assets"

# One cell in eight or so carries something other than plain ground. Higher and
# the floor reads as noise; lower and the tiles were not worth cutting.
DECOR_IN = 8

# How far a biome sample may wander from the cell's centre, in pixels. About a
# tile and a half: wide enough to interlock visibly, narrow enough that the
# mixing stays an edge rather than becoming static.
BLEND = config.TILE_SIZE * 1.5

# How far past the rim a cell is still drawn. The tiles overhang and the void
# mask trims a smooth arc over them; dropped instead, the edge shows void
# through the gaps between cells.
OVERHANG = config.TILE_SIZE * 2.0


@dataclass(frozen=True)
class TileSheet:
    """One biome's atlas, as its ``tileset.json`` describes it."""

    key: str
    image: Path
    size: int
    columns: int
    base: int  # the plain ground tile
    decor: tuple[int, ...]  # everything scattered over it

    def rect(self, tile_id: int) -> tuple[int, int, int, int]:
        """Where ``tile_id`` sits in the atlas, as (left, top, w, h)."""
        column, row = tile_id % self.columns, tile_id // self.columns
        return (column * self.size, row * self.size, self.size, self.size)


def _folder(key: str) -> Path:
    """The asset folder for a biome key, which may be spelled either way.

    The editor writes ``burnt-forest`` where the biome table says
    ``burnt_forest``; the rest match.
    """
    for name in (key, key.replace("_", "-")):
        if (_ASSETS / name / "tiles32" / "tileset.json").exists():
            return _ASSETS / name / "tiles32"
    raise FileNotFoundError(f"no tileset for biome {key!r}")


def _read(key: str) -> TileSheet:
    folder = _folder(key)
    described = json.loads((folder / "tileset.json").read_text(encoding="utf-8"))
    rows = described["tiles"]
    plain = min(tile["id"] for tile in rows)
    decor = tuple(
        tile["id"] for tile in rows if tile["id"] != plain and not tile.get("hidden", False)
    )
    return TileSheet(
        key=key,
        image=folder / described["image"],
        size=int(described["tilewidth"]),
        columns=int(described["columns"]),
        base=plain,
        decor=decor,
    )


SHEETS: dict[str, TileSheet] = {biome.key: _read(biome.key) for biome in BIOMES}


def _scramble(x: int, y: int) -> int:
    """A stable hash of a cell. Plain arithmetic on purpose.

    ``hash()`` of anything holding a string is salted per process, so a tile
    chosen with it would differ between runs -- and the one promise this module
    makes is that it does not.
    """
    h = (x * 0x1F1F1F1F) ^ (y * 0x27220A95)
    h &= 0xFFFFFFFF
    h = ((h ^ (h >> 15)) * 0x2545F491) & 0xFFFFFFFF
    return (h ^ (h >> 13)) & 0xFFFFFFFF


def pick(sheet: TileSheet, cell_x: int, cell_y: int) -> int:
    """The tile for one cell of one biome's ground."""
    h = _scramble(cell_x, cell_y)
    if h % DECOR_IN:
        return sheet.base
    return sheet.decor[(h // DECOR_IN) % len(sheet.decor)]


def biome_for_cell(world: WorldMap, cell_x: int, cell_y: int) -> Biome | None:
    """Whose ground this cell is, or None when it is past the rim.

    Sampled from a jittered point so that seams interlock. At the rim the
    jitter is undone rather than allowed to punch holes: the cell falls back to
    its own centre, then to a point pulled inward, and only then gives up.
    """
    half = config.TILE_SIZE / 2
    middle = pygame.Vector2(cell_x * config.TILE_SIZE + half, cell_y * config.TILE_SIZE + half)

    h = _scramble(cell_x, cell_y)
    wander = pygame.Vector2(
        ((h & 0xFF) / 127.5 - 1.0) * BLEND,
        (((h >> 8) & 0xFF) / 127.5 - 1.0) * BLEND,
    )
    found = world.biome_at(middle + wander)
    if found is not None:
        return found

    found = world.biome_at(middle)
    if found is not None:
        return found

    # Hanging over the edge: take the biome of the nearest ground inside.
    inward = middle - world.center
    if inward.length() > world.radius + OVERHANG or inward.length_squared() == 0:
        return None
    return world.biome_at(world.center + inward.normalize() * (world.radius - half))


def visible_cells(offset: pygame.Vector2, view_size: tuple[int, int]) -> tuple[int, int, int, int]:
    """The half-open cell range covering a view, as (x0, y0, x1, y1)."""
    size = config.TILE_SIZE
    x0 = math.floor(offset.x / size)
    y0 = math.floor(offset.y / size)
    x1 = math.ceil((offset.x + view_size[0]) / size)
    y1 = math.ceil((offset.y + view_size[1]) / size)
    return x0, y0, x1, y1
