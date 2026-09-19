from game.inventory import grid
from game.inventory.grid import Grid
from game.inventory.hotbar import Hotbar
from game.inventory.stack import Stack
from game.inventory.storage import Container
from game.items.item_kinds import CORE_SHARD, STONE
from game.items.tools import MiningTool


def _both() -> tuple[Hotbar, Container]:
    return Hotbar.create(), Container.empty(4)


def test_clicking_a_full_slot_picks_it_up():
    hb, pack = _both()
    pack.add(STONE, 3)
    g = Grid()
    g.click(grid.PACK, 0, pack, hb)
    assert g.held == Stack(STONE, 3)
    assert pack.slots[0] is None


def test_clicking_an_empty_slot_with_an_empty_hand_does_nothing():
    hb, pack = _both()
    g = Grid()
    g.click(grid.PACK, 0, pack, hb)
    assert g.held is None


def test_clicking_an_empty_slot_while_holding_puts_it_down():
    hb, pack = _both()
    g = Grid(held=Stack(STONE, 3))
    g.click(grid.PACK, 2, pack, hb)
    assert g.held is None
    assert pack.slots[2] == Stack(STONE, 3)


def test_a_stack_can_be_moved_from_the_pack_onto_the_hotbar():
    # This is the whole point of the screen: choosing what death will spare.
    hb, pack = _both()
    pack.add(CORE_SHARD, 2)
    g = Grid()
    g.click(grid.PACK, 0, pack, hb)
    g.click(grid.HOTBAR, 1, pack, hb)
    assert hb.slots[1] == Stack(CORE_SHARD, 2)
    assert g.held is None


def test_dropping_onto_the_same_kind_merges():
    hb, pack = _both()
    pack.add(STONE, 2)
    g = Grid(held=Stack(STONE, 3))
    g.click(grid.PACK, 0, pack, hb)
    assert pack.slots[0] == Stack(STONE, 5)
    assert g.held is None


def test_dropping_onto_a_different_kind_swaps_into_the_hand():
    hb, pack = _both()
    pack.add(STONE, 2)
    g = Grid(held=Stack(CORE_SHARD, 1))
    g.click(grid.PACK, 0, pack, hb)
    assert pack.slots[0] == Stack(CORE_SHARD, 1)
    assert g.held == Stack(STONE, 2)


def test_a_tool_cannot_be_put_into_the_pack():
    # Tools live on the hotbar. Letting one into the pack would let a death
    # take the pickaxe, which is the one thing the hotbar exists to prevent.
    hb, pack = _both()
    hb.slots[0] = MiningTool()
    g = Grid()
    g.click(grid.HOTBAR, 0, pack, hb)
    assert isinstance(g.held, MiningTool)
    g.click(grid.PACK, 0, pack, hb)
    assert isinstance(g.held, MiningTool)  # still in hand
    assert pack.slots[0] is None


def test_tools_move_freely_between_hotbar_slots():
    hb, pack = _both()
    hb.slots[0] = MiningTool()
    g = Grid()
    g.click(grid.HOTBAR, 0, pack, hb)
    g.click(grid.HOTBAR, 3, pack, hb)
    assert hb.slots[0] is None
    assert isinstance(hb.slots[3], MiningTool)
    assert g.held is None


def test_the_pack_cannot_be_clicked_when_there_is_none():
    hb = Hotbar.create()
    g = Grid(held=Stack(STONE, 1))
    g.click(grid.PACK, 0, None, hb)
    assert g.held == Stack(STONE, 1)  # nothing happened


def test_closing_puts_what_is_held_back_rather_than_losing_it():
    hb, pack = _both()
    g = Grid(held=Stack(STONE, 3))
    g.close(pack, hb)
    assert g.held is None
    assert pack.count(STONE) == 3


def test_closing_with_a_full_pack_falls_back_to_the_hotbar():
    hb = Hotbar.create()
    pack = Container.empty(1)
    pack.add(STONE, STONE.stack_max)
    g = Grid(held=Stack(CORE_SHARD, 2))
    g.close(pack, hb)
    assert g.held is None
    assert hb.count(CORE_SHARD) == 2


def test_closing_puts_a_held_tool_back_on_the_hotbar():
    hb, pack = _both()
    g = Grid(held=MiningTool())
    g.close(pack, hb)
    assert g.held is None
    assert any(isinstance(s, MiningTool) for s in hb.slots)


def test_closing_with_an_empty_hand_is_harmless():
    hb, pack = _both()
    g = Grid()
    g.close(pack, hb)
    assert g.held is None
