"""Saving the whole game and getting exactly that game back."""

import pickle

import pygame
import pytest

from game import config, saves
from game.inventory.stack import Stack
from game.items.item_kinds import CORE_SHARD, ITEM_KINDS, STONE
from game.scenes.play import PlayScene
from game.world import biomes, dungeon


def _played(seconds: float = 6.0, seed: int = 5) -> PlayScene:
    """A game a little way in: moved, carrying things, the world ticking."""
    scene = PlayScene(seed=seed)
    scene.hotbar.slots[0] = Stack(STONE, 7)
    scene.hotbar.slots[1] = Stack(CORE_SHARD, 2)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
    for _ in range(int(seconds / config.FIXED_DT)):
        scene.update(config.FIXED_DT)
    scene.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_d))
    return scene


def _fingerprint(scene: PlayScene) -> tuple:
    return (
        round(scene.player.pos.x, 6),
        round(scene.player.pos.y, 6),
        round(scene.player.hp, 6),
        round(scene.clock.elapsed, 6),
        scene.clock.day,
        [
            (s.kind.key, s.count) if isinstance(s, Stack) else type(s).__name__
            for s in scene.hotbar.slots
        ],
        sorted((round(f.pos.x, 3), round(f.pos.y, 3), f.kind.key) for f in scene.fragments),
        sorted((round(e.pos.x, 3), round(e.pos.y, 3)) for e in scene.enemies),
        scene.rng.getstate(),
        scene.tree_rng.getstate(),
    )


def test_catalogue_entries_come_back_as_the_very_same_objects():
    loaded = saves.loads(saves.dumps(_played()))
    held = loaded.hotbar.slots[0]
    assert held.kind is STONE
    assert loaded.hotbar.slots[1].kind is CORE_SHARD
    assert all(f.kind is ITEM_KINDS[f.kind.key] for f in loaded.fragments)
    assert [t.biome for t in loaded.temples] == list(biomes.RING_BIOMES)
    assert all(
        a is b for a, b in zip((t.biome for t in loaded.temples), biomes.RING_BIOMES, strict=True)
    )


def test_named_strings_come_back_as_the_constants():
    scene = _played()
    rooms = scene.temples[0].interior().rooms
    loaded = saves.loads(saves.dumps(scene))
    kinds = [room.kind for room in loaded.temples[0].interior().rooms]
    assert kinds == [room.kind for room in rooms]
    assert any(kind is dungeon.BOSS for kind in kinds)


def test_a_loaded_game_carries_on_exactly_like_the_one_saved():
    original = _played()
    loaded = saves.loads(saves.dumps(original))
    assert _fingerprint(loaded) == _fingerprint(original)
    for scene in (original, loaded):
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w))
        for _ in range(int(5 / config.FIXED_DT)):
            scene.update(config.FIXED_DT)
    assert _fingerprint(loaded) == _fingerprint(original)


def test_a_loaded_game_draws():
    loaded = saves.loads(saves.dumps(_played()))
    loaded.draw(pygame.Surface(config.SCREEN_SIZE))


def test_menus_open_at_save_time_are_closed_on_load():
    scene = _played()
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert scene.pause_open
    assert not saves.loads(saves.dumps(scene)).pause_open


def test_slots_on_disk(tmp_path):
    assert saves.info(0, tmp_path) is None
    scene = _played()
    saves.save(scene, 1, tmp_path)
    assert saves.info(0, tmp_path) is None
    assert saves.info(1, tmp_path).day == scene.clock.day
    assert _fingerprint(saves.load(1, tmp_path)) == _fingerprint(scene)
    saves.erase(1, tmp_path)
    assert saves.info(1, tmp_path) is None


def test_saving_again_replaces_the_slot(tmp_path):
    first, second = _played(seed=1), _played(seed=2)
    saves.save(first, 0, tmp_path)
    saves.save(second, 0, tmp_path)
    assert _fingerprint(saves.load(0, tmp_path)) == _fingerprint(second)
    assert not list(tmp_path.glob("*.tmp"))


def test_a_broken_save_raises_rather_than_loading_half_a_game(tmp_path):
    saves.save(_played(), 0, tmp_path)
    (tmp_path / "slot1.save").write_bytes(b"not a save")
    with pytest.raises(pickle.UnpicklingError):
        saves.load(0, tmp_path)


def test_there_are_three_slots(tmp_path):
    assert saves.SLOTS == 3
    with pytest.raises(ValueError):
        saves.info(3, tmp_path)
