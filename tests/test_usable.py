"""What may sit on the hotbar.

The hotbar is the hand: the selected slot is what the action key acts with.
A slot holding stone is a slot that does nothing, and five of them is a hand
with nothing in it -- so cargo stays in the pack and only what can be USED
goes on the bar.
"""

from game.inventory.grid import HOTBAR, PACK, Grid
from game.inventory.hotbar import Hotbar
from game.inventory.stack import Stack
from game.inventory.storage import Container
from game.items import tools
from game.items.item_kinds import (
    BENCH,
    COOKED_MEAT,
    CRUDE_AXE,
    IRON_INGOT,
    SNOWFIELD_DETECTOR,
    STAFF_ITEM,
    STONE,
    WOOD,
)
from game.systems import usable


def _grid_with(thing) -> tuple[Grid, Hotbar, Container]:
    grid = Grid(held=thing)
    return grid, Hotbar.create(), Container.empty(8)


# --- what counts ----------------------------------------------------------


def test_a_tool_is_usable():
    assert usable.is_usable(Stack(CRUDE_AXE, 1))


def test_the_weapon_is_usable():
    assert usable.is_usable(tools.WeaponTool())


def test_a_staff_is_usable():
    assert usable.is_usable(Stack(STAFF_ITEM, 1))


def test_a_station_is_usable():
    # It goes down in front of you, which is a use.
    assert usable.is_usable(Stack(BENCH, 1))


def test_food_is_usable():
    assert usable.is_usable(Stack(COOKED_MEAT, 2))


def test_a_detector_is_usable():
    # It does its work by being held rather than pressed, which still means
    # the slot is doing something.
    assert usable.is_usable(Stack(SNOWFIELD_DETECTOR, 1))


def test_plain_cargo_is_not():
    for kind in (STONE, WOOD, IRON_INGOT):
        assert not usable.is_usable(Stack(kind, 5)), kind.key


def test_nothing_is_not_usable():
    assert not usable.is_usable(None)


def test_the_table_is_built_from_the_catalogues():
    # Written out by hand it would be a second copy of five catalogues, and
    # the day a food was added it would be the stale one.
    from game.systems.consume import EDIBLE

    assert set(EDIBLE) <= usable.usable_kinds()


# --- the hotbar turns the rest away --------------------------------------


def test_cargo_cannot_be_dropped_on_the_hotbar():
    grid, hotbar, _pack = _grid_with(Stack(STONE, 5))
    grid.click(HOTBAR, 0, None, hotbar)
    assert hotbar.slots[0] is None
    assert isinstance(grid.held, Stack)  # still in hand, not vanished


def test_a_refused_drop_says_so():
    grid, hotbar, _pack = _grid_with(Stack(STONE, 5))
    assert not grid.refused
    grid.click(HOTBAR, 0, None, hotbar)
    assert grid.refused


def test_a_tool_still_goes_on():
    grid, hotbar, _pack = _grid_with(Stack(CRUDE_AXE, 1))
    grid.click(HOTBAR, 0, None, hotbar)
    assert hotbar.slots[0] is not None
    assert grid.held is None
    assert not grid.refused


def test_cargo_still_goes_in_the_pack():
    grid, _hotbar, pack = _grid_with(Stack(STONE, 5))
    grid.click(PACK, 0, pack, Hotbar.create())
    assert pack.count(STONE) == 5
    assert grid.held is None


def test_taking_something_off_the_hotbar_still_works():
    hotbar = Hotbar.create()
    hotbar.add(CRUDE_AXE, 1)
    grid = Grid()
    grid.click(HOTBAR, 0, None, hotbar)
    assert grid.held is not None
    assert hotbar.slots[0] is None


def test_a_refusal_changes_nothing_else():
    hotbar = Hotbar.create()
    hotbar.add(CRUDE_AXE, 1)
    grid = Grid(held=Stack(STONE, 5))
    grid.click(HOTBAR, 0, None, hotbar)
    assert hotbar.count(CRUDE_AXE) == 1  # the axe was not swapped out for it
