"""The spec's promise that the five terrains do not overlap.

Each biome's own tests look only at its own terrain. This file is the one that
puts all five side by side -- the promise is about them being DIFFERENT, and
nothing checking one at a time can see a leak.
"""

import math
import random

import pygame
import pytest

from game import config
from game.entities.player import Player
from game.systems import falling, survival, weather
from game.world import biomes, chasms, lava, mires
from game.world.map import WorldMap

WORLD = WorldMap(rotation=41.0)
RNG = random.Random(7)

LAVA = lava.place(WORLD, random.Random(7))
MIRES = mires.place(WORLD, random.Random(7))
CHASMS = chasms.place(WORLD, random.Random(7))

TERRAIN = {
    biomes.BURNT_FOREST: LAVA,
    biomes.BOG: MIRES,
    biomes.WIND_PLATEAU: CHASMS,
}


def _middle_of(biome) -> pygame.Vector2:
    index = biomes.RING_BIOMES.index(biome)
    radians = math.radians(WORLD.rotation + (index + 0.5) * WORLD.sector_degrees)
    reach = WORLD.grassland_radius + WORLD.ring_width * 0.5
    return pygame.Vector2(
        WORLD.center.x + math.cos(radians) * reach,
        WORLD.center.y + math.sin(radians) * reach,
    )


# --- each terrain stays home ----------------------------------------------


@pytest.mark.parametrize("owner", list(TERRAIN))
def test_a_biome_s_terrain_never_strays_into_another(owner):
    for spot in TERRAIN[owner]:
        assert WORLD.biome_at(spot.pos) is owner


@pytest.mark.parametrize("owner", list(TERRAIN))
def test_no_terrain_spills_into_the_grassland(owner):
    for spot in TERRAIN[owner]:
        assert WORLD.center.distance_to(spot.pos) > WORLD.grassland_radius


def test_every_terrain_biome_actually_got_some():
    # A biome whose feature failed to place is a biome with no character, and
    # the placer gives up quietly rather than looping forever.
    for owner, spots in TERRAIN.items():
        assert spots, owner.key


# --- the five do five different things ------------------------------------


def _player_in(biome) -> Player:
    return Player(pos=_middle_of(biome))


def test_only_the_burnt_forest_burns():
    for biome in biomes.RING_BIOMES:
        player = _player_in(biome)
        for spot in LAVA:
            if spot.holds(player.pos):
                break
        else:
            survival.update_lava(1.0, player, LAVA)
            assert player.hp == config.PLAYER_MAX_HP, biome.key


def test_only_the_bog_takes_breath_where_you_stand():
    for biome in biomes.RING_BIOMES:
        if biome is biomes.BOG:
            continue
        player = _player_in(biome)
        survival.update_mire(5.0, player, MIRES, moving=True)
        assert player.stamina == player.max_stamina, biome.key


def test_only_the_plateau_has_ground_that_is_not_there():
    for biome in biomes.RING_BIOMES:
        if biome is biomes.WIND_PLATEAU:
            continue
        player = _player_in(biome)
        assert not falling.update_fall(1.0, player, CHASMS), biome.key


def test_only_the_snowfield_shortens_what_can_be_seen():
    # The weather itself is blind to place; the scene is what asks for it
    # only in the right biome. What this holds is that the two storms are
    # separate functions, not one dressed twice.
    moments = [i * 0.25 for i in range(400)]
    assert any(abs(weather.blizzard_at(t) - weather.sandstorm_at(t)) > 0.5 for t in moments)


def test_only_the_wasteland_blunts_a_run():
    def ran(biome) -> float:
        player = _player_in(biome)
        start = pygame.Vector2(player.pos)
        player.update(1.0, pygame.Vector2(1, 0), WORLD, sprinting=True)
        return player.pos.distance_to(start)

    far = {biome: ran(biome) for biome in biomes.RING_BIOMES}
    slowest = min(far, key=lambda b: far[b])
    assert slowest is biomes.WASTELAND
    others = {v for b, v in far.items() if b is not biomes.WASTELAND}
    assert len(others) == 1  # every other biome runs at exactly one speed


# --- and the grassland does none of it ------------------------------------


def test_the_safe_land_stays_safe():
    # The grassland is where the core is and where the ward reaches. If any
    # of the five leaked into it, the one place meant to be plain would stop
    # being the one place meant to be plain.
    home = pygame.Vector2(WORLD.center) + pygame.Vector2(WORLD.grassland_radius * 0.5, 0)
    assert WORLD.biome_at(home) is biomes.GRASSLAND

    player = Player(pos=pygame.Vector2(home))
    survival.update_lava(5.0, player, LAVA)
    survival.update_mire(5.0, player, MIRES, moving=True)
    assert not falling.update_fall(5.0, player, CHASMS)

    start = pygame.Vector2(player.pos)
    player.update(1.0, pygame.Vector2(1, 0), WORLD, sprinting=True)
    walked = player.pos.distance_to(start)

    assert player.hp == config.PLAYER_MAX_HP
    assert walked == pytest.approx(config.PLAYER_SPEED * config.PLAYER_SPRINT_MULT)


def test_all_five_terrains_are_reproducible_together():
    # One shared seed, one world. If any placer reached for a different source
    # of randomness, two runs of the same seed would differ.
    def world_from(seed: int):
        return (
            [(p.pos, p.radius) for p in lava.place(WORLD, random.Random(seed))],
            [(m.pos, m.radius) for m in mires.place(WORLD, random.Random(seed))],
            [(c.pos, c.radius) for c in chasms.place(WORLD, random.Random(seed))],
        )

    assert world_from(3) == world_from(3)
    assert world_from(3) != world_from(4)
