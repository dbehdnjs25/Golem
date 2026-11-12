import random

import pygame

from game import config
from game.entities.structure import BIOME_RUIN, GRASS_VAULT, Structure
from game.items import glyphs
from game.world import biomes, structures
from game.world.map import WorldMap

WORLD = WorldMap(rotation=23.0)


def _placed(seed: int = 1):
    return structures.place(WORLD, random.Random(seed))


def test_the_same_seed_builds_the_same_world():
    assert [(s.pos, s.kind, s.glyph) for s in _placed(4)] == [
        (s.pos, s.kind, s.glyph) for s in _placed(4)
    ]


def test_different_seeds_move_them():
    assert [s.pos for s in _placed(1)] != [s.pos for s in _placed(2)]


def test_every_basic_glyph_can_be_found_somewhere():
    # The only way into the magic. One missing and that biome is shut, which
    # no amount of reading the placement code would show.
    for seed in range(12):
        found = {s.glyph.key for s in _placed(seed)}
        for glyph in glyphs.basic_glyphs():
            assert glyph.key in found, f"seed {seed} never offers {glyph.key}"


def test_a_biome_ruin_only_ever_holds_its_own_biome_s_drawing():
    for seed in range(8):
        for site in _placed(seed):
            if site.kind is BIOME_RUIN:
                assert site.glyph.biome is WORLD.biome_at(site.pos)


def test_the_vault_stands_in_the_grassland():
    for seed in range(8):
        vault = next(s for s in _placed(seed) if s.kind is GRASS_VAULT)
        assert WORLD.biome_at(vault.pos) is biomes.GRASSLAND


def test_the_vault_sells_a_walk_for_a_fight():
    # It holds one biome's basic shape -- the same thing that biome's own
    # ruin holds, three minutes out. Two prices for one reward, which is how
    # the safe land teaches that a guarded site is worth it.
    for seed in range(8):
        sites = _placed(seed)
        vault = next(s for s in sites if s.kind is GRASS_VAULT)
        assert vault.guarded
        assert vault.glyph.biome is not None
        far = [s for s in sites if s.kind is BIOME_RUIN and s.glyph is vault.glyph]
        assert far, vault.glyph.key  # the long way round still exists


def test_everything_lands_on_the_map_and_clear_of_the_core():
    for seed in range(8):
        for site in _placed(seed):
            assert WORLD.contains(site.pos)
            assert WORLD.center.distance_to(site.pos) > config.STRUCTURE_MIN_FROM_CORE


def test_opening_one_gives_its_drawing_once():
    first = glyphs.basic_glyphs()[0]
    site = Structure(pos=pygame.Vector2(0, 0), kind=BIOME_RUIN, glyph=first)
    assert not site.opened
    assert site.open() is first
    assert site.opened
    assert site.open() is None  # a looted ruin is just scenery


def test_you_have_to_be_standing_at_it():
    site = Structure(pos=pygame.Vector2(0, 0), kind=BIOME_RUIN, glyph=glyphs.basic_glyphs()[0])
    far = pygame.Vector2(config.STRUCTURE_REACH + 10, 0)
    assert not site.in_reach(far)
    assert site.in_reach(pygame.Vector2(config.STRUCTURE_REACH - 1, 0))


def test_no_two_sites_are_stacked_on_each_other():
    for seed in range(8):
        sites = _placed(seed)
        for i, a in enumerate(sites):
            for b in sites[i + 1 :]:
                assert a.pos.distance_to(b.pos) > config.STRUCTURE_SPACING
