from game.inventory.storage import Folder
from game.items.item_kinds import FRAGMENT, ItemKind

# Deliberately NOT in the catalogue: a folder must handle any kind it is handed,
# so used_mb cannot depend on a catalogue lookup.
HEAVY = ItemKind(key="heavy", name="큰 파일", mb=10, color=(1, 2, 3))


def test_add_counts_per_kind_and_bills_megabytes():
    f = Folder(cap_mb=30)  # 10 fragments
    assert f.add(FRAGMENT, 3) == 3
    assert f.count(FRAGMENT) == 3
    assert f.used_mb == 9
    assert f.free_mb == 21


def test_add_caps_at_capacity_and_reports_actual():
    f = Folder(cap_mb=30)
    assert f.add(FRAGMENT, 100) == 10
    assert f.add(FRAGMENT, 1) == 0
    assert f.free_mb == 0


def test_remove_is_bounded_by_what_is_stored():
    f = Folder(cap_mb=30)
    f.add(FRAGMENT, 4)
    assert f.remove(FRAGMENT, 3) == 3
    assert f.count(FRAGMENT) == 1
    assert f.remove(FRAGMENT, 99) == 1
    assert f.count(FRAGMENT) == 0


def test_removing_an_absent_kind_reports_zero():
    f = Folder(cap_mb=30)
    assert f.remove(HEAVY, 5) == 0


def test_kinds_are_counted_separately_and_share_the_cap():
    f = Folder(cap_mb=30)
    f.add(HEAVY, 2)  # 20 MB
    assert f.count(HEAVY) == 2
    assert f.count(FRAGMENT) == 0
    assert f.add(FRAGMENT, 5) == 3  # only 10 MB left -> 3 fragments


def test_fits_reports_what_would_actually_go_in():
    f = Folder(cap_mb=30)
    assert f.fits(FRAGMENT, 4) == 4
    assert f.fits(FRAGMENT, 50) == 10
    f.add(FRAGMENT, 9)
    assert f.fits(FRAGMENT, 5) == 1


def test_rows_follow_catalogue_order_and_skip_empties():
    f = Folder(cap_mb=100)
    assert f.rows() == []
    f.add(FRAGMENT, 2)
    assert f.rows() == [(FRAGMENT, 2)]
    f.add(FRAGMENT, 3)
    assert f.rows() == [(FRAGMENT, 5)]  # count changed, position did not
    f.remove(FRAGMENT, 5)
    assert f.rows() == []  # an emptied row leaves the list
    # HEAVY is stored (add/count/used_mb all work on it) but is not in CATALOGUE,
    # so it must never surface in rows() -- this is what actually exercises the
    # "absent from CATALOGUE is invisible here" filtering, not just row ordering.
    f.add(FRAGMENT, 1)
    f.add(HEAVY, 1)
    assert f.rows() == [(FRAGMENT, 1)]


def test_reserved_space_cannot_be_taken_by_anything_else():
    f = Folder(cap_mb=30)
    f.reserve(21)
    assert f.free_mb == 9
    assert f.fits(FRAGMENT, 10) == 3
    assert f.add(FRAGMENT, 10) == 3


def test_release_gives_the_space_back():
    f = Folder(cap_mb=30)
    f.reserve(30)
    assert f.fits(FRAGMENT, 1) == 0
    f.release(30)
    assert f.fits(FRAGMENT, 10) == 10


def test_release_cannot_drive_the_reservation_negative():
    f = Folder(cap_mb=30)
    f.reserve(3)
    f.release(99)
    assert f.reserved_mb == 0
    assert f.free_mb == 30


def test_two_folders_do_not_share_the_default_dict():
    a, b = Folder(cap_mb=30), Folder(cap_mb=30)
    a.add(FRAGMENT, 1)
    assert b.count(FRAGMENT) == 0


def test_the_old_int_api_is_gone():
    import game.inventory.storage as storage

    assert not hasattr(storage, "transfer")
    assert not hasattr(Folder(cap_mb=30), "is_full")
