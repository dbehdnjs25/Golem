"""The ring around the altar, and what knocking it down earns.

Until now the guards were scenery with a health bar. They stood up when the
player walked in, and nothing anywhere set ``guards_down`` -- so the altar
answered "수호 골렘이 제단을 지키고 있다" for the rest of the run and the five
bosses were unreachable in an ordinary game.

So this is the door to all of it: clear the ring, and the altar answers. And
the ring is that biome's own golem rather than a plain one, which makes a
temple the first look at what the raids will later be made of.
"""

import pygame

from game import config
from game.entities.enemy import BIOME_GOLEMS, PLAIN_GOLEM
from game.scenes.play import PlayScene
from game.systems import arena
from game.world.biomes import RING_BIOMES


def _walk_into(scene: PlayScene, temple):
    """Put the player at the temple's edge and let the scene notice."""
    scene.player.pos.update(temple.pos + pygame.Vector2(temple.radius * 0.8, 0))
    scene._visit_temples()
    return temple


def _first_temple(scene: PlayScene):
    return scene.temples[0]


def _guards(scene: PlayScene):
    return [e for e in scene.enemies if e.guarding]


# --- who is standing there ------------------------------------------------


def test_walking_in_stands_the_ring_up():
    scene = PlayScene()
    temple = _walk_into(scene, _first_temple(scene))
    assert temple.layout is not None
    assert len(_guards(scene)) == len(temple.layout.guards)
    assert _guards(scene)


def test_the_ring_is_that_biome_s_own_golem():
    # A temple is the first look at what the raids will later throw at you.
    scene = PlayScene()
    temple = _walk_into(scene, _first_temple(scene))
    for guard in _guards(scene):
        assert guard.kind.biome is temple.biome
        assert guard.kind is not PLAIN_GOLEM


def test_every_ring_biome_has_a_golem_to_stand_there():
    assert len(BIOME_GOLEMS) == len(RING_BIOMES)
    for biome in RING_BIOMES:
        assert any(k.biome is biome for k in BIOME_GOLEMS)


def test_a_guard_is_tougher_than_the_golem_it_is_made_from():
    scene = PlayScene()
    _walk_into(scene, _first_temple(scene))
    guard = _guards(scene)[0]
    assert guard.hp > guard.kind.hp


# --- what knocking it down earns ------------------------------------------


def test_the_altar_will_not_answer_while_one_still_stands():
    scene = PlayScene()
    temple = _walk_into(scene, _first_temple(scene))
    scene._visit_temples()
    assert not temple.guards_down
    assert arena.why_not(temple) is not None


def test_clearing_the_ring_opens_the_altar():
    scene = PlayScene()
    temple = _walk_into(scene, _first_temple(scene))
    scene.enemies = [e for e in scene.enemies if not e.guarding]  # all of them dead
    scene._visit_temples()
    assert temple.guards_down
    assert arena.why_not(temple) is None


def test_a_half_cleared_ring_is_not_a_cleared_ring():
    scene = PlayScene()
    temple = _walk_into(scene, _first_temple(scene))
    standing = _guards(scene)
    if len(standing) > 1:
        scene.enemies = [e for e in scene.enemies if e is standing[0]]
    scene._visit_temples()
    assert not temple.guards_down


def test_the_cleared_ring_leaves_the_room_empty():
    # The drawing has to forget them too, or the next visit shows a ring of
    # guards that are not there.
    scene = PlayScene()
    temple = _walk_into(scene, _first_temple(scene))
    scene.enemies = []
    scene._visit_temples()
    assert temple.layout is not None
    assert temple.layout.guards == ()


def test_a_cleared_ring_does_not_stand_up_again():
    scene = PlayScene()
    temple = _walk_into(scene, _first_temple(scene))
    scene.enemies = []
    scene._visit_temples()
    # Out of the door and back in, which is what redraws the room.
    scene.player.pos.update(temple.pos + pygame.Vector2(temple.radius * 3, 0))
    scene._visit_temples()
    _walk_into(scene, temple)
    assert not _guards(scene)
    assert temple.guards_down


