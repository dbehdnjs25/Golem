"""Putting things down on purpose: the drop key, and walking back to pick up."""

import pygame

from game import config
from game.core import controls as ctl
from game.inventory import grid
from game.inventory.stack import Stack
from game.inventory.storage import Container
from game.items.item_kinds import CORE_SHARD, STONE
from game.items.tools import WeaponTool
from game.scenes.play import PlayScene


def _press(scene: PlayScene, key: int) -> None:
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
    scene.handle_event(pygame.event.Event(pygame.KEYUP, key=key))


def _scene_holding_stone(n: int = 5) -> PlayScene:
    scene = PlayScene()
    scene.hotbar.slots[0] = Stack(STONE, n)
    scene.hotbar.select(0)
    return scene


def _walk_away_and_back(scene: PlayScene, there: pygame.Vector2) -> None:
    scene.player.pos.update(there + pygame.Vector2(config.DROP_PICKUP_RADIUS * 3, 0))
    scene._tick_dropped(config.FIXED_DT)
    scene.player.pos.update(there)
    scene._tick_dropped(config.FIXED_DT)


def test_q_is_the_drop_key_by_default():
    assert ctl.Controls().is_key(pygame.K_q, ctl.DROP)


def test_drop_puts_one_of_the_held_stack_on_the_ground():
    scene = _scene_holding_stone(5)
    _press(scene, pygame.K_q)
    assert scene.hotbar.slots[0] == Stack(STONE, 4)
    assert len(scene.dropped) == 1
    assert scene.dropped[0].item == Stack(STONE, 1)
    assert scene.dropped[0].pos == scene.player.pos


def test_pressing_again_adds_to_the_same_pile():
    scene = _scene_holding_stone(5)
    _press(scene, pygame.K_q)
    _press(scene, pygame.K_q)
    assert len(scene.dropped) == 1
    assert scene.dropped[0].item == Stack(STONE, 2)


def test_with_shift_held_the_whole_stack_goes():
    scene = _scene_holding_stone(5)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LSHIFT))
    _press(scene, pygame.K_q)
    assert scene.hotbar.slots[0] is None
    assert scene.dropped[0].item == Stack(STONE, 5)


def test_a_tool_is_dropped_whole():
    scene = PlayScene()
    scene.hotbar.select(4)
    weapon = scene.hotbar.slots[4]
    assert isinstance(weapon, WeaponTool)
    _press(scene, pygame.K_q)
    assert scene.hotbar.slots[4] is None
    assert scene.dropped[0].item is weapon


def test_an_empty_hand_drops_nothing():
    scene = PlayScene()
    scene.hotbar.select(0)
    scene.hotbar.slots[0] = None
    _press(scene, pygame.K_q)
    assert scene.dropped == []


def test_it_is_not_picked_straight_back_up():
    scene = _scene_holding_stone(5)
    _press(scene, pygame.K_q)
    for _ in range(30):
        scene._tick_dropped(config.FIXED_DT)
    assert len(scene.dropped) == 1
    assert scene.hotbar.slots[0] == Stack(STONE, 4)


def test_walking_away_and_back_picks_it_up():
    scene = _scene_holding_stone(5)
    _press(scene, pygame.K_q)
    _walk_away_and_back(scene, pygame.Vector2(scene.dropped[0].pos))
    assert scene.dropped == []
    assert scene._carried(STONE) == 5  # back in the hand or the base inventory


def test_a_dropped_tool_comes_back_to_an_empty_slot():
    scene = PlayScene()
    scene.hotbar.select(4)
    weapon = scene.hotbar.slots[4]
    _press(scene, pygame.K_q)
    _walk_away_and_back(scene, pygame.Vector2(scene.dropped[0].pos))
    assert weapon in scene.hotbar.slots
    assert scene.dropped == []


def test_what_does_not_fit_stays_on_the_ground():
    scene = _scene_holding_stone(5)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LSHIFT))
    _press(scene, pygame.K_q)
    scene.handle_event(pygame.event.Event(pygame.KEYUP, key=pygame.K_LSHIFT))
    for i in range(len(scene.hotbar.slots)):
        scene.hotbar.slots[i] = WeaponTool()  # every slot full of something else
    scene.backpack = Container.empty(0)  # and nowhere else to put it either
    _walk_away_and_back(scene, pygame.Vector2(scene.dropped[0].pos))
    assert scene.dropped[0].item == Stack(STONE, 5)


def test_with_the_bag_open_the_slot_under_the_cursor_is_dropped():
    scene = PlayScene()
    scene.backpack = Container.empty(4)
    scene.backpack.slots[2] = Stack(STONE, 3)
    _press(scene, pygame.K_i)
    assert scene.grid_open
    scene.grid_cursor = (grid.PACK, 2)
    _press(scene, pygame.K_q)
    assert scene.backpack.slots[2] == Stack(STONE, 2)
    assert scene.dropped[0].item == Stack(STONE, 1)


def test_a_drop_rots_like_a_lost_pile_but_a_core_shard_never_does():
    scene = PlayScene()
    scene.hotbar.slots[0] = Stack(STONE, 1)
    scene.hotbar.slots[1] = Stack(CORE_SHARD, 1)
    for slot in (0, 1):
        scene.hotbar.select(slot)
        _press(scene, pygame.K_q)
        scene.player.pos += pygame.Vector2(config.DROP_PICKUP_RADIUS * 3, 0)
    scene._tick_dropped(config.LOOT_LIFETIME + 1)
    assert [d.item.kind for d in scene.dropped] == [CORE_SHARD]


def test_the_drop_key_can_be_rebound():
    controls = ctl.Controls()
    assert controls.rebind(ctl.DROP, pygame.K_g)
    assert controls.is_key(pygame.K_g, ctl.DROP)
    assert ctl.DROP in ctl.LABELS
