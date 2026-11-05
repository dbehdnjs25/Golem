"""The pure half of tile drawing: which tile goes in which cell.

No surfaces here. Everything below is arithmetic on a cell's coordinates, so a
seed draws the same ground twice and the answers can be checked without a
window.
"""

import pygame

from game import config
from game.world import biomes, tiles
from game.world.map import WorldMap

WORLD = WorldMap(rotation=37.0)
CENTRE = WORLD.center


def _cell_of(point: pygame.Vector2) -> tuple[int, int]:
    return int(point.x // config.TILE_SIZE), int(point.y // config.TILE_SIZE)


# --- the catalogue --------------------------------------------------------


def test_every_biome_has_a_tileset():
    # A biome with no art would fall back to a flat colour mid-map, which is
    # exactly the seam the tiles exist to remove.
    for biome in biomes.BIOMES:
        sheet = tiles.SHEETS[biome.key]
        assert sheet.image.exists(), biome.key
        assert sheet.size == config.TILE_SIZE


def test_the_plain_ground_is_the_first_tile():
    for sheet in tiles.SHEETS.values():
        assert sheet.base == 0


def test_decoration_leaves_out_the_plain_tile_and_the_hidden_ones():
    for sheet in tiles.SHEETS.values():
        assert sheet.base not in sheet.decor
        assert sheet.decor, sheet.key  # every biome scatters something


def test_a_tile_id_maps_onto_the_atlas():
    sheet = tiles.SHEETS["snowfield"]
    assert sheet.rect(0) == (0, 0, config.TILE_SIZE, config.TILE_SIZE)
    # Second row, first column: the atlas is four wide.
    assert sheet.rect(sheet.columns) == (0, config.TILE_SIZE, config.TILE_SIZE, config.TILE_SIZE)


# --- picking a tile -------------------------------------------------------


def test_the_same_cell_always_gets_the_same_tile():
    # The whole point. A cell that re-rolls every frame shimmers, and a chunk
    # rebuilt after being evicted from the cache would not match its neighbour.
    sheet = tiles.SHEETS["bog"]
    for cell in ((0, 0), (17, -4), (1_000, 2_000), (-9, -9)):
        first = tiles.pick(sheet, *cell)
        assert tiles.pick(sheet, *cell) == first


def test_a_picked_tile_is_one_the_sheet_has():
    sheet = tiles.SHEETS["wasteland"]
    allowed = {sheet.base, *sheet.decor}
    for x in range(40):
        for y in range(40):
            assert tiles.pick(sheet, x, y) in allowed


def test_most_ground_is_plain_but_not_all_of_it():
    # Decoration on every cell reads as noise; on none of them the tiles were
    # not worth cutting.
    sheet = tiles.SHEETS["grassland"]
    picks = [tiles.pick(sheet, x, y) for x in range(60) for y in range(60)]
    plain = picks.count(sheet.base) / len(picks)
    assert 0.6 < plain < 0.95
    assert len(set(picks)) > 3  # and it uses more than one decoration


# --- which biome a cell belongs to ---------------------------------------


def test_deep_inside_a_sector_the_biome_is_that_sector():
    # The jitter that softens the seams must not reach the middle of a biome.
    for index, biome in enumerate(biomes.RING_BIOMES):
        angle = WORLD.rotation + (index + 0.5) * WORLD.sector_degrees
        point = CENTRE + pygame.Vector2(1, 0).rotate(angle) * (
            WORLD.grassland_radius + WORLD.ring_width * 0.5
        )
        assert tiles.biome_for_cell(WORLD, *_cell_of(point)) is biome


def test_the_grassland_middle_is_grassland():
    assert tiles.biome_for_cell(WORLD, *_cell_of(CENTRE)) is biomes.GRASSLAND


def test_a_seam_is_mixed_rather_than_a_straight_line():
    # Two biomes interlock for a tile or two either side. A razor edge across a
    # tiled floor reads as a drawing mistake; a ragged one reads as ground.
    angle = WORLD.rotation + WORLD.sector_degrees  # the first seam
    along = pygame.Vector2(1, 0).rotate(angle)
    across = along.rotate(90)
    reach = WORLD.grassland_radius + WORLD.ring_width * 0.4
    found = set()
    for step in range(-3, 4):
        for slide in range(-60, 60):
            point = CENTRE + along * (reach + slide * config.TILE_SIZE)
            point += across * (step * config.TILE_SIZE)
            found.add(tiles.biome_for_cell(WORLD, *_cell_of(point)))
    assert len(found) == 2  # both neighbours appear in the band, nothing else


def test_the_blend_stays_near_the_seam():
    # Far enough from the seam and the sector is solid, or the mixing would
    # look like static instead of an edge.
    angle = WORLD.rotation + WORLD.sector_degrees
    along = pygame.Vector2(1, 0).rotate(angle)
    across = along.rotate(90)
    reach = WORLD.grassland_radius + WORLD.ring_width * 0.4
    far = config.TILE_SIZE * 4
    for side, biome in ((1, biomes.SNOWFIELD), (-1, biomes.BURNT_FOREST)):
        for slide in range(-30, 30):
            point = CENTRE + along * (reach + slide * config.TILE_SIZE)
            point += across * (side * far)
            assert tiles.biome_for_cell(WORLD, *_cell_of(point)) is biome


# --- the rim --------------------------------------------------------------


def test_a_cell_hanging_over_the_edge_still_draws():
    # Cells whose centre has left the circle are drawn anyway, so the tiles
    # overhang the rim and the void mask can trim a smooth arc over them. Drop
    # them instead and the edge shows void through the gaps.
    out = CENTRE + pygame.Vector2(WORLD.radius + config.TILE_SIZE * 0.5, 0)
    assert tiles.biome_for_cell(WORLD, *_cell_of(out)) is not None


def test_well_past_the_edge_there_is_nothing():
    out = CENTRE + pygame.Vector2(WORLD.radius + config.TILE_SIZE * 6, 0)
    assert tiles.biome_for_cell(WORLD, *_cell_of(out)) is None
