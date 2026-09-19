import pygame

from game import config
from game.entities.fragment import Fragment
from game.inventory.hotbar import Hotbar
from game.inventory.storage import Container
from game.items import grades, tools
from game.items.item_kinds import (
    COPPER_ORE,
    CORE_SHARD,
    GOLD_ORE,
    IRON_ORE,
    OBSIDIAN,
    STONE,
    WOOD,
)
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


def _swing(tool, kind, dt=1.0):
    """One swing at a node of ``kind``. Returns (status, node)."""
    node = Fragment(pos=pygame.Vector2(PLAYER.x + 10, PLAYER.y), kind=kind)
    status, _ = mining.update_mining(
        dt,
        active_tool=tool,
        held=True,
        aim_world=pygame.Vector2(node.pos),
        player_pos=PLAYER,
        fragments=[node],
        backpack=_backpack(),
        hotbar=Hotbar.create(),
    )
    return status, node


def test_a_wooden_pick_cannot_touch_iron():
    # And it must not leave a half-chewed node behind: the check comes before
    # any damage, or an unreachable ore sits there ruined.
    status, node = _swing(tools.pickaxe(grades.WOOD_G), IRON_ORE)
    assert status == mining.TOO_HARD
    assert node.hp == config.FRAGMENT_HP


def test_a_copper_pick_opens_iron():
    status, node = _swing(tools.pickaxe(grades.COPPER_G), IRON_ORE, dt=0.1)
    assert status == mining.MINING
    assert node.hp < config.FRAGMENT_HP


def test_an_axe_cannot_mine_ore():
    status, node = _swing(tools.axe(grades.STEEL_G), COPPER_ORE)
    assert status == mining.WRONG_TOOL
    assert node.hp == config.FRAGMENT_HP


def test_a_pickaxe_cannot_chop_wood():
    status, node = _swing(tools.pickaxe(grades.STEEL_G), WOOD)
    assert status == mining.WRONG_TOOL
    assert node.hp == config.FRAGMENT_HP


def test_an_axe_chops_wood():
    status, node = _swing(tools.axe(grades.WOOD_G), WOOD, dt=0.1)
    assert status == mining.MINING


def test_a_better_pick_digs_faster():
    _, slow = _swing(tools.pickaxe(grades.WOOD_G), STONE, dt=0.1)
    _, fast = _swing(tools.pickaxe(grades.STEEL_G), STONE, dt=0.1)
    assert fast.hp < slow.hp


def test_gold_is_shut_until_iron():
    assert _swing(tools.pickaxe(grades.COPPER_G), GOLD_ORE)[0] == mining.TOO_HARD
    assert _swing(tools.pickaxe(grades.IRON_G), GOLD_ORE, dt=0.1)[0] == mining.MINING


def test_biome_materials_are_shut_until_gold():
    assert _swing(tools.pickaxe(grades.IRON_G), OBSIDIAN)[0] == mining.TOO_HARD
    assert _swing(tools.pickaxe(grades.GOLD_G), OBSIDIAN, dt=0.1)[0] == mining.MINING
