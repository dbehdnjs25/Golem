import pytest

from game.inventory.stack import Stack
from game.items.item_kinds import CORE_SHARD, STONE


def test_a_stack_knows_its_room():
    s = Stack(STONE, 10)
    assert s.room == STONE.stack_max - 10
    assert s.is_full is False
    assert Stack(STONE, STONE.stack_max).is_full is True


def test_merging_pours_in_what_fits_and_reports_it():
    a = Stack(STONE, STONE.stack_max - 3)
    b = Stack(STONE, 10)
    assert a.merge(b) == 3
    assert a.is_full
    assert b.count == 7  # the rest stays where it was


def test_merging_a_different_kind_takes_nothing():
    a, b = Stack(STONE, 1), Stack(CORE_SHARD, 1)
    assert a.merge(b) == 0
    assert (a.count, b.count) == (1, 1)


def test_splitting_takes_what_was_asked_for():
    s = Stack(STONE, 10)
    half = s.split(4)
    assert (half.kind, half.count) == (STONE, 4)
    assert s.count == 6


def test_splitting_is_bounded_by_what_is_there():
    s = Stack(STONE, 3)
    assert s.split(99).count == 3
    assert s.count == 0


def test_a_stack_cannot_be_built_over_its_kind_s_limit():
    # An over-full stack would quietly break every slot count that reads it.
    with pytest.raises(ValueError):
        Stack(CORE_SHARD, CORE_SHARD.stack_max + 1)
