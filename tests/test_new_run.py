"""Every new game rolls fresh trees and fresh temple insides.

The world itself -- where the biomes sit, where each temple stands, the lava --
keeps its fixed seed, so a player learns the land; what is IN it changes.
A scene built with no seed is the fixed one the rest of the tests rely on.
"""

import pygame

import game.__main__ as entry
from game.scenes.play import PlayScene
from game.world.biomes import BIOMES

TIMBERS = {biome.timber for biome in BIOMES}


def _trees(scene: PlayScene) -> list[tuple[float, float]]:
    return sorted((f.pos.x, f.pos.y) for f in scene.fragments if f.kind in TIMBERS)


def _insides(scene: PlayScene) -> list[int]:
    return [temple.salt for temple in scene.temples]


def test_two_new_games_grow_different_trees_and_temples():
    first, second = PlayScene(seed=1), PlayScene(seed=2)
    assert _trees(first) and _trees(second)
    assert _trees(first) != _trees(second)
    assert _insides(first) != _insides(second)
    rooms = [t.interior().rooms for t in first.temples]
    assert rooms != [t.interior().rooms for t in second.temples]


def test_the_land_itself_stays_put():
    first, second = PlayScene(seed=1), PlayScene(seed=2)
    assert first.world.rotation == second.world.rotation
    assert [t.pos for t in first.temples] == [t.pos for t in second.temples]
    assert [t.biome for t in first.temples] == [t.biome for t in second.temples]


def test_the_same_seed_is_the_same_game():
    assert _trees(PlayScene(seed=7)) == _trees(PlayScene(seed=7))
    assert _insides(PlayScene(seed=7)) == _insides(PlayScene(seed=7))


def test_no_seed_is_the_fixed_world_the_tests_use():
    assert _trees(PlayScene()) == _trees(PlayScene())
    assert _insides(PlayScene()) == _insides(PlayScene())


def test_starting_the_game_picks_a_fresh_seed(monkeypatch):
    started: list[PlayScene] = []

    class FakeGame:
        def run(self, scene: PlayScene) -> None:
            started.append(scene)

    monkeypatch.setattr(entry, "Game", FakeGame)
    entry.main()
    entry.main()
    assert len(started) == 2
    assert _trees(started[0]) != _trees(started[1])
    assert isinstance(started[0].player.pos, pygame.Vector2)
