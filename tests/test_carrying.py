from game.inventory.hotbar import Hotbar
from game.inventory.storage import Container
from game.items.item_kinds import STONE
from game.items.tools import MiningTool
from game.systems import carrying


def test_it_goes_into_the_backpack_when_there_is_one():
    pack, hb = Container.empty(3), Hotbar.create()
    assert carrying.store(STONE, 5, pack, hb) == 5
    assert pack.count(STONE) == 5
    assert hb.count(STONE) == 0  # the hotbar is left alone


def test_it_falls_back_to_the_hotbar_with_no_backpack():
    hb = Hotbar.create()
    assert carrying.store(STONE, 5, None, hb) == 5
    assert hb.count(STONE) == 5


def test_a_full_backpack_does_not_spill_into_the_hotbar():
    # The five hotbar slots are the only thing death spares. Filling them
    # behind the player's back would spend that protection for them.
    pack, hb = Container.empty(1), Hotbar.create()
    pack.add(STONE, STONE.stack_max)
    assert carrying.store(STONE, 5, pack, hb) == 0
    assert hb.count(STONE) == 0


def test_a_full_hotbar_with_no_backpack_takes_nothing():
    hb = Hotbar.create()
    for i in range(len(hb.slots)):
        hb.slots[i] = MiningTool()
    assert carrying.store(STONE, 1, None, hb) == 0


def test_it_reports_the_partial_amount_it_managed():
    pack, hb = Container.empty(1), Hotbar.create()
    assert carrying.store(STONE, STONE.stack_max + 10, pack, hb) == STONE.stack_max


def test_room_for_agrees_with_store():
    # One rule asked two ways -- "you can put it here" must never disagree with
    # what happens when you do.
    pack, hb = Container.empty(1), Hotbar.create()
    assert carrying.room_for(STONE, pack, hb) == 1
    pack.add(STONE, STONE.stack_max)
    assert carrying.room_for(STONE, pack, hb) == 0
    assert carrying.store(STONE, 1, pack, hb) == 0


def test_room_for_uses_the_hotbar_when_there_is_no_backpack():
    hb = Hotbar.create()
    assert carrying.room_for(STONE, None, hb) == 1
    for i in range(len(hb.slots)):
        hb.slots[i] = MiningTool()
    assert carrying.room_for(STONE, None, hb) == 0
