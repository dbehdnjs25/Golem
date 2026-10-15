import dataclasses

import pytest

from game.items import glyphs
from game.items.glyphs import BASIC, GLYPHS, GREATER, SUPREME, Glyph
from game.world import biomes


def test_rows_are_frozen_with_unique_keys():
    with pytest.raises(dataclasses.FrozenInstanceError):
        GLYPHS[0].power = 1.0  # type: ignore[misc]
    keys = [g.key for g in GLYPHS]
    assert len(keys) == len(set(keys))


def test_every_glyph_fits_somewhere():
    # A glyph that cannot be carved onto anything is a dead row: the player
    # would learn it, see it listed, and never be able to use it.
    for glyph in GLYPHS:
        assert glyph.fits, glyph.key


def test_only_the_grassland_glyphs_have_no_element():
    for glyph in GLYPHS:
        if glyph.biome is None:
            assert glyph.element is None
        else:
            assert glyph.element == glyph.biome.element


def test_each_ring_biome_has_a_full_ladder():
    for biome in biomes.RING_BIOMES:
        tiers = [g.tier for g in glyphs.glyphs_of(biome)]
        assert sorted(tiers) == sorted([BASIC, GREATER, SUPREME]), biome.key


def test_power_climbs_with_the_tier_inside_a_biome():
    for biome in biomes.RING_BIOMES:
        ladder = sorted(
            glyphs.glyphs_of(biome), key=lambda g: (BASIC, GREATER, SUPREME).index(g.tier)
        )
        powers = [g.power for g in ladder]
        assert powers == sorted(powers)
        assert powers[0] < powers[-1]  # strictly worth climbing


def test_the_grassland_offers_a_weak_and_a_strong_cut_of_the_same_thing():
    # The spec's two grassland sites: an unguarded small one and a guarded big
    # one with "the same gimmick, stronger".
    plain = glyphs.glyphs_of(None)
    assert len(plain) == 2
    weak, strong = sorted(plain, key=lambda g: g.power)
    assert weak.gimmick == strong.gimmick
    assert strong.power > weak.power


def test_the_supreme_glyphs_are_not_lying_about_where_they_come_from():
    # They drop from bosses, which do not exist yet. Marked so, so nothing
    # tries to scatter them in a structure and quietly skip step 8.
    for glyph in GLYPHS:
        if glyph.tier == SUPREME:
            assert glyph.source == glyphs.FROM_BOSS


def test_lookup_by_key_covers_the_catalogue():
    assert len(glyphs.GLYPH_BY_KEY) == len(GLYPHS)
    for glyph in GLYPHS:
        assert glyphs.GLYPH_BY_KEY[glyph.key] is glyph


def test_a_glyph_knows_what_it_can_be_carved_on():
    fire = next(g for g in GLYPHS if g.biome is biomes.VOLCANO and g.tier == BASIC)
    assert glyphs.STAFF in fire.fits


def test_glyphs_of_an_unknown_biome_is_empty_not_an_error():
    assert glyphs.glyphs_of(biomes.GRASSLAND) == glyphs.glyphs_of(None)


def test_the_catalogue_is_the_size_the_spec_asks_for():
    # Two grassland cuts plus three per ring biome.
    assert len(GLYPHS) == 2 + 3 * len(biomes.RING_BIOMES)


def test_a_glyph_is_a_plain_row():
    assert isinstance(GLYPHS[0], Glyph)
    assert all(g.name for g in GLYPHS)
