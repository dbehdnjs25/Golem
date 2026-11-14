"""The burnt forest's three, and the hazard shapes they are built from.

Three shapes, because the fifteen tricks are mostly the same few things aimed
differently: something that lands where it was announced, something that
travels, and something that opens out from a point. The snowfield's pillar and
the plateau's rings are the first shape again, so it is worth having once.
"""

import random

import pygame

from game import config
from game.entities.hazard import Falling, Ring, Wall
from game.entities.patch import BURNING
from game.entities.player import Player
from game.systems import boss_tricks

HOME = pygame.Vector2(3000, 3000)


def _player(at=None) -> Player:
    return Player(pos=pygame.Vector2(at or HOME))


def _tick(field, player, seconds, patches=None):
    patches = [] if patches is None else patches
    for _ in range(int(seconds / config.FIXED_DT)):
        boss_tricks.update(config.FIXED_DT, field, player, patches)
    return patches


# --- something that lands where it was announced -------------------------


def test_a_falling_spot_waits_before_it_lands():
    field = boss_tricks.Field()
    field.falling.append(Falling(pos=pygame.Vector2(HOME), damage=20.0))
    player = _player()
    _tick(field, player, config.FALL_WARNING * 0.5)
    assert player.hp == player.max_hp  # announced, not landed
    assert field.falling


def test_it_lands_and_is_gone():
    field = boss_tricks.Field()
    field.falling.append(Falling(pos=pygame.Vector2(HOME), damage=20.0))
    player = _player()
    _tick(field, player, config.FALL_WARNING + 0.1)
    assert player.hp < player.max_hp
    assert not field.falling


def test_stepping_off_the_circle_is_the_whole_point():
    field = boss_tricks.Field()
    field.falling.append(Falling(pos=pygame.Vector2(HOME), damage=20.0, radius=80.0))
    player = _player(HOME + pygame.Vector2(300, 0))
    _tick(field, player, config.FALL_WARNING + 0.1)
    assert player.hp == player.max_hp


def test_what_it_leaves_behind_is_asked_for_not_assumed():
    field = boss_tricks.Field()
    field.falling.append(Falling(pos=pygame.Vector2(HOME), damage=1.0, leaves=BURNING))
    patches = _tick(field, _player(), config.FALL_WARNING + 0.1)
    assert any(p.kind is BURNING for p in patches)

    field = boss_tricks.Field()
    field.falling.append(Falling(pos=pygame.Vector2(HOME), damage=1.0))
    assert not _tick(field, _player(), config.FALL_WARNING + 0.1)


# --- something that travels ----------------------------------------------


def test_a_wall_walks_forward():
    field = boss_tricks.Field()
    wall = Wall(pos=pygame.Vector2(HOME), vel=pygame.Vector2(100, 0), damage=5.0)
    field.walls.append(wall)
    _tick(field, _player(HOME + pygame.Vector2(5000, 0)), 1.0)
    assert wall.pos.x > HOME.x


def test_a_wall_hurts_what_it_reaches():
    field = boss_tricks.Field()
    field.walls.append(Wall(pos=pygame.Vector2(HOME), vel=pygame.Vector2(200, 0), damage=9.0))
    player = _player(HOME + pygame.Vector2(100, 0))
    _tick(field, player, 1.0)
    assert player.hp < player.max_hp


def test_a_wall_hurts_once_not_every_frame():
    # Sixty hits a second is not a wall, it is a death sentence for touching.
    field = boss_tricks.Field()
    field.walls.append(Wall(pos=pygame.Vector2(HOME), vel=pygame.Vector2(60, 0), damage=9.0))
    player = _player(HOME + pygame.Vector2(30, 0))
    _tick(field, player, 2.0)
    assert player.max_hp - player.hp == 9.0


def test_a_wall_runs_out():
    field = boss_tricks.Field()
    field.walls.append(Wall(pos=pygame.Vector2(HOME), vel=pygame.Vector2(60, 0), ttl=0.5))
    _tick(field, _player(HOME + pygame.Vector2(9000, 0)), 1.0)
    assert not field.walls


# --- something that opens out from a point -------------------------------


