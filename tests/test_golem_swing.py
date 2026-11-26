"""A golem stops and swings instead of grinding you down by standing there.

Contact damage was a tax: walk into one, or let one walk into you, and health
drained for as long as the two circles overlapped. Nothing was announced and
nothing could be dodged -- the only answer was to not be there, which is the
same answer as the one before it and the one after.

Now it walks until it is close enough, STOPS, winds up where you can see it,
and swings. Step out while it winds and the swing lands on nothing. The sum
of what it deals over a cycle is about what the contact drain was, so the
fight is no softer; it is answerable.
"""

import pygame

from game import config
from game.entities.core import Core
from game.entities.enemy import BIOME_GOLEMS, PLAIN_GOLEM, Golem, swing
from game.entities.player import Player
from game.systems import combat
from game.world.map import WorldMap

WORLD = WorldMap()
HOME = pygame.Vector2(WORLD.center)


def _player(at=None) -> Player:
    return Player(pos=pygame.Vector2(at or HOME))


def _core() -> Core:
    core = Core(pos=pygame.Vector2(HOME) + pygame.Vector2(9000, 0))
    core.ignite()
    return core


def _hunter(at=None) -> Golem:
    """One that comes for the player rather than the core."""
    from dataclasses import replace

    from game.entities.enemy import TARGET_PLAYER

    kind = replace(PLAIN_GOLEM, target=TARGET_PLAYER)
    return Golem(pos=pygame.Vector2(at or (HOME + pygame.Vector2(400, 0))), kind=kind)


def _tick(enemies, player, core, seconds):
    for _ in range(int(seconds / config.FIXED_DT)):
        combat.update_enemies(config.FIXED_DT, enemies, player, WORLD, core, raid=True)


# --- walking up to it -----------------------------------------------------


def test_it_walks_while_you_are_far_off():
    golem = _hunter()
    player = _player()
    was = golem.pos.distance_to(player.pos)
    _tick([golem], player, _core(), 0.3)
    assert golem.pos.distance_to(player.pos) < was
    assert golem.phase is swing.WALK


def test_it_stops_when_it_is_close_enough():
    golem = _hunter()
    player = _player()
    _tick([golem], player, _core(), 4.0)
    assert golem.phase is not swing.WALK
    # Measured body to body, which is how the golem measures it.
    gap = golem.pos.distance_to(player.pos) - player.radius
    assert gap <= golem.reach + 1


def test_it_does_not_keep_shuffling_once_it_has_stopped():
    golem = _hunter()
    player = _player()
    _tick([golem], player, _core(), 4.0)
    where = pygame.Vector2(golem.pos)
    _tick([golem], player, _core(), config.GOLEM_WIND / 2)
    assert golem.pos == where


# --- the swing ------------------------------------------------------------


def test_standing_there_costs_nothing_until_it_swings():
    golem = _hunter(HOME + pygame.Vector2(30, 0))
    player = _player()
    _tick([golem], player, _core(), config.GOLEM_WIND * 0.5)
    assert player.hp == player.max_hp


def test_the_swing_lands():
    golem = _hunter(HOME + pygame.Vector2(30, 0))
    player = _player()
    _tick([golem], player, _core(), config.GOLEM_WIND + 0.1)
    assert player.hp < player.max_hp


def test_one_swing_is_one_hit():
    golem = _hunter(HOME + pygame.Vector2(30, 0))
    player = _player()
    _tick([golem], player, _core(), config.GOLEM_WIND + 0.1)
    once = player.max_hp - player.hp
    _tick([golem], player, _core(), config.GOLEM_REST * 0.5)
    assert player.max_hp - player.hp == once


def test_stepping_out_while_it_winds_dodges_it():
    # The whole point. The wind-up is long enough to leave, and leaving works.
    golem = _hunter(HOME + pygame.Vector2(30, 0))
    player = _player()
    _tick([golem], player, _core(), config.GOLEM_WIND * 0.5)
    player.pos.update(HOME + pygame.Vector2(900, 0))
    _tick([golem], player, _core(), config.GOLEM_WIND)
    assert player.hp == player.max_hp


def test_it_swings_again_after_a_rest():
    golem = _hunter(HOME + pygame.Vector2(30, 0))
    player = _player()
    _tick([golem], player, _core(), config.GOLEM_WIND + 0.1)
    once = player.max_hp - player.hp
    _tick([golem], player, _core(), config.GOLEM_REST + config.GOLEM_WIND + 0.1)
    assert player.max_hp - player.hp > once


def test_a_whole_cycle_costs_about_what_standing_in_one_used_to():
    # Not softer -- answerable. A player who never moves pays the old rate.
    cycle = config.GOLEM_WIND + config.GOLEM_REST
    assert 0.6 < (PLAIN_GOLEM.hit / cycle) / PLAIN_GOLEM.contact_dps < 1.4