def test_clearing_one_temple_does_not_open_another():
    scene = PlayScene()
    first, second = scene.temples[0], scene.temples[1]
    _walk_into(scene, first)
    scene.enemies = []
    scene._visit_temples()
    assert first.guards_down
    assert not second.guards_down


def test_walking_into_a_second_temple_stands_its_own_ring_up():
    scene = PlayScene()
    first, second = scene.temples[0], scene.temples[1]
    _walk_into(scene, first)
    scene.player.pos.update(second.pos + pygame.Vector2(second.radius * 0.8, 0))
    scene._visit_temples()
    assert _guards(scene)
    for guard in _guards(scene):
        assert guard.kind.biome is second.biome


def test_leaving_without_clearing_leaves_the_altar_shut():
    scene = PlayScene()
    temple = _walk_into(scene, _first_temple(scene))
    scene.player.pos.update(temple.pos + pygame.Vector2(temple.radius * 3, 0))
    scene._visit_temples()
    assert not temple.guards_down


def test_an_empty_room_nobody_is_standing_in_stays_shut():
    # Nothing is guarding anything while the player is outside, and that must
    # not read as a cleared ring.
    scene = PlayScene()
    temple = _first_temple(scene)
    scene.player.pos.update(temple.pos + pygame.Vector2(temple.radius * 5, 0))
    scene.enemies = []
    scene._visit_temples()
    assert not temple.guards_down


def test_the_player_is_told_the_altar_opened():
    scene = PlayScene()
    _walk_into(scene, _first_temple(scene))
    scene.enemies = []
    scene._visit_temples()
    assert scene.note
    assert scene.note_left > 0


def test_a_guard_is_a_golem_like_any_other():
    # It marches, it can be shot, it is removed when it dies. The flag only
    # says which temple's ring it belongs to.
    scene = PlayScene()
    _walk_into(scene, _first_temple(scene))
    guard = _guards(scene)[0]
    guard.damage(guard.hp)
    assert guard.is_dead


def test_the_guard_scale_still_multiplies_something_already_tough():
    # Guards used to be plain golems blown up 2.4x. They are biome golems now,
    # which already carry the ring's toughness, so the multiplier on top has to
    # come down or the first temple becomes the hardest thing in the game.
    assert config.GUARD_SCALE < 2.4
    first = BIOME_GOLEMS[0].hp * config.GUARD_SCALE
    assert first >= PLAIN_GOLEM.hp * 2.0  # still worth bringing a weapon to


# --- they belong to the room, not to the world ----------------------------


def test_walking_out_takes_the_ring_with_you():
    # They are golems, and a golem marches on the core. Left standing when the
    # player walks out, a ring raised by peering through the door escorted
    # itself home -- three biome golems, from a temple five biomes away, at a
    # core the player was not defending.
    scene = PlayScene()
    temple = _walk_into(scene, _first_temple(scene))
    assert _guards(scene)
    scene.player.pos.update(scene.core.pos)
    scene._visit_temples()
    assert not _guards(scene)
    assert not temple.inside


def test_the_ring_comes_back_when_you_do():
    scene = PlayScene()
    temple = _first_temple(scene)
    _walk_into(scene, temple)
    scene.player.pos.update(scene.core.pos)
    scene._visit_temples()
    _walk_into(scene, temple)
    assert _guards(scene)
    assert not temple.guards_down


def test_leaving_does_not_disturb_anything_else_on_the_field():
    from game.entities.enemy import Golem

    scene = PlayScene()
    temple = _first_temple(scene)
    _walk_into(scene, temple)
    wanderer = Golem(pos=pygame.Vector2(scene.core.pos))
    scene.enemies.append(wanderer)
    scene.player.pos.update(scene.core.pos)
    scene._visit_temples()
    assert wanderer in scene.enemies


def test_a_cleared_temple_has_nothing_to_take_away():
    scene = PlayScene()
    temple = _walk_into(scene, _first_temple(scene))
    scene.enemies = []
    scene._visit_temples()
    assert temple.guards_down
    scene.player.pos.update(scene.core.pos)
    scene._visit_temples()
    assert temple.guards_down
