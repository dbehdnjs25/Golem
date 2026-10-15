import random

import pygame

from game import config
from game.entities.structure import BIOME_RUIN, GRASS_RUIN, GRASS_VAULT, Structure
from game.items import glyphs
from game.world import structures
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


def test_the_grassland_sites_hold_the_elementless_pair():
    for seed in range(8):
        for site in _placed(seed):
            if site.kind in (GRASS_RUIN, GRASS_VAULT):
                assert site.glyph.biome is None
                assert WORLD.biome_at(site.pos) is not None


def test_the_guarded_vault_holds_the_stronger_cut():
    # The spec's pairing: an open ruin and a vault a golem stands over, same
    # gimmick, the vault stronger. It is what teaches that a guarded site is
    # worth the fight before any biome asks the player to believe it.
    sites = _placed(3)
    ruin = next(s for s in sites if s.kind is GRASS_RUIN)
    vault = next(s for s in sites if s.kind is GRASS_VAULT)
    assert ruin.glyph.gimmick == vault.glyph.gimmick
    assert vault.glyph.power > ruin.glyph.power
    assert vault.guarded and not ruin.guarded


def test_everything_lands_on_the_map_and_clear_of_the_core():
    for seed in range(8):
        for site in _placed(seed):
            assert WORLD.contains(site.pos)
            assert WORLD.center.distance_to(site.pos) > config.STRUCTURE_MIN_FROM_CORE


def test_opening_one_gives_its_drawing_once():
    site = Structure(pos=pygame.Vector2(0, 0), kind=GRASS_RUIN, glyph=glyphs.LESSER_SWIFT)
    assert not site.opened
    assert site.open() is glyphs.LESSER_SWIFT
    assert site.opened
    assert site.open() is None  # a looted ruin is just scenery


def test_you_have_to_be_standing_at_it():
    site = Structure(pos=pygame.Vector2(0, 0), kind=GRASS_RUIN, glyph=glyphs.LESSER_SWIFT)
    far = pygame.Vector2(config.STRUCTURE_REACH + 10, 0)
    assert not site.in_reach(far)
    assert site.in_reach(pygame.Vector2(config.STRUCTURE_REACH - 1, 0))


def test_no_two_sites_are_stacked_on_each_other():
    for seed in range(8):
        sites = _placed(seed)
        for i, a in enumerate(sites):
            for b in sites[i + 1 :]:
                assert a.pos.distance_to(b.pos) > config.STRUCTURE_SPACING
