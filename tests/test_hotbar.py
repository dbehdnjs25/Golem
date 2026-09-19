from game import config
from game.inventory.hotbar import Hotbar
from game.inventory.stack import Stack
from game.items.item_kinds import CORE_SHARD, STONE
from game.items.tools import MiningTool


def test_create_has_five_empty_slots():
    hb = Hotbar.create()
    assert len(hb.slots) == config.HOTBAR_SLOTS
    assert config.HOTBAR_SLOTS == 5
    assert all(s is None for s in hb.slots)


def test_active_tool_reflects_selection():
    hb = Hotbar.create()
    tool = MiningTool()
    hb.slots[0] = tool
    assert hb.active_tool is tool


def test_select_ignores_out_of_range():
    hb = Hotbar.create()
    hb.select(4)  # last valid slot
    assert hb.selected == 4
    hb.select(5)  # past the end
    assert hb.selected == 4
    hb.select(-1)
    assert hb.selected == 4


def test_the_unlock_concept_is_gone():
    assert not hasattr(Hotbar.create(), "unlocked")
    assert not hasattr(config, "HOTBAR_START_UNLOCKED")
    assert not hasattr(config, "HOTBAR_MAX_SLOTS")


def test_mining_tool_defaults():
    t = MiningTool()
    assert t.range == config.MINING_RANGE
    assert t.dps == config.MINING_DPS


def test_a_slot_can_hold_a_stack_instead_of_a_tool():
    hb = Hotbar.create()
    hb.slots[0] = Stack(STONE, 3)
    assert hb.active_stack == Stack(STONE, 3)
    assert hb.active_tool is None  # a stack is not a tool


def test_a_tool_slot_reports_no_stack():
    hb = Hotbar.create()
    hb.slots[0] = MiningTool()
    assert hb.active_tool is not None
    assert hb.active_stack is None


def test_adding_fills_empty_slots_without_disturbing_tools():
    hb = Hotbar.create()
    hb.slots[0] = MiningTool()
    assert hb.add(STONE, 5) == 5
    assert isinstance(hb.slots[0], MiningTool)  # the tool stayed put
    assert hb.slots[1] == Stack(STONE, 5)


def test_adding_tops_up_an_open_stack_first():
    hb = Hotbar.create()
    hb.add(STONE, 2)
    hb.add(STONE, 3)
    assert hb.slots[0] == Stack(STONE, 5)
    assert hb.slots[1] is None


def test_a_hotbar_full_of_tools_takes_nothing():
    hb = Hotbar.create()
    for i in range(len(hb.slots)):
        hb.slots[i] = MiningTool()
    assert hb.add(STONE, 1) == 0
    assert hb.has_room_for(STONE) is False


def test_counting_and_removing_span_the_slots():
    hb = Hotbar.create()
    hb.add(CORE_SHARD, CORE_SHARD.stack_max)
    hb.add(CORE_SHARD, 3)
    assert hb.count(CORE_SHARD) == CORE_SHARD.stack_max + 3
    assert hb.remove(CORE_SHARD, 4) == 4
    assert hb.count(CORE_SHARD) == CORE_SHARD.stack_max - 1


def test_has_room_for_sees_an_open_stack_even_with_no_empty_slot():
    hb = Hotbar.create()
    hb.add(STONE, 1)
    for i in range(1, len(hb.slots)):
        hb.slots[i] = MiningTool()
    assert hb.has_room_for(STONE) is True
    assert hb.has_room_for(CORE_SHARD) is False