def test_a_ring_grows():
    field = boss_tricks.Field()
    ring = Ring(pos=pygame.Vector2(HOME), speed=300.0, reach=600.0)
    field.rings.append(ring)
    _tick(field, _player(HOME + pygame.Vector2(5000, 0)), 0.5)
    assert ring.radius > 0


def test_a_ring_catches_you_as_it_passes():
    field = boss_tricks.Field()
    field.rings.append(Ring(pos=pygame.Vector2(HOME), speed=300.0, reach=600.0, damage=12.0))
    player = _player(HOME + pygame.Vector2(300, 0))
    _tick(field, player, 2.0)
    assert player.hp < player.max_hp


def test_standing_at_the_middle_is_safe_once_it_has_passed():
    # It opens OUT. Staying where it started is the answer, which is what
    # makes "get close" the read.
    field = boss_tricks.Field()
    field.rings.append(Ring(pos=pygame.Vector2(HOME), speed=300.0, reach=600.0, damage=12.0))
    player = _player(HOME)
    _tick(field, player, 2.0)
    assert player.max_hp - player.hp <= 12.0  # caught at most on the first tick


def test_a_ring_stops_at_its_reach():
    field = boss_tricks.Field()
    field.rings.append(Ring(pos=pygame.Vector2(HOME), speed=600.0, reach=300.0))
    _tick(field, _player(HOME + pygame.Vector2(5000, 0)), 2.0)
    assert not field.rings


# --- the burnt forest's three --------------------------------------------


def _cast(key, boss_at=None, player_at=None):
    field = boss_tricks.Field()
    player = _player(player_at or (HOME + pygame.Vector2(250, 0)))
    boss_tricks.cast(key, field, pygame.Vector2(boss_at or HOME), player.pos, might=1.0)
    return field, player


def test_ember_announces_one_place_and_promises_more():
    # It used to put all five down at once. One at a time is the point now,
    # so what the cast leaves immediately is a single circle and a promise.
    field, _ = _cast("ember")
    assert len(field.falling) == 1
    assert field.casting[0].left == config.EMBER_DROPS - 1


def test_ember_drops_around_where_you_are():
    field, player = _cast("ember")
    assert any(f.pos.distance_to(player.pos) < config.EMBER_SPREAD for f in field.falling)


def test_ember_leaves_the_floor_burning():
    field, player = _cast("ember", player_at=HOME)
    patches = _tick(field, player, config.FALL_WARNING + 0.2)
    assert any(p.kind is BURNING for p in patches)


def test_flame_sends_one_wall_at_you():
    field, player = _cast("flame")
    assert len(field.walls) == 1
    assert field.walls[0].vel.x > 0  # the player is to the right


def test_flame_is_slow_enough_to_walk_around():
    field, _ = _cast("flame")
    assert field.walls[0].vel.length() < config.PLAYER_SPEED


def test_ashheart_opens_out_of_the_boss():
    field, _ = _cast("ashheart")
    assert len(field.rings) == 1
    assert field.rings[0].pos == HOME


def test_ashheart_leaves_fire_where_it_went():
    field, player = _cast("ashheart", player_at=HOME + pygame.Vector2(200, 0))
    patches = _tick(field, player, 3.0)
    assert any(p.kind is BURNING for p in patches)


def test_the_second_phase_makes_all_three_hit_harder():
    def hurt(key, might):
        # Both runs get the same dice. Ember scatters, and a different scatter
        # would be comparing luck rather than the multiplier -- its beats draw
        # from the module's own generator, so that is the one to pin.
        boss_tricks._SPIN.seed(7)
        field = boss_tricks.Field()
        player = _player(HOME)
        boss_tricks.cast(
            key, field, pygame.Vector2(HOME), player.pos, might=might, rng=random.Random(7)
        )
        _tick(field, player, 6.0)
        return player.max_hp - player.hp

    for key in ("ember", "flame", "ashheart"):
        assert hurt(key, 1.5) > hurt(key, 1.0), key


