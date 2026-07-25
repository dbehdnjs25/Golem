from game.inventory.storage import Folder, transfer


def test_add_increases_count() -> None:
    f = Folder(cap_mb=50, mb_per_item=5)  # holds 10
    assert f.add(3) == 3
    assert f.count == 3
    assert f.used_mb == 15


def test_add_caps_at_capacity_and_reports_actual() -> None:
    f = Folder(cap_mb=50, mb_per_item=5)  # holds 10
    assert f.add(100) == 10
    assert f.is_full is True
    assert f.add(1) == 0  # no room left


def test_remove_decreases_count_and_reports_actual() -> None:
    f = Folder(cap_mb=50, mb_per_item=5)
    f.add(4)
    assert f.remove(3) == 3
    assert f.count == 1


def test_remove_cannot_go_below_empty() -> None:
    f = Folder(cap_mb=50, mb_per_item=5)
    f.add(2)
    assert f.remove(99) == 2  # bounded by what is stored
    assert f.count == 0


def test_transfer_moves_what_fits() -> None:
    src = Folder(cap_mb=50, mb_per_item=5)
    dst = Folder(cap_mb=15, mb_per_item=5)  # holds 3
    src.add(10)
    moved = transfer(src, dst)
    assert moved == 3
    assert dst.count == 3
    assert src.count == 7  # remainder stays (warehouse full)
