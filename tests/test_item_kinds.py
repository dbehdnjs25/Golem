import dataclasses

import pytest

from game import config
from game.items.item_kinds import CATALOGUE, FRAGMENT, ITEM_KINDS, ItemKind


def test_fragment_row_matches_config():
    assert FRAGMENT.key == "fragment"
    assert FRAGMENT.stack_max == config.STACK_MAX_DEFAULT
    assert len(FRAGMENT.color) == 3


def test_catalogue_leads_with_fragment():
    assert CATALOGUE[0] is FRAGMENT


def test_lookup_maps_every_catalogue_key():
    assert set(ITEM_KINDS) == {k.key for k in CATALOGUE}
    assert ITEM_KINDS["fragment"] is FRAGMENT


def test_kinds_are_frozen_and_hashable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        FRAGMENT.stack_max = 99  # type: ignore[misc]
    assert {FRAGMENT: 1}[FRAGMENT] == 1  # usable as a dict key


def test_every_kind_has_a_positive_stack():
    assert all(k.stack_max > 0 for k in CATALOGUE)


def test_keys_are_unique():
    keys = [k.key for k in CATALOGUE]
    assert len(keys) == len(set(keys))


def test_kind_is_a_dataclass_with_a_name():
    assert isinstance(FRAGMENT, ItemKind)
    assert FRAGMENT.name