def test_every_trick_the_burnt_lord_holds_can_be_cast():
    from game.entities.boss import BOSS_KINDS

    for key in BOSS_KINDS[0].tricks:
        field, player = _cast(key)
        assert field.falling or field.walls or field.rings, key


def test_a_trick_nobody_has_written_yet_is_quiet_rather_than_a_crash():
    # All fifteen are built now, so this is tested with a name that is not a
    # trick at all. The quiet path still matters: the design is edited more
    # often than the behaviour, and a boss must not take the game down over a
    # key the table has and the system does not.
    field = boss_tricks.Field()
    boss_tricks.cast("nothing_at_all", field, pygame.Vector2(HOME), pygame.Vector2(HOME), 1.0)
    assert not (field.falling or field.walls or field.rings)


# --- what is left behind must match what was announced -------------------


def test_the_fire_left_behind_is_the_circle_you_were_shown():
    # It used to be the global patch size, which was larger than the warning:
    # you stepped out of a ninety-wide circle and the fire that replaced it was
    # a hundred and twenty. Dodging correctly still burned you.
    field = boss_tricks.Field()
    field.falling.append(Falling(pos=pygame.Vector2(HOME), damage=1.0, radius=70.0, leaves=BURNING))
    patches = _tick(field, _player(HOME + pygame.Vector2(9000, 0)), config.FALL_WARNING + 0.1)
    assert patches[0].radius == 70.0


def test_one_ember_leaves_somewhere_to_stand():
    # Five circles that between them carpet the room is not a trick, it is a
    # timer on the fight. The arena has to still have floor in it.
    import math

    field, player = _cast("ember", boss_at=HOME, player_at=HOME)
    patches = _tick(field, player, config.FALL_WARNING + 0.2)
    covered = sum(math.pi * p.radius**2 for p in patches)  # overlap ignored
    room = math.pi * config.TEMPLE_RADIUS**2
    assert covered / room < 0.3


# --- one at a time, while the boss stands there --------------------------


def test_ember_drops_one_at_a_time():
    # Five circles at once is a place to not be. One after another is a thing
    # to walk away from, and the walking is what the trick is for.
    field, player = _cast("ember")
    assert len(field.falling) == 1
    _tick(field, player, config.EMBER_INTERVAL * 1.1)
    assert len(field.falling) >= 1
    assert field.casting  # more still to come


def test_ember_keeps_going_until_it_has_dropped_them_all():
    field, player = _cast("ember")
    seen = 0
    patches = []
    for _ in range(int((config.EMBER_INTERVAL * config.EMBER_DROPS + 2.0) / config.FIXED_DT)):
        before = len(patches)
        boss_tricks.update(config.FIXED_DT, field, player, patches)
        seen += len(patches) - before
    assert seen == config.EMBER_DROPS
    assert not field.casting


def test_each_one_lands_near_where_you_are_when_it_appears():
    # They follow, so standing still collects all five. Walking is the answer.
    field = boss_tricks.Field()
    player = _player(HOME)
    boss_tricks.cast("ember", field, pygame.Vector2(HOME), player.pos, might=1.0)
    player.pos.update(HOME + pygame.Vector2(2000, 0))
    _tick(field, player, config.EMBER_INTERVAL * 1.5)
    latest = field.falling[-1]
    assert latest.pos.distance_to(player.pos) < config.EMBER_SPREAD + 1


def test_casting_says_how_long_the_boss_is_busy():
    # The boss stands still for its own channel; the number it stands for has
    # to come from the trick rather than be guessed at the call site.
    field = boss_tricks.Field()
    held = boss_tricks.cast("ember", field, pygame.Vector2(HOME), pygame.Vector2(HOME))
    assert held >= config.EMBER_INTERVAL * (config.EMBER_DROPS - 1)


def test_an_instant_trick_holds_nobody():
    field = boss_tricks.Field()
    assert boss_tricks.cast("flame", field, pygame.Vector2(HOME), pygame.Vector2(HOME)) == 0.0


def test_an_unbuilt_trick_holds_nobody_either():
    field = boss_tricks.Field()
    held = boss_tricks.cast("nothing_at_all", field, pygame.Vector2(HOME), pygame.Vector2(HOME))
    assert held == 0.0
