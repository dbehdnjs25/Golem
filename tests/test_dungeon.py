"""The inside of a temple.

A temple was one circle with an altar in it. It is a building now, and the
shape of that building is doing work: a TREE, branches and no way round. The
loop is what is deliberately missing -- with one in it a player could walk
past a room full of golems and come at the far side from behind, and "the
doors do not open until the room is clear" would be a suggestion rather than
a rule.
"""

import random

from game import config
from game.world import dungeon
from game.world.dungeon import BOSS, CHEST, EAST, NORTH, PLAIN, SOUTH, START, WEST, Dungeon, Room


def _built(salt: int = 7) -> Dungeon:
    return dungeon.build(salt)


def _every_salt(n: int = 40):
    return [dungeon.build(salt) for salt in range(1, n + 1)]


# --- the shape ------------------------------------------------------------


def test_a_temple_has_at_least_thirteen_rooms():
    for place in _every_salt():
        assert len(place.rooms) >= config.DUNGEON_ROOMS


def test_the_boss_is_at_least_five_rooms_in():
    for place in _every_salt():
        assert place.depth_of_boss >= config.DUNGEON_BOSS_DEPTH


def test_there_is_exactly_one_boss_room():
    for place in _every_salt():
        assert sum(1 for room in place.rooms if room.kind is BOSS) == 1


def test_the_start_room_has_at_least_one_door():
    for place in _every_salt():
        assert place.rooms[0].doors


def test_the_start_room_is_the_only_one_with_no_way_back():
    for place in _every_salt():
        without = [room for room in place.rooms if room.back is None]
        assert [room.index for room in without] == [0]


def test_it_is_a_tree_and_not_a_maze():
    # Every room but the entrance has exactly one way back, and the doors
    # going on never point at a room that has already been reached. That is
    # the whole of "no way round".
    for place in _every_salt():
        seen = {0}
        for room in place.rooms:
            for target in room.doors.values():
                assert target not in seen or target == room.index
                seen.add(target)
        assert len(seen) == len(place.rooms)


def test_every_room_is_reachable_from_the_door():
    for place in _every_salt():
        found, edge = {0}, [0]
        while edge:
            here = edge.pop()
            for target in place.rooms[here].doors.values():
                if target not in found:
                    found.add(target)
                    edge.append(target)
        assert len(found) == len(place.rooms)


def test_a_door_leads_back_where_it_came_from():
    for place in _every_salt(10):
        for room in place.rooms:
            for target in room.doors.values():
                assert place.rooms[target].back == room.index


def test_nothing_is_built_past_the_boss():
    # A door out of the boss's room would let a player walk round the fight.
    for place in _every_salt():
        assert place.boss_room.is_dead_end


def test_the_same_temple_is_drawn_the_same_way_twice():
    one, two = dungeon.build(11), dungeon.build(11)
    assert [(r.kind, r.depth, r.golems) for r in one.rooms] == [
        (r.kind, r.depth, r.golems) for r in two.rooms
    ]


def test_two_temples_are_not_the_same_place():
    one, two = dungeon.build(3), dungeon.build(4)
    assert [r.kind for r in one.rooms] != [r.kind for r in two.rooms] or [
        r.doors for r in one.rooms
    ] != [r.doors for r in two.rooms]


# --- what is in them ------------------------------------------------------


def test_the_doorway_is_safe():
    # Walking in to find something already swinging gives the player no moment
    # to read the room.
    for place in _every_salt():
        assert place.rooms[0].golems == 0


def test_a_chest_room_is_guarded_by_at_least_three():
    for place in _every_salt():
        for room in place.rooms:
            if room.kind is CHEST:
                assert room.golems >= config.DUNGEON_CHEST_GUARDS


def test_ordinary_rooms_have_somebody_in_them():
    for place in _every_salt():
        for room in place.rooms:
            if room.kind is PLAIN:
                assert room.golems >= config.DUNGEON_GUARDS_MIN


def test_every_dead_end_is_worth_walking_to():
    # A branch that ends in an empty room is a longer way of being lost.
    for place in _every_salt():
        for room in place.rooms:
            if room.is_dead_end and room.kind is not BOSS:
                assert room.kind is CHEST


def test_exactly_one_chest_holds_the_key():
    for place in _every_salt():
        assert sum(1 for room in place.rooms if room.has_key) == 1


def test_the_key_is_never_behind_the_door_it_opens():
    # It is in a chest, and no chest is past the boss -- nothing is.
    for place in _every_salt():
        holder = next(room for room in place.rooms if room.has_key)
        assert holder.kind is CHEST


# --- the doors ------------------------------------------------------------


def test_a_room_with_something_standing_holds_every_door():
    place = _built()
    place.walk(next(iter(place.rooms[0].doors)))
    here = place.room
    assert here.standing > 0
    for way in (NORTH, EAST, WEST, SOUTH):
        if place.through(way) is not None:
            assert place.locked(way) is not None


def test_clearing_the_room_opens_them_again():
    place = _built()
    way = next(iter(place.rooms[0].doors))
    place.walk(way)
    while not place.room.cleared:
        place.kill_one()
    assert place.locked(SOUTH) is None
    assert place.walk(SOUTH)
    assert place.at == 0


def test_an_empty_wall_is_not_a_locked_door():
    place = _built()
    blank = next(way for way in (NORTH, EAST, WEST) if way not in place.rooms[0].doors)
    assert place.through(blank) is None
    assert not place.walk(blank)


