from game.inventory import packs
from game.items.item_kinds import ITEM_KINDS, STONE


def test_every_pack_is_a_catalogue_row_that_does_not_stack():
    assert packs.PACK_SLOTS
    for kind in packs.PACK_SLOTS:
        assert ITEM_KINDS[kind.key] is kind
        assert kind.stack_max == 1  # you wear one, you do not hoard them


def test_packs_are_ordered_by_how_much_they_hold():
    held = list(packs.PACK_SLOTS.values())
    assert held == sorted(held)
    assert len(set(held)) == len(held)


def test_ordinary_items_are_not_packs():
    assert packs.is_pack(STONE) is False
    assert packs.slots_of(STONE) == 0
