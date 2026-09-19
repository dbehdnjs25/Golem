from game.inventory.stack import Stack
from game.inventory.storage import Container
from game.items.item_kinds import CORE_SHARD, STONE


def test_an_empty_container_has_the_size_it_was_made_with():
    c = Container.empty(4)
    assert (c.size, c.used, c.free) == (4, 0, 4)
    assert c.slots == [None, None, None, None]


def test_adding_fills_the_first_empty_slot():
    c = Container.empty(3)
    assert c.add(STONE, 5) == 5
    assert c.slots[0] == Stack(STONE, 5)
    assert c.slots[1] is None


def test_adding_tops_up_an_open_stack_before_opening_a_new_one():
    c = Container.empty(3)
    c.add(STONE, STONE.stack_max - 2)
    c.add(STONE, 5)
    assert c.slots[0].count == STONE.stack_max
    assert c.slots[1].count == 3
    assert c.used == 2


def test_adding_stops_when_the_slots_run_out_and_reports_what_went_in():
    c = Container.empty(1)
    assert c.add(STONE, 999) == STONE.stack_max
    assert c.add(STONE, 1) == 0
    assert c.free == 0


def test_count_sums_a_kind_across_every_slot():
    c = Container.empty(3)
    c.add(STONE, STONE.stack_max + 4)
    assert c.count(STONE) == STONE.stack_max + 4
    assert c.count(CORE_SHARD) == 0


def test_removing_drains_the_last_slots_first():
    # Draining from the end keeps earlier slots stable, so a stack the player
    # is looking at does not jump position when something is spent.
    c = Container.empty(3)
    c.add(STONE, STONE.stack_max + 5)
    assert c.remove(STONE, 5) == 5
    assert c.slots[1] is None
    assert c.slots[0].count == STONE.stack_max


def test_removing_is_bounded_by_what_is_there():
    c = Container.empty(2)
    c.add(STONE, 3)
    assert c.remove(STONE, 99) == 3
    assert c.used == 0


def test_fits_reports_what_would_actually_go_in():
    c = Container.empty(2)
    assert c.fits(STONE, 999) == STONE.stack_max * 2
    c.add(STONE, STONE.stack_max + 1)
    assert c.fits(STONE, 999) == STONE.stack_max - 1


def test_different_kinds_share_the_slots():
    c = Container.empty(2)
    c.add(STONE, 1)
    assert c.add(CORE_SHARD, 999) == CORE_SHARD.stack_max
    assert c.free == 0
    assert c.add(STONE, 999) == STONE.stack_max - 1  # only the open stone stack


def test_take_lifts_a_slot_out_and_leaves_it_empty():
    c = Container.empty(2)
    c.add(STONE, 4)
    assert c.take(0) == Stack(STONE, 4)
    assert c.slots[0] is None


def test_take_on_an_empty_slot_gives_nothing():
    assert Container.empty(2).take(1) is None


def test_put_drops_a_stack_into_an_empty_slot():
    c = Container.empty(2)
    assert c.put(1, Stack(STONE, 3)) is None
    assert c.slots[1] == Stack(STONE, 3)


def test_put_onto_the_same_kind_merges_and_hands_back_the_remainder():
    c = Container.empty(1)
    c.add(STONE, STONE.stack_max - 2)
    assert c.put(0, Stack(STONE, 5)) == Stack(STONE, 3)
    assert c.slots[0].is_full


def test_put_onto_a_different_kind_swaps():
    c = Container.empty(1)
    c.add(STONE, 4)
    assert c.put(0, Stack(CORE_SHARD, 2)) == Stack(STONE, 4)
    assert c.slots[0] == Stack(CORE_SHARD, 2)


def test_rows_lists_what_is_held_in_catalogue_order():
    c = Container.empty(4)
    c.add(STONE, 3)
    c.add(CORE_SHARD, 2)
    assert c.rows() == [(CORE_SHARD, 2), (STONE, 3)]


def test_the_old_dict_model_is_gone():
    # It could say how many slots were used but never which, and a grid the
    # player drags things around in cannot be built on that.
    c = Container.empty(2)
    assert not hasattr(c, "items")
    assert not hasattr(c, "reserved_slots")
    assert not hasattr(c, "slots_used")
