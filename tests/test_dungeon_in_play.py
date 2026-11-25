"""Walking a temple: doors, golems, chests, the key, and the thing asleep.

``test_dungeon`` checks the shape of the building. This is the part where
somebody is actually standing in it -- the doors that will not open while
something is swinging, the chest that will not either, and the boss that is
lying in the middle of the last room until a hand is laid on it.
"""

import pygame

from game import config
from game.items.item_kinds import CORE_SIGIL
from game.scenes.play import PlayScene
from game.world import dungeon, rooms


def _outside(scene: PlayScene, temple) -> None:
    scene.player.pos.update(temple.pos + pygame.Vector2(temple.radius * 3, 0))


def _walk_in(index: int = 0) -> tuple[PlayScene, object]:
    scene = PlayScene()
    scene.core.ignite()
    temple = scene.temples[index]
    scene.player.pos.update(temple.pos + pygame.Vector2(temple.radius * 0.6, 0))
    scene.update(config.FIXED_DT)
    return scene, temple


def _guards(scene: PlayScene) -> list:
    return [e for e in scene.enemies if e.guarding]


def _clear_the_room(scene: PlayScene) -> None:
    for guard in _guards(scene):
        guard.damage(guard.hp)
    scene.enemies = [e for e in scene.enemies if not e.is_dead]
    scene.update(config.FIXED_DT)


def _step_into(scene: PlayScene, temple, way: str) -> None:
    """Stand in a doorway and let the scene notice."""
    scene.player.pos.update(pygame.Vector2(rooms.doorway(temple.pos, way).center))
    scene.update(config.FIXED_DT)


# --- coming in and going out ---------------------------------------------


def test_walking_into_a_temple_puts_you_inside_it():
    scene, temple = _walk_in()
    assert scene.inside is temple
    assert temple.inside
    assert rooms.inner(temple.pos).collidepoint(scene.player.pos.x, scene.player.pos.y)


def test_you_arrive_at_the_door_you_came_in_by():
    scene, temple = _walk_in()
    assert scene.player.pos.y > temple.pos.y  # the south wall


def test_the_first_room_is_the_start_room():
    scene, temple = _walk_in()
    assert temple.interior().room.kind is dungeon.START


def test_the_doorway_is_empty():
    scene, temple = _walk_in()
    assert not _guards(scene)


def test_walking_back_out_of_the_first_room_leaves_the_temple():
    scene, temple = _walk_in()
    _step_into(scene, temple, dungeon.SOUTH)
    assert scene.inside is None
    assert not temple.inside
    assert not temple.contains(scene.player.pos)


def test_the_building_remembers_where_you_were():
    scene, temple = _walk_in()
    place = temple.interior()
    way = next(iter(place.room.doors))
    _step_into(scene, temple, way)
    deeper = place.at
    assert deeper != 0
    _outside(scene, temple)
    scene.update(config.FIXED_DT)
    assert place.at == deeper


# --- the doors ------------------------------------------------------------


def test_a_room_with_golems_in_it_stands_them_up():
    scene, temple = _walk_in()
    place = temple.interior()
    _step_into(scene, temple, next(iter(place.room.doors)))
    assert len(_guards(scene)) == place.room.standing
    assert _guards(scene)


def test_the_golems_are_that_biome_s_own():
    scene, temple = _walk_in()
    place = temple.interior()
    _step_into(scene, temple, next(iter(place.room.doors)))
    for guard in _guards(scene):
        assert guard.kind.biome is temple.biome


def test_the_doors_hold_while_anything_is_standing():
    scene, temple = _walk_in()
    place = temple.interior()
    _step_into(scene, temple, next(iter(place.room.doors)))
    was = place.at
    _step_into(scene, temple, dungeon.SOUTH)
    assert place.at == was  # not even the way back


def test_clearing_the_room_opens_them():
    scene, temple = _walk_in()
    place = temple.interior()
    _step_into(scene, temple, next(iter(place.room.doors)))
    was = place.at
    _clear_the_room(scene)
    _step_into(scene, temple, dungeon.SOUTH)
    assert place.at != was


def test_a_held_door_says_why():
    scene, temple = _walk_in()
    place = temple.interior()
    _step_into(scene, temple, next(iter(place.room.doors)))
    _step_into(scene, temple, dungeon.SOUTH)
    assert scene.note


def test_a_blank_wall_is_not_a_door():
    scene, temple = _walk_in()
    place = temple.interior()
    blank = next(
        (w for w in (dungeon.NORTH, dungeon.EAST, dungeon.WEST) if w not in place.room.doors),
        None,
    )
    if blank is None:
        return
    _step_into(scene, temple, blank)
    assert place.at == 0
    assert scene.inside is temple


def test_the_golems_do_not_follow_you_through_the_door():
    scene, temple = _walk_in()
    place = temple.interior()
    _step_into(scene, temple, next(iter(place.room.doors)))
    _clear_the_room(scene)
    _step_into(scene, temple, dungeon.SOUTH)
    assert place.at == 0
    assert not _guards(scene)


def test_a_body_cannot_walk_out_through_a_wall():
    scene, temple = _walk_in()
    scene.player.pos.update(temple.pos + pygame.Vector2(9000, 9000))
    scene.update(config.FIXED_DT)
    assert rooms.inner(temple.pos).collidepoint(scene.player.pos.x, scene.player.pos.y)


