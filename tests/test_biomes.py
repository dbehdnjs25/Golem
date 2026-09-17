import dataclasses

import pytest

from game.items import item_kinds
from game.world import biomes
from game.world.biomes import BIOME_BY_KEY, BIOMES, GRASSLAND, RING_BIOMES, Biome


def test_there_are_five_ring_biomes_plus_the_grassland():
    assert len(RING_BIOMES) == 5
    assert BIOMES == (GRASSLAND,) + RING_BIOMES


def test_ring_order_is_difficulty_order():
    # Volcano first: lava is a visible, stationary hazard, the easiest to read.
    # Bog fourth: its stamina drain is unfair before cooking and potions exist.
    # Wasteland last: raids come in crowds and chaining is the answer to them.
    assert [b.key for b in RING_BIOMES] == [
        "volcano",
        "snowfield",
        "wind_plateau",
        "bog",
        "wasteland",
    ]


def test_the_grassland_has_no_attribute_and_no_material():
    # Grade comes from the grassland, attributes come from the biomes. The two
    # ladders do not mix, so the grassland carries neither of the biome fields.
    assert GRASSLAND.element is None
    assert GRASSLAND.material is None


def test_every_ring_biome_has_its_own_element_and_material():
    elements = [b.element for b in RING_BIOMES]
    materials = [b.material for b in RING_BIOMES]
    assert all(e is not None for e in elements)
    assert all(m is not None for m in materials)
    assert len(set(elements)) == 5
    assert len(set(materials)) == 5


def test_materials_are_real_catalogue_rows():
    for biome in RING_BIOMES:
        assert biome.material is not None
        assert item_kinds.ITEM_KINDS[biome.material.key] is biome.material


def test_element_constants_are_the_ones_used():
    assert {b.element for b in RING_BIOMES} == {
        biomes.FIRE,
        biomes.ICE,
        biomes.WIND,
        biomes.POISON,
        biomes.LIGHTNING,
    }


def test_keys_names_and_colours_are_unique():
    assert len({b.key for b in BIOMES}) == len(BIOMES)
    assert len({b.name for b in BIOMES}) == len(BIOMES)
    assert len({b.color for b in BIOMES}) == len(BIOMES)


def test_lookup_maps_every_biome():
    assert set(BIOME_BY_KEY) == {b.key for b in BIOMES}
    assert BIOME_BY_KEY["grassland"] is GRASSLAND


def test_biomes_are_frozen_and_hashable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        GRASSLAND.name = "x"  # type: ignore[misc]
    assert {GRASSLAND: 1}[GRASSLAND] == 1


def test_biome_is_a_dataclass_row():
    assert isinstance(GRASSLAND, Biome)
    assert all(len(b.color) == 3 for b in BIOMES)
