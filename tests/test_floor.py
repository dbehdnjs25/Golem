"""The tiled floor keeps drawing when a biome's tile atlas is not on disk.

Art can be deleted from the asset library at any time; the game reads that as
"stop using it", not as a reason to stop.
"""

import dataclasses

from game import config
from game.render.floor import CHUNK, Floor
from game.world import biomes, tiles
from game.world.map import WorldMap

WORLD = WorldMap(rotation=37.0)


def _grassland_chunk() -> tuple[int, int]:
    """The chunk holding the map's middle, which is grassland."""
    cell = int(WORLD.center.x // config.TILE_SIZE), int(WORLD.center.y // config.TILE_SIZE)
    assert tiles.biome_for_cell(WORLD, *cell) is biomes.GRASSLAND
    return cell[0] // CHUNK, cell[1] // CHUNK


def test_a_missing_tile_atlas_paints_the_biome_colour(monkeypatch, tmp_path):
    sheet = tiles.SHEETS["grassland"]
    gone = dataclasses.replace(sheet, image=tmp_path / "deleted.png")
    monkeypatch.setitem(tiles.SHEETS, "grassland", gone)

    chunk = Floor(WORLD)._chunk(*_grassland_chunk())

    middle = chunk.get_at((chunk.get_width() // 2, chunk.get_height() // 2))
    assert middle[:3] == biomes.GRASSLAND.color


def test_with_the_atlas_present_the_tiles_are_used():
    chunk = Floor(WORLD)._chunk(*_grassland_chunk())
    colours = {
        tuple(chunk.get_at((x, y))[:3])
        for x in range(0, chunk.get_width(), 7)
        for y in range(0, chunk.get_height(), 7)
    }
    assert len(colours) > 1  # real tiles have texture; a flat fill would not


def test_the_game_draws_with_every_picture_deleted(monkeypatch):
    # The asset library deletes art at will. Pretend all of it is gone -- the
    # tile atlases, the trees, the item and resource icons -- and the whole
    # screen must still draw, just plainer.
    import pathlib

    import pygame

    from game.render import resources, trees
    from game.scenes.play import PlayScene

    real_is_file = pathlib.Path.is_file

    def no_pictures(path: pathlib.Path) -> bool:
        if "assets" in path.parts and path.suffix.lower() in (".png", ".webp"):
            return False
        return real_is_file(path)

    monkeypatch.setattr(pathlib.Path, "is_file", no_pictures)
    monkeypatch.setattr(trees, "_images", {})
    monkeypatch.setattr(trees, "_missing", set())
    monkeypatch.setattr(trees, "_own_shadow", {})
    monkeypatch.setattr(resources, "_images", {})
    loaded: list[str] = []
    monkeypatch.setattr(pygame.image, "load", lambda path, *a: loaded.append(str(path)))

    scene = PlayScene()
    surface = pygame.Surface(config.SCREEN_SIZE)
    scene.draw(surface)
    scene.grid_open = True
    scene.draw(surface)
    assert loaded == []
