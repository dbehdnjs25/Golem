import dataclasses

import pytest

from game import config
from game.items import item_kinds
from game.items.item_kinds import CATALOGUE, CORE_SHARD, ITEM_KINDS, STEEL_INGOT, ItemKind


def test_core_shard_leads_the_catalogue():
    assert CATALOGUE[0] is CORE_SHARD
    assert CORE_SHARD.key == "core_shard"
    assert CORE_SHARD.name == "코어 파편"


def test_the_file_metaphor_is_gone():
    assert not hasattr(item_kinds, "FRAGMENT")
    assert all("데이터" not in k.name for k in CATALOGUE)


def test_the_grade_ladder_is_present():
    ladder = ["stone", "copper_ingot", "iron_ingot", "gold_ingot", "brass_ingot", "steel_ingot"]
    assert all(key in ITEM_KINDS for key in ladder)


def test_zinc_is_an_ore_with_no_ingot():
    # Zinc is smelting-only: it feeds brass and never becomes a tool tier.
    assert "zinc_ore" in ITEM_KINDS
    assert "zinc_ingot" not in ITEM_KINDS


def test_every_biome_material_is_present():
    for key in ("obsidian", "frost_crystal", "weathered_stone", "bog_moss", "thunder_stone"):
        assert key in ITEM_KINDS


def test_lookup_maps_every_catalogue_key():
    assert set(ITEM_KINDS) == {k.key for k in CATALOGUE}
    assert ITEM_KINDS["steel_ingot"] is STEEL_INGOT


def test_kinds_are_frozen_and_hashable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        CORE_SHARD.stack_max = 99  # type: ignore[misc]
    assert {CORE_SHARD: 1}[CORE_SHARD] == 1  # usable as a dict key


def test_every_kind_has_a_positive_stack_and_a_colour():
    assert all(k.stack_max > 0 for k in CATALOGUE)
    assert all(len(k.color) == 3 for k in CATALOGUE)


def test_rare_kinds_stack_lower_than_the_default():
    assert CORE_SHARD.stack_max < config.STACK_MAX_DEFAULT
    assert ITEM_KINDS["potion"].stack_max < config.STACK_MAX_DEFAULT


def test_keys_are_unique():
    keys = [k.key for k in CATALOGUE]
    assert len(keys) == len(set(keys))


def test_names_are_unique():
    names = [k.name for k in CATALOGUE]
    assert len(names) == len(set(names))


def test_kind_is_a_dataclass_with_a_name():
    assert isinstance(CORE_SHARD, ItemKind)
    assert CORE_SHARD.name