def test_the_way_back_is_the_way_you_came():
    place = _built()
    way = next(iter(place.rooms[0].doors))
    place.walk(way)
    while not place.room.cleared:
        place.kill_one()
    place.walk(SOUTH)
    assert place.at == 0


def test_opposite_walls_face_each_other():
    assert Dungeon.opposite(NORTH) is SOUTH
    assert Dungeon.opposite(SOUTH) is NORTH
    assert Dungeon.opposite(EAST) is WEST
    assert Dungeon.opposite(WEST) is EAST


# --- the key --------------------------------------------------------------


def _clear_to(place: Dungeon, target: int) -> None:
    """Walk to a room, clearing everything on the way."""
    route: list[int] = []
    here: int | None = target
    while here is not None:
        route.append(here)
        here = place.rooms[here].back
    for step in reversed(route[:-1]):
        while not place.room.cleared:
            place.kill_one()
        way = next(w for w, t in place.room.doors.items() if t == step)
        place.key_found = True  # so the boss door is not what is under test
        place.walk(way)


def test_the_boss_door_will_not_open_without_the_key():
    place = _built()
    boss = place.boss_room.index
    before = place.rooms[boss].back
    assert before is not None
    _clear_to(place, before)
    place.key_found = place.key_spent = False
    while not place.room.cleared:
        place.kill_one()
    way = next(w for w, t in place.room.doors.items() if t == boss)
    assert place.locked(way) is not None
    assert not place.walk(way)


def test_the_key_opens_it():
    place = _built()
    boss = place.boss_room.index
    before = place.rooms[boss].back
    assert before is not None
    _clear_to(place, before)
    place.key_found, place.key_spent = True, False
    while not place.room.cleared:
        place.kill_one()
    way = next(w for w, t in place.room.doors.items() if t == boss)
    assert place.locked(way) is None
    assert place.walk(way)
    assert place.at == boss


def test_the_key_is_turned_once_and_gone():
    place = _built()
    boss = place.boss_room.index
    before = place.rooms[boss].back
    assert before is not None
    _clear_to(place, before)
    place.key_found, place.key_spent = True, False
    while not place.room.cleared:
        place.kill_one()
    way = next(w for w, t in place.room.doors.items() if t == boss)
    place.walk(way)
    assert not place.key_found
    assert place.key_spent


def test_a_turned_door_stays_open():
    place = _built()
    place.key_spent = True
    boss = place.boss_room.index
    before = place.rooms[boss].back
    assert before is not None
    _clear_to(place, before)
    while not place.room.cleared:
        place.kill_one()
    way = next(w for w, t in place.room.doors.items() if t == boss)
    assert place.locked(way) is None


# --- chests ---------------------------------------------------------------


def test_a_chest_will_not_open_while_the_room_is_guarded():
    place = Dungeon(rooms=[Room(index=0, kind=CHEST, depth=0, golems=3, standing=3)])
    assert not place.open_chest()
    assert not place.room.chest_opened


def test_clearing_the_room_opens_the_chest():
    place = Dungeon(rooms=[Room(index=0, kind=CHEST, depth=0, golems=3, standing=0)])
    assert place.open_chest()
    assert place.room.chest_opened


def test_a_chest_opens_once():
    place = Dungeon(rooms=[Room(index=0, kind=CHEST, depth=0)])
    assert place.open_chest()
    assert not place.open_chest()


def test_a_room_with_no_chest_has_nothing_to_open():
    place = Dungeon(rooms=[Room(index=0, kind=PLAIN, depth=0)])
    assert not place.open_chest()


def test_the_key_comes_out_of_the_chest_that_holds_it():
    place = Dungeon(rooms=[Room(index=0, kind=CHEST, depth=0, has_key=True)])
    assert not place.key_found
    place.open_chest()
    assert place.key_found


def test_an_ordinary_chest_holds_no_key():
    place = Dungeon(rooms=[Room(index=0, kind=CHEST, depth=0)])
    place.open_chest()
    assert not place.key_found


# --- killing things -------------------------------------------------------


def test_the_count_comes_down_as_they_fall():
    place = Dungeon(rooms=[Room(index=0, kind=PLAIN, depth=0, golems=3, standing=3)])
    place.kill_one()
    assert place.room.standing == 2
    assert not place.room.cleared
    place.kill_one()
    place.kill_one()
    assert place.room.cleared


def test_the_count_never_goes_below_nothing():
    place = Dungeon(rooms=[Room(index=0, kind=PLAIN, depth=0, golems=1, standing=1)])
    for _ in range(5):
        place.kill_one()
    assert place.room.standing == 0


def test_an_empty_room_is_clear_from_the_start():
    place = Dungeon(rooms=[Room(index=0, kind=START, depth=0)])
    assert place.room.cleared


# --- the boss ------------------------------------------------------------


def test_the_boss_sleeps_until_it_is_woken():
    place = _built()
    assert not place.boss_room.boss_woken


def test_the_shape_holds_for_a_hand_picked_rng():
    # Not a seed from the salt: the generator has to work for any dice.
    place = dungeon.build(0, rng=random.Random(99))
    assert len(place.rooms) >= config.DUNGEON_ROOMS
    assert place.depth_of_boss >= config.DUNGEON_BOSS_DEPTH
    assert place.boss_room.is_dead_end
