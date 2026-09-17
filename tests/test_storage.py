from game.inventory.storage import Container
from game.items.item_kinds import FRAGMENT, ItemKind

# Deliberately NOT in the catalogue: a container must handle any kind it is
# handed, so slots_used cannot depend on a catalogue lookup.
BULK = ItemKind(key="bulk", name="벌크", stack_max=10, color=(1, 2, 3))


def test_add_counts_per_kind_and_bills_slots():
    c = Container(slots=4)
    assert c.add(BULK, 3) == 3
    assert c.count(BULK) == 3
    assert c.slots_used == 1  # a partial stack still occupies a slot
    assert c.free_slots == 3


def test_a_full_stack_rolls_over_into_the_next_slot():
    c = Container(slots=4)
    c.add(BULK, 10)
    assert c.slots_used == 1
    c.add(BULK, 1)
    assert c.slots_used == 2


def test_topping_up_an_open_stack_takes_no_new_slot():
    c = Container(slots=1)
    c.add(BULK, 4)
    assert c.free_slots == 0  # the only slot is taken
    assert c.add(BULK, 6) == 6  # but the open stack still has room
    assert c.count(BULK) == 10
    assert c.add(BULK, 1) == 0  # now it is genuinely full


def test_add_caps_at_slot_capacity_and_reports_actual():
    c = Container(slots=2)
    assert c.add(BULK, 100) == 20
    assert c.add(BULK, 1) == 0
    assert c.free_slots == 0


def test_remove_is_bounded_by_what_is_stored():
    c = Container(slots=4)
    c.add(BULK, 4)
    assert c.remove(BULK, 3) == 3
    assert c.count(BULK) == 1
    assert c.remove(BULK, 99) == 1
    assert c.count(BULK) == 0
    assert c.slots_used == 0  # an emptied row frees its slot


def test_removing_an_absent_kind_reports_zero():
    c = Container(slots=4)
    assert c.remove(BULK, 5) == 0


def test_kinds_are_counted_separately_and_share_the_slots():
    c = Container(slots=2)
    c.add(BULK, 10)  # one full slot
    assert c.count(BULK) == 10
    assert c.count(FRAGMENT) == 0
    assert c.add(FRAGMENT, 999) == FRAGMENT.stack_max  # one slot left


def test_fits_reports_what_would_actually_go_in():
    c = Container(slots=2)
    assert c.fits(BULK, 4) == 4
    assert c.fits(BULK, 50) == 20
    c.add(BULK, 15)  # one full stack + a partial holding 5
    assert c.fits(BULK, 50) == 5  # only the open stack's room is left


def test_rows_follow_catalogue_order_and_skip_empties():
    c = Container(slots=10)
    assert c.rows() == []
    c.add(FRAGMENT, 2)
    assert c.rows() == [(FRAGMENT, 2)]
    c.add(FRAGMENT, 3)
    assert c.rows() == [(FRAGMENT, 5)]  # count changed, position did not
    c.remove(FRAGMENT, 5)
    assert c.rows() == []  # an emptied row leaves the list
    # BULK is stored (add/count/slots_used all work on it) but is not in
    # CATALOGUE, so it must never surface in rows() -- this is what actually
    # exercises the "absent from CATALOGUE is invisible here" filtering, not
    # just row ordering.
    c.add(FRAGMENT, 1)
    c.add(BULK, 1)
    assert c.rows() == [(FRAGMENT, 1)]


def test_reserved_slots_cannot_be_taken_by_anything_else():
    c = Container(slots=4)
    c.reserve(3)
    assert c.free_slots == 1
    assert c.fits(BULK, 100) == 10
    assert c.add(BULK, 100) == 10


def test_release_gives_the_slots_back():
    c = Container(slots=4)
    c.reserve(4)
    assert c.fits(BULK, 1) == 0
    c.release(4)
    assert c.fits(BULK, 100) == 40


def test_release_cannot_drive_the_reservation_negative():
    c = Container(slots=4)
    c.reserve(1)
    c.release(99)
    assert c.reserved_slots == 0
    assert c.free_slots == 4


def test_two_containers_do_not_share_the_default_dict():
    a, b = Container(slots=4), Container(slots=4)
    a.add(FRAGMENT, 1)
    assert b.count(FRAGMENT) == 0


def test_the_old_megabyte_api_is_gone():
    import game.inventory.storage as storage

    assert not hasattr(storage, "Folder")
    c = Container(slots=4)
    assert not hasattr(c, "used_mb")
    assert not hasattr(c, "free_mb")
    assert not hasattr(c, "cap_mb")
