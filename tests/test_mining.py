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
    OBSIDIAN_STONE,
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
    assert _swing(tools.pickaxe(grades.IRON_G), OBSIDIAN_STONE)[0] == mining.TOO_HARD
    assert _swing(tools.pickaxe(grades.GOLD_G), OBSIDIAN_STONE, dt=0.1)[0] == mining.MINING


def test_litter_comes_up_with_no_tool_at_all():
    # The bootstrap: a player holding nothing can still pick these up.
    from game.items.item_kinds import TWIG

    status, node = _swing(tools.pickaxe(grades.CRUDE_G), TWIG, dt=0.1)
    assert status == mining.MINING
    assert node.hp < config.FRAGMENT_HP


def test_a_crude_axe_fells_a_tree():
    status, node = _swing(tools.axe(grades.CRUDE_G), WOOD, dt=0.1)
    assert status == mining.MINING


def test_a_pickaxe_cannot_fell_a_tree():
    status, node = _swing(tools.pickaxe(grades.STEEL_G), WOOD)
    assert status == mining.WRONG_TOOL
    assert node.hp == config.FRAGMENT_HP


def test_an_axe_is_still_the_faster_way_to_wood():
    _, by_hand = _swing(tools.pickaxe(grades.WOOD_G), WOOD, dt=0.1)
    _, with_axe = _swing(tools.axe(grades.STEEL_G), WOOD, dt=0.1)
    assert with_axe.hp < by_hand.hp


def test_ore_still_refuses_the_wrong_family():
    assert _swing(tools.axe(grades.STEEL_G), COPPER_ORE)[0] == mining.WRONG_TOOL


def test_an_empty_hand_can_still_take_litter():
    # The very first action of a run: nothing selected, nothing owned.
    from game.items.item_kinds import TWIG

    status, node = _swing(None, TWIG, dt=0.1)
    assert status == mining.MINING
    assert node.hp < config.FRAGMENT_HP


def test_an_empty_hand_cannot_fell_a_tree():
    status, node = _swing(None, WOOD)
    assert status == mining.WRONG_TOOL
    assert node.hp == config.FRAGMENT_HP


def test_an_empty_hand_cannot_mine():
    assert _swing(None, STONE)[0] == mining.WRONG_TOOL


def _digger():
    from game.entities.player import Player

    return Player(pos=pygame.Vector2(PLAYER))


def test_digging_costs_wind():
    player = _digger()
    node = Fragment(pos=pygame.Vector2(PLAYER), kind=STONE)
    mining.update_mining(
        1.0,
        active_tool=tools.pickaxe(grades.STONE_G),
        held=True,
        aim_world=node.pos,
        player_pos=player.pos,
        fragments=[node],
        backpack=None,
        hotbar=Hotbar.create(),
        player=player,
    )
    assert player.stamina < player.max_stamina


def test_running_dry_slows_digging_but_never_stops_it():
    # Blocking it outright leaves someone who came out for one bagful standing
    # still. Pressure, not punishment.
    def dug(stamina: float) -> float:
        player = _digger()
        player.stamina = stamina
        node = Fragment(pos=pygame.Vector2(PLAYER), kind=STONE, hp=9999.0)
        mining.update_mining(
            1.0,
            active_tool=tools.pickaxe(grades.STONE_G),
            held=True,
            aim_world=node.pos,
            player_pos=player.pos,
            fragments=[node],
            backpack=None,
            hotbar=Hotbar.create(),
            player=player,
        )
        return 9999.0 - node.hp

    assert 0 < dug(0.0) < dug(100.0)


def test_digging_still_works_with_nobody_holding_the_pick():
    # The player is optional: plenty of tests and tools swing without one, and
    # a stamina rule must not make the whole call need a body.
    node = Fragment(pos=pygame.Vector2(PLAYER), kind=STONE)
    status, _ = mining.update_mining(
        0.01,
        active_tool=tools.pickaxe(grades.STONE_G),
        held=True,
        aim_world=node.pos,
        player_pos=pygame.Vector2(PLAYER),
        fragments=[node],
        backpack=None,
        hotbar=Hotbar.create(),
    )
    assert status == mining.MINING