# --- chests ---------------------------------------------------------------


def _walk_to(scene: PlayScene, temple, target: int) -> None:
    """Clear a path to one room and stand in it."""
    place = temple.interior()
    route: list[int] = []
    here: int | None = target
    while here is not None:
        route.append(here)
        here = place.rooms[here].back
    for step in reversed(route[:-1]):
        _clear_the_room(scene)
        place.key_spent = True  # the boss's door is not what is under test
        way = next(w for w, t in place.room.doors.items() if t == step)
        _step_into(scene, temple, way)


def test_a_chest_will_not_open_while_the_room_is_guarded():
    scene, temple = _walk_in()
    place = temple.interior()
    chest = next(r for r in place.rooms if r.kind is dungeon.CHEST)
    _walk_to(scene, temple, chest.index)
    scene.player.pos.update(temple.pos)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    scene.update(config.FIXED_DT)
    assert not chest.chest_opened


def test_clearing_the_room_opens_the_chest():
    scene, temple = _walk_in()
    place = temple.interior()
    chest = next(r for r in place.rooms if r.kind is dungeon.CHEST)
    _walk_to(scene, temple, chest.index)
    _clear_the_room(scene)
    scene.player.pos.update(temple.pos)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    scene.update(config.FIXED_DT)
    assert chest.chest_opened


def test_a_chest_hands_over_something():
    scene, temple = _walk_in()
    place = temple.interior()
    chest = next(r for r in place.rooms if r.kind is dungeon.CHEST)
    _walk_to(scene, temple, chest.index)
    _clear_the_room(scene)
    learned = len(scene.grimoire.learned)
    carried = sum(getattr(s, "count", 0) for s in scene.hotbar.slots if s is not None)
    scene.player.pos.update(temple.pos)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    scene.update(config.FIXED_DT)
    after = sum(getattr(s, "count", 0) for s in scene.hotbar.slots if s is not None)
    assert after > carried or len(scene.grimoire.learned) > learned


def test_the_chest_with_the_key_hands_the_key_over():
    scene, temple = _walk_in()
    place = temple.interior()
    holder = next(r for r in place.rooms if r.has_key)
    _walk_to(scene, temple, holder.index)
    _clear_the_room(scene)
    scene.player.pos.update(temple.pos)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    scene.update(config.FIXED_DT)
    assert place.key_found


# --- the thing asleep -----------------------------------------------------


def test_the_boss_room_is_shut_without_the_key():
    scene, temple = _walk_in()
    place = temple.interior()
    boss_room = place.boss_room
    assert boss_room.back is not None
    _walk_to(scene, temple, boss_room.back)
    _clear_the_room(scene)
    place.key_found = place.key_spent = False
    way = next(w for w, t in place.room.doors.items() if t == boss_room.index)
    was = place.at
    _step_into(scene, temple, way)
    assert place.at == was


def test_the_key_opens_the_boss_room():
    scene, temple = _walk_in()
    place = temple.interior()
    boss_room = place.boss_room
    assert boss_room.back is not None
    _walk_to(scene, temple, boss_room.back)
    _clear_the_room(scene)
    place.key_found, place.key_spent = True, False
    way = next(w for w, t in place.room.doors.items() if t == boss_room.index)
    _step_into(scene, temple, way)
    assert place.at == boss_room.index


def test_the_boss_is_asleep_until_it_is_touched():
    scene, temple = _walk_in()
    place = temple.interior()
    place.at = place.boss_room.index
    scene.player.pos.update(temple.pos + pygame.Vector2(600, 0))
    scene.update(config.FIXED_DT)
    assert scene.boss is None
    assert not place.boss_room.boss_woken


def test_laying_a_hand_on_it_wakes_it():
    scene, temple = _walk_in()
    place = temple.interior()
    place.at = place.boss_room.index
    scene.player.pos.update(temple.pos)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    scene.update(config.FIXED_DT)
    assert scene.boss is not None
    assert place.boss_room.boss_woken
    assert scene.arena.sealed


def test_waking_it_shuts_the_door_on_you():
    scene, temple = _walk_in()
    place = temple.interior()
    place.at = place.boss_room.index
    scene.player.pos.update(temple.pos)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    scene.update(config.FIXED_DT)
    scene.player.pos.update(temple.pos + pygame.Vector2(9000, 0))
    scene.update(config.FIXED_DT)
    assert temple.pos.distance_to(scene.player.pos) <= rooms.arena_radius() + 1


def test_it_only_wakes_once():
    scene, temple = _walk_in()
    place = temple.interior()
    place.at = place.boss_room.index
    scene.player.pos.update(temple.pos)
    for _ in range(3):
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        scene.update(config.FIXED_DT)
    assert scene.boss is not None


def test_killing_it_opens_the_door_and_leaves_a_sigil():
    scene, temple = _walk_in()
    place = temple.interior()
    place.at = place.boss_room.index
    scene.player.pos.update(temple.pos)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    scene.update(config.FIXED_DT)
    assert scene.boss is not None
    scene.boss.damage(scene.boss.hp)
    scene.update(config.FIXED_DT)
    assert scene.boss is None
    assert not scene.arena.sealed
    assert temple.boss_killed
    assert scene._carried(CORE_SIGIL) >= 1
