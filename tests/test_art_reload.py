"""Art saved while the game runs shows up without a restart.

Save a tree in Aseprite, the asset library exports its PNG, and within about a
second the running game draws the new one. Also the other way: a picture that
appears (or is deleted) is picked up the same way.
"""

import dataclasses
import os

import pygame

from game import config
from game.items.item_kinds import STONE, WOOD
from game.render import art, resources, trees
from game.render.floor import CHUNK, Floor
from game.scenes.play import PlayScene
from game.world import biomes, tiles
from game.world.map import WorldMap

RED, BLUE = (220, 30, 30), (30, 30, 220)


def _paint(path, colour, size=(8, 8)) -> None:
    """Write a flat picture, and push its clock on so the change is seen."""
    image = pygame.Surface(size)
    image.fill(colour)
    pygame.image.save(image, str(path))
    later = path.stat().st_mtime + 5 if path.exists() else None
    if later is not None:
        os.utime(path, (later, later))


def _middle(surface: pygame.Surface) -> tuple[int, int, int]:
    return tuple(surface.get_at((surface.get_width() // 2, surface.get_height() // 2)))[:3]


def test_a_tree_saved_again_is_redrawn(monkeypatch, tmp_path):
    picture = tmp_path / "tree.png"
    _paint(picture, RED)
    monkeypatch.setitem(trees._FILES, WOOD, picture)
    art.refresh(force=True)
    assert _middle(trees.tree_image(WOOD)) == RED

    _paint(picture, BLUE)
    assert art.refresh()
    assert _middle(trees.tree_image(WOOD)) == BLUE


def test_nothing_changed_means_nothing_reloaded(monkeypatch, tmp_path):
    picture = tmp_path / "tree.png"
    _paint(picture, RED)
    monkeypatch.setitem(trees._FILES, WOOD, picture)
    art.refresh(force=True)
    first = trees.tree_image(WOOD)
    assert not art.refresh()
    assert trees.tree_image(WOOD) is first


def test_a_picture_that_appears_is_picked_up(monkeypatch, tmp_path):
    picture = tmp_path / "tree.png"
    monkeypatch.setitem(trees._FILES, WOOD, picture)
    art.refresh(force=True)
    assert trees.tree_image(WOOD) is None

    _paint(picture, RED)
    assert art.refresh()
    assert _middle(trees.tree_image(WOOD)) == RED


def test_an_item_icon_saved_again_is_redrawn(monkeypatch, tmp_path):
    monkeypatch.setattr(resources, "_ROOT", tmp_path)
    _paint(tmp_path / "stone.png", RED, (32, 32))
    art.refresh(force=True)
    assert _middle(resources.resource_image(STONE)) == RED

    _paint(tmp_path / "stone.png", BLUE, (32, 32))
    assert art.refresh()
    assert _middle(resources.resource_image(STONE)) == BLUE


def test_the_floor_rebuilds_when_its_tiles_are_saved(monkeypatch, tmp_path):
    world = WorldMap(rotation=37.0)
    sheet = tiles.SHEETS["grassland"]
    atlas = tmp_path / "atlas.png"
    width = sheet.columns * sheet.size
    _paint(atlas, RED, (width, width))
    monkeypatch.setitem(tiles.SHEETS, "grassland", dataclasses.replace(sheet, image=atlas))
    cell = int(world.center.x // config.TILE_SIZE), int(world.center.y // config.TILE_SIZE)
    assert tiles.biome_for_cell(world, *cell) is biomes.GRASSLAND
    chunk = cell[0] // CHUNK, cell[1] // CHUNK
    floor = Floor(world)
    art.refresh(force=True)
    assert _middle(floor._chunk(*chunk)) == RED

    _paint(atlas, BLUE, (width, width))
    assert art.refresh()
    assert _middle(floor._chunk(*chunk)) == BLUE


def test_the_running_game_looks_about_once_a_second(monkeypatch):
    looks: list[bool] = []
    monkeypatch.setattr(art, "refresh", lambda force=False: looks.append(True) or False)
    scene = PlayScene()
    surface = pygame.Surface(config.SCREEN_SIZE)
    for _ in range(config.FPS * 2):
        scene.draw(surface)
    assert len(looks) == 2
