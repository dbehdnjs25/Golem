import math
import random

import pygame

from game import config
from game.entities.temple import Temple
from game.world import biomes, temples
from game.world.map import WorldMap

WORLD = WorldMap(rotation=37.0)
SITES = WORLD.temple_sites(random.Random(3))


def _raised(seed: int = 1) -> list[Temple]:
    return temples.place(WORLD, SITES, random.Random(seed))


def _outside(temple: Temple) -> pygame.Vector2:
    """A point well clear of a temple, to walk in from."""
    return temple.pos + pygame.Vector2(temple.radius * 3, 0)


# --- one per biome, where the sites already are ---------------------------


def test_there_is_one_temple_per_ring_biome_in_order():
    raised = _raised()
    assert len(raised) == len(biomes.RING_BIOMES)
    for temple, biome in zip(raised, biomes.RING_BIOMES, strict=True):
        assert temple.biome is biome


def test_each_stands_on_the_site_the_map_chose():
    for temple, site in zip(_raised(), SITES, strict=True):
        assert temple.pos == site


def test_each_stands_in_its_own_biome():
    for temple in _raised():
        assert WORLD.biome_at(temple.pos) is temple.biome


# --- the inside, redrawn on every entry -----------------------------------


def test_a_fresh_temple_has_no_layout_until_it_is_entered():
    # Nothing to draw and nothing to walk into before anyone turns up.
    temple = _raised()[0]
    assert temple.layout is None


def test_entering_draws_an_inside():
    temple = _raised()[0]
    temple.enter(_outside(temple))
    assert temple.layout is not None
    assert temple.layout.chest is not None
    assert temple.layout.altar is not None


def test_entering_again_from_outside_draws_a_different_one():
    temple = _raised()[0]
    temple.enter(_outside(temple))
    first = temple.layout
    temple.leave()
    temple.enter(_outside(temple))
    assert temple.layout != first


def test_entering_twice_without_leaving_changes_nothing():
    # Otherwise a player could stand in the doorway and reroll the room until
    # the layout suited them.
    temple = _raised()[0]
    temple.enter(_outside(temple))
    first = temple.layout
    temple.enter(_outside(temple))
    assert temple.layout == first


def test_the_entrance_faces_whoever_is_arriving():
    # Put anywhere else, a wall appears where the player is standing.
    temple = _raised()[0]
    for degrees in (0, 90, 180, 270):
        radians = math.radians(degrees)
        from_pos = temple.pos + pygame.Vector2(math.cos(radians), math.sin(radians)) * (
            temple.radius * 3
        )
        temple.leave()
        temple.enter(from_pos)
        door = temple.layout.door
        assert (door - temple.pos).normalize().dot((from_pos - temple.pos).normalize()) > 0.9


def test_everything_inside_is_actually_inside():
    temple = _raised()[0]
    for _ in range(12):
        temple.leave()
        temple.enter(_outside(temple))
        inside = [temple.layout.chest, temple.layout.altar, *temple.layout.guards]
        for spot in inside:
            assert temple.pos.distance_to(spot) < temple.radius


def test_nothing_inside_sits_on_top_of_anything_else():
    temple = _raised()[0]
    for _ in range(12):
        temple.leave()
        temple.enter(_outside(temple))
        spots = [temple.layout.chest, temple.layout.altar, *temple.layout.guards]
        for i, a in enumerate(spots):
            for b in spots[i + 1 :]:
                assert a.distance_to(b) > config.TEMPLE_SPACING


def test_the_chest_is_nearer_the_door_than_the_altar():
    # Tasting the element has to come before being hit with it, and the altar
    # is the thing with the guard standing over it.
    temple = _raised()[0]
    for _ in range(12):
        temple.leave()
        temple.enter(_outside(temple))
        door = temple.layout.door
        assert door.distance_to(temple.layout.chest) < door.distance_to(temple.layout.altar)


def test_the_guards_stand_around_the_altar():
    temple = _raised()[0]
    temple.enter(_outside(temple))
    for guard in temple.layout.guards:
        assert guard.distance_to(temple.layout.altar) <= config.GUARD_RING


# --- what a visit remembers -----------------------------------------------


def test_an_opened_chest_simply_is_not_there_next_time():
    # Not an opened chest somewhere it has never been. The flag lives apart
    # from the geometry, so the geometry can say nothing at all.
    temple = _raised()[0]
    temple.enter(_outside(temple))
    temple.chest_opened = True
    temple.leave()
    temple.enter(_outside(temple))
    assert temple.layout.chest is None


def test_a_cleared_guard_does_not_stand_again():
    temple = _raised()[0]
    temple.enter(_outside(temple))
    temple.guards_down = True
    temple.leave()
    temple.enter(_outside(temple))
    assert temple.layout.guards == ()


def test_the_altar_is_always_there():
    # Even after the boss is dead: an empty plinth reads as a place that was
    # used, where a missing one reads as a room that was never finished.
    temple = _raised()[0]
    temple.boss_killed = True
    temple.enter(_outside(temple))
    assert temple.layout.altar is not None


# --- reproducible, and the world's dice are left alone --------------------


def test_the_same_world_seed_raises_the_same_temples():
    assert [(t.pos, t.radius, t.biome) for t in _raised(4)] == [
        (t.pos, t.radius, t.biome) for t in _raised(4)
    ]


def test_the_same_visit_of_the_same_temple_is_reproducible():
    a, b = _raised(4)[0], _raised(4)[0]
    for temple in (a, b):
        temple.enter(_outside(temple))
    assert a.layout == b.layout


def test_a_temple_does_not_spend_the_world_s_dice():
    # Drawing from the shared rng would shift every later roll, so one visit to
    # one temple would change the weather and the ore for the rest of the run.
    shared = random.Random(9)
    temple = temples.place(WORLD, SITES, random.Random(1))[0]
    before = [shared.random() for _ in range(5)]

    again = random.Random(9)
    temple.enter(_outside(temple))
    temple.leave()
    temple.enter(_outside(temple))
    after = [again.random() for _ in range(5)]
    assert before == after


def test_two_temples_in_one_world_do_not_draw_the_same_room():
    raised = _raised()
    for temple in raised:
        temple.enter(_outside(temple))
    layouts = [t.layout for t in raised]
    assert len({(round(layout.altar.x), round(layout.altar.y)) for layout in layouts}) > 1


# --- the door, and who is where -------------------------------------------


def test_contains_is_the_room_not_the_whole_site():
    temple = _raised()[0]
    assert temple.contains(temple.pos)
    assert not temple.contains(_outside(temple))


def test_walking_away_and_back_counts_as_two_visits():
    temple = _raised()[0]
    assert temple.visits == 0
    temple.enter(_outside(temple))
    assert temple.visits == 1
    temple.leave()
    temple.enter(_outside(temple))
    assert temple.visits == 2
