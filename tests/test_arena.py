import random

import pygame

from game.entities.temple import Temple
from game.systems import arena
from game.world import biomes, temples
from game.world.map import WorldMap

WORLD = WorldMap(rotation=37.0)
SITES = WORLD.temple_sites(random.Random(3))


def _ready(index: int = 0, guards_down: bool = True) -> Temple:
    """A temple walked into, with the guard already seen to unless told not."""
    temple = temples.place(WORLD, SITES, random.Random(1))[index]
    temple.guards_down = guards_down
    temple.enter(temple.pos + pygame.Vector2(temple.radius * 3, 0))
    return temple


def _ground() -> arena.Ground:
    return arena.Ground()


# --- the altar will not answer while the guard stands ---------------------


def test_the_guard_has_to_be_down_first():
    temple = _ready(guards_down=False)
    assert arena.why_not(temple) is not None
    assert not arena.summon(temple, _ground(), random.Random(1))


def test_with_the_guard_down_it_answers():
    temple = _ready()
    assert arena.why_not(temple) is None
    assert arena.summon(temple, _ground(), random.Random(1))


def test_it_refuses_from_outside():
    temple = _ready()
    temple.leave()
    assert arena.why_not(temple) is not None


def test_a_dead_boss_cannot_be_called_again():
    temple = _ready()
    temple.boss_killed = True
    assert arena.why_not(temple) is not None


def test_it_refuses_while_one_is_already_up():
    temple = _ready()
    ground = _ground()
    arena.summon(temple, ground, random.Random(1))
    assert not arena.summon(temple, ground, random.Random(1))


# --- summoning lays that biome's own ground -------------------------------


def test_the_floor_becomes_the_biome():
    # The wasteland is the exception and has its own test: its terrain is the
    # absence of any, so an empty floor there is the right answer.
    for index, biome in enumerate(biomes.RING_BIOMES):
        if biome is biomes.WASTELAND:
            continue
        temple = _ready(index)
        ground = _ground()
        arena.summon(temple, ground, random.Random(2))
        assert ground.sealed
        assert ground.what_was_laid(), biome.key


def test_only_that_biome_s_ground_is_laid():
    # The burnt forest's arena has lava and no ice; the snowfield's the other
    # way about. Fought on a neighbour's floor, a gimmick would stop matching
    # the place it came from.
    burnt = _ready(biomes.RING_BIOMES.index(biomes.BURNT_FOREST))
    ground = _ground()
    arena.summon(burnt, ground, random.Random(2))
    assert ground.lava and not ground.ice and not ground.chasms and not ground.mires


def test_the_snowfield_lays_ice_and_nothing_else():
    snow = _ready(biomes.RING_BIOMES.index(biomes.SNOWFIELD))
    ground = _ground()
    arena.summon(snow, ground, random.Random(2))
    assert ground.ice and not ground.lava and not ground.chasms and not ground.mires


def test_the_wasteland_lays_nothing_at_all():
    # Its terrain IS the absence of any, and an empty floor is the truest
    # reading of nowhere to hide.
    waste = _ready(biomes.RING_BIOMES.index(biomes.WASTELAND))
    ground = _ground()
    arena.summon(waste, ground, random.Random(2))
    assert ground.sealed
    assert not ground.what_was_laid()


def test_everything_laid_is_inside_the_room():
    for index in range(len(biomes.RING_BIOMES)):
        temple = _ready(index)
        ground = _ground()
        arena.summon(temple, ground, random.Random(4))
        for spot in ground.what_was_laid():
            assert temple.pos.distance_to(spot.pos) < temple.radius


def test_nothing_is_laid_over_the_altar():
    # Walking back to a plinth under a lava pool would be a cruel joke.
    for index in range(len(biomes.RING_BIOMES)):
        temple = _ready(index)
        ground = _ground()
        arena.summon(temple, ground, random.Random(5))
        for spot in ground.what_was_laid():
            assert spot.pos.distance_to(temple.layout.altar) > spot.radius


def test_the_floor_is_empty_before_anyone_calls():
    _ready()  # walked in, looked around, called nothing
    ground = _ground()
    assert not ground.sealed
    assert not ground.what_was_laid()


# --- the door shuts -------------------------------------------------------


def test_a_sealed_room_holds_you_in():
    temple = _ready()
    ground = _ground()
    arena.summon(temple, ground, random.Random(1))
    out = temple.pos + pygame.Vector2(temple.radius * 2, 0)
    at = pygame.Vector2(out)
    arena.hold(at, temple, ground)
    assert temple.contains(at)


def test_an_open_room_lets_you_walk_out():
    temple = _ready()
    ground = _ground()
    out = temple.pos + pygame.Vector2(temple.radius * 2, 0)
    at = pygame.Vector2(out)
    arena.hold(at, temple, ground)
    assert at == out


# --- and opens again ------------------------------------------------------


def test_releasing_clears_the_floor_and_the_door():
    temple = _ready()
    ground = _ground()
    arena.summon(temple, ground, random.Random(1))
    arena.release(ground)
    assert not ground.sealed
    assert not ground.what_was_laid()


def test_the_altar_answers_again_after_a_loss():
    # A defeat is a second attempt, not a long walk. The guard stays down.
    temple = _ready()
    ground = _ground()
    arena.summon(temple, ground, random.Random(1))
    arena.release(ground)
    assert arena.why_not(temple) is None
    assert arena.summon(temple, ground, random.Random(1))


def test_a_won_fight_closes_the_altar_for_good():
    temple = _ready()
    ground = _ground()
    arena.summon(temple, ground, random.Random(1))
    temple.boss_killed = True
    arena.release(ground)
    assert arena.why_not(temple) is not None


# --- the world outside is left alone --------------------------------------


def test_an_arena_keeps_its_own_ground():
    # Pushed into the world's lists, a dozen summons would quietly grow the
    # map a dozen lava pools that never cool.
    from game.world import lava

    world_lava = lava.place(WORLD, random.Random(7))
    before = len(world_lava)
    temple = _ready(biomes.RING_BIOMES.index(biomes.BURNT_FOREST))
    ground = _ground()
    arena.summon(temple, ground, random.Random(1))
    assert len(world_lava) == before


def test_the_same_seed_lays_the_same_floor():
    def floor(seed: int):
        temple = _ready()
        ground = _ground()
        arena.summon(temple, ground, random.Random(seed))
        return [(s.pos, s.radius) for s in ground.what_was_laid()]

    assert floor(3) == floor(3)
    assert floor(3) != floor(4)
