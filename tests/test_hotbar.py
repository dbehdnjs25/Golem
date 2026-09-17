from game import config
from game.inventory.hotbar import Hotbar
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