def test_a_biome_golem_hits_harder_than_a_plain_one():
    assert BIOME_GOLEMS[-1].hit > PLAIN_GOLEM.hit


def test_i_frames_still_turn_a_swing_aside():
    golem = _hunter(HOME + pygame.Vector2(30, 0))
    player = _player()
    player.iframe_timer = 9.0
    _tick([golem], player, _core(), config.GOLEM_WIND + 0.1)
    assert player.hp == player.max_hp


def test_a_corpse_is_not_swung_at():
    golem = _hunter(HOME + pygame.Vector2(30, 0))
    player = _player()
    player.hp = 0
    _tick([golem], player, _core(), config.GOLEM_WIND + 0.1)
    assert player.hp == 0


# --- the core gets the same treatment ------------------------------------


def test_one_marching_on_the_core_stops_and_swings_at_it():
    core = Core(pos=pygame.Vector2(HOME))
    core.ignite()
    golem = Golem(pos=pygame.Vector2(HOME) + pygame.Vector2(80, 0))
    player = _player(HOME + pygame.Vector2(9000, 0))
    before = core.hp
    _tick([golem], player, core, config.GOLEM_WIND + 0.2)
    assert core.hp < before
    assert golem.phase is not swing.WALK


def test_an_unlit_core_is_not_worth_swinging_at():
    core = Core(pos=pygame.Vector2(HOME))
    golem = Golem(pos=pygame.Vector2(HOME) + pygame.Vector2(80, 0))
    _tick([golem], _player(HOME + pygame.Vector2(9000, 0)), core, 2.0)
    assert core.hp == 0  # never lit, never hurt


# --- what the player is shown --------------------------------------------


def test_a_winding_golem_says_how_far_through_it_is():
    # The red shape on screen is drawn from this: it closes as the wind runs
    # out, so the player reads WHEN as well as where.
    golem = _hunter(HOME + pygame.Vector2(30, 0))
    player = _player()
    _tick([golem], player, _core(), config.GOLEM_WIND * 0.5)
    assert golem.phase is swing.WIND
    assert 0.0 < golem.wound < 1.0


def test_a_landed_swing_flashes():
    golem = _hunter(HOME + pygame.Vector2(30, 0))
    player = _player()
    _tick([golem], player, _core(), config.GOLEM_WIND + config.FIXED_DT * 3)
    assert golem.flash > 0


def test_the_flash_goes_out():
    golem = _hunter(HOME + pygame.Vector2(30, 0))
    player = _player()
    _tick([golem], player, _core(), config.GOLEM_WIND + 0.1)
    _tick([golem], player, _core(), config.SWING_FLASH + 0.1)
    assert golem.flash == 0


# --- the red shapes on screen --------------------------------------------


def _drawn(scene) -> pygame.Surface:
    surface = pygame.Surface(config.SCREEN_SIZE)
    scene.draw(surface)
    return surface


def _has_red(surface: pygame.Surface) -> bool:
    # Exactly the hitbox colour. A golem is drawn in a red of its own, close
    # enough that a tolerance would call every golem on screen a hitbox.
    red = config.HITBOX_COLOR
    return any(
        surface.get_at((x, y))[:3] == red
        for x in range(0, surface.get_width(), 2)
        for y in range(0, surface.get_height(), 2)
    )


def test_a_winding_golem_is_drawn_in_red():
    from game.scenes.play import PlayScene

    scene = PlayScene()
    golem = _hunter(scene.player.pos + pygame.Vector2(30, 0))
    golem.phase, golem.beat = swing.WIND, config.GOLEM_WIND / 2
    scene.enemies.append(golem)
    scene.camera.center_on(scene.player.pos)
    assert _has_red(_drawn(scene))


def test_a_walking_golem_draws_no_box():
    # Only what is about to decide something. A ring round every golem on
    # screen is a screen nobody reads.
    from game.scenes.play import PlayScene

    scene = PlayScene()
    scene.enemies.clear()
    golem = _hunter(scene.player.pos + pygame.Vector2(300, 0))
    scene.enemies.append(golem)
    scene.camera.center_on(scene.player.pos)
    assert golem.phase is swing.WALK
    assert not _has_red(_drawn(scene))


def test_the_tool_in_hand_shows_its_reach_while_it_is_used():
    from game.items.tools import WeaponTool
    from game.scenes.play import PlayScene

    scene = PlayScene()
    scene.enemies.clear()
    scene.hotbar.slots[0] = WeaponTool()
    scene.hotbar.select(0)
    scene.facing.update(1, 0)
    scene.camera.center_on(scene.player.pos)
    assert not _has_red(_drawn(scene))
    scene._swing_left = config.SWING_FLASH
    assert _has_red(_drawn(scene))
