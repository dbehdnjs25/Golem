import math
import random

import pygame
import pytest

from game import config
from game.systems import detector
from game.world import biomes
from game.world.map import WorldMap

WORLD = WorldMap(rotation=19.0)
SITES = WORLD.temple_sites(random.Random(3))


def test_there_is_one_detector_per_ring_biome():
    assert len(detector.DETECTOR_OF) == len(biomes.RING_BIOMES)
    for biome in biomes.RING_BIOMES:
        assert biome in detector.DETECTOR_OF


def test_a_detector_knows_which_temple_it_is_for():
    for index, biome in enumerate(biomes.RING_BIOMES):
        kind = detector.DETECTOR_OF[biome]
        assert detector.biome_of(kind) is biome
        assert detector.temple_for(kind, WORLD, SITES) == SITES[index]


def test_an_ordinary_item_is_not_a_detector():
    from game.items.item_kinds import STONE

    assert detector.biome_of(STONE) is None


def test_the_bearing_points_at_the_temple():
    here = WORLD.center
    for site in SITES:
        want = math.degrees(math.atan2(site.y - here.y, site.x - here.x)) % 360
        assert detector.bearing(here, site) == pytest.approx(want)


def test_standing_on_it_still_answers_rather_than_dividing_by_zero():
    site = SITES[0]
    assert detector.bearing(pygame.Vector2(site), site) == 0.0
    assert detector.rough_distance(pygame.Vector2(site), site) == config.DISTANCE_WORDS[0]


def test_distance_is_a_word_not_a_number():
    # The whole point. A number would make the random placement pointless --
    # the player would walk a bearing and watch a counter, which is a puzzle
    # with one move in it.
    here = WORLD.center
    for site in SITES:
        said = detector.rough_distance(here, site)
        assert said in config.DISTANCE_WORDS
        assert not any(ch.isdigit() for ch in said)


def test_the_word_gets_nearer_as_you_close_in():
    site = SITES[0]
    toward = (site - WORLD.center).normalize()
    said = [
        detector.rough_distance(site - toward * gap, site)
        for gap in (20000, 12000, 6000, 1500, 100)
    ]
    # Each step is the same word or a nearer one; never further away.
    order = list(config.DISTANCE_WORDS)
    ranks = [order.index(word) for word in said]
    assert ranks == sorted(ranks, reverse=True)
    assert said[-1] == config.DISTANCE_WORDS[0]


def test_every_band_is_reachable_so_none_of_the_words_is_dead():
    site = SITES[0]
    toward = (site - WORLD.center).normalize()
    seen = {
        detector.rough_distance(site - toward * gap, site)
        for gap in range(0, int(WORLD.radius), 500)
    }
    assert seen == set(config.DISTANCE_WORDS)
