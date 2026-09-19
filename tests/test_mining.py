import pygame

from game import config
from game.entities.fragment import Fragment
from game.inventory.hotbar import Hotbar
from game.inventory.storage import Container
from game.items.item_kinds import CORE_SHARD
from game.items.tools import MiningTool
from game.systems import mining

PLAYER = pygame.Vector2(1000, 1000)


def _backpack() -> Container:
    return Container.empty(config.BACKPACK_SLOTS)


def test_idle_when_not_held() -> None:
    frags = [Fragment(pos=pygame.Vector2(1010, 1000))]
    status, _ = mining.update_mining(
        1 / 60,
        active_tool=MiningTool(),
        held=False,
        aim_world=pygame.Vector2(1010, 1000),
        player_pos=PLAYER,
        fragments=frags,
        backpack=_backpack(),
        hotbar=Hotbar.create(),
    )
    assert status == mining.IDLE


def test_channelling_reduces_hp() -> None:
    frag = Fragment(pos=pygame.Vector2(1010, 1000))
    frags = [frag]
    status, _ = mining.update_mining(
        1.0,
        active_tool=MiningTool(),
        held=True,
        aim_world=pygame.Vector2(1010, 1000),
        player_pos=PLAYER,
        fragments=frags,
        backpack=_backpack(),
        hotbar=Hotbar.create(),
    )
    assert status == mining.MINING
    assert frag.hp == config.FRAGMENT_HP - config.MINING_DPS


def test_depletion_collects_into_backpack() -> None:
    frag = Fragment(pos=pygame.Vector2(1010, 1000), hp=config.MINING_DPS)  # one tick to deplete
    frags = [frag]
    bp = _backpack()
    status, _ = mining.update_mining(
        1.0,
        active_tool=MiningTool(),
        held=True,
        aim_world=pygame.Vector2(1010, 1000),
        player_pos=PLAYER,
        fragments=frags,
        backpack=bp,
        hotbar=Hotbar.create(),
    )
    assert status == mining.COLLECTED
    assert frags == []
    assert bp.count(CORE_SHARD) == 1


def test_out_of_range_does_no_damage() -> None:
    frag = Fragment(pos=pygame.Vector2(2000, 1000))  # far from player
    frags = [frag]
    status, _ = mining.update_mining(
        1.0,
        active_tool=MiningTool(),
        held=True,
        aim_world=pygame.Vector2(2000, 1000),
        player_pos=PLAYER,
        fragments=frags,
        backpack=_backpack(),
        hotbar=Hotbar.create(),
    )
    assert status == mining.OUT_OF_RANGE
    assert frag.hp == config.FRAGMENT_HP


def test_full_backpack_blocks_and_preserves_fragment() -> None:
    frag = Fragment(pos=pygame.Vector2(1010, 1000))
    frags = [frag]
    bp = Container.empty(1)  # one slot
    bp.add(CORE_SHARD, CORE_SHARD.stack_max)  # now full
    status, _ = mining.update_mining(
        1.0,
        active_tool=MiningTool(),
        held=True,
        aim_world=pygame.Vector2(1010, 1000),
        player_pos=PLAYER,
        fragments=frags,
        backpack=bp,
        hotbar=Hotbar.create(),
    )
    assert status == mining.FULL
    assert frag.hp == config.FRAGMENT_HP  # untouched
