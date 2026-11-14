"""The wind plateau's three, and the shape they needed.

Wind does not hit, it MOVES you. Which needed the one shape none of the five
earlier tricks had: a place rather than an event. A circle that lands, a front
that passes and a ring that crosses are all over the instant they resolve; a
whirl has to still be there a second later, growing, with you being pulled
into it the whole time.

So: a whirl that grows (바람1), the whole floor flowing one way (바람2), and
circles around the boss that burst in order (바람3).
"""

import random

import pygame

from game import config
from game.entities.hazard import Zone
from game.entities.player import Player
from game.systems import boss_tricks

HOME = pygame.Vector2(3000, 3000)
RADIUS = config.TEMPLE_RADIUS


def _player(at=None) -> Player:
    return Player(pos=pygame.Vector2(at or HOME))


def _tick(field, player, seconds, patches=None):
    patches = [] if patches is None else patches
    for _ in range(int(seconds / config.FIXED_DT)):
        boss_tricks.update(config.FIXED_DT, field, player, patches, room=HOME, radius=RADIUS)
    return patches


def _cast(key, boss_at=None, player_at=None, might=1.0, patches=None):
    field = boss_tricks.Field()
    player = _player(player_at or (HOME + pygame.Vector2(250, 0)))
    boss_tricks.cast(
        key,
        field,
        pygame.Vector2(boss_at or HOME),
        player.pos,
        might=might,
        rng=random.Random(5),
        patches=patches,
        room=HOME,
        radius=RADIUS,
    )
    return field, player


# --- a place rather than an event ----------------------------------------


def test_a_zone_bills_by_the_second():
    # Not per entry. A brush past has to be cheap and standing in it must not
    # be, which is the whole difference between a place and a blow.
    field = boss_tricks.Field()
    field.zones.append(Zone(pos=pygame.Vector2(HOME), radius=100, dps=10.0, ttl=9.0))
    player = _player(HOME)
    _tick(field, player, 1.0)
    taken = player.max_hp - player.hp
    assert 8.0 < taken < 12.0


def test_a_zone_leaves_someone_outside_it_alone():
    field = boss_tricks.Field()
    field.zones.append(Zone(pos=pygame.Vector2(HOME), radius=100, dps=10.0, ttl=9.0))
    player = _player(HOME + pygame.Vector2(400, 0))
    _tick(field, player, 1.0)
    assert player.hp == player.max_hp


def test_a_zone_runs_out():
    field = boss_tricks.Field()
    field.zones.append(Zone(pos=pygame.Vector2(HOME), radius=100, ttl=1.0))
    _tick(field, _player(HOME), 1.5)
    assert not field.zones


def test_a_zone_can_be_thrown_and_then_sits():
    field = boss_tricks.Field()
    zone = Zone(
        pos=pygame.Vector2(HOME), radius=50, vel=pygame.Vector2(200, 0), settle=0.5, ttl=5.0
    )
    field.zones.append(zone)
    _tick(field, _player(HOME + pygame.Vector2(2000, 0)), 0.5)
    flew_to = pygame.Vector2(zone.pos)
    assert flew_to.x > HOME.x
    _tick(field, _player(HOME + pygame.Vector2(2000, 0)), 1.0)
    assert zone.pos.distance_to(flew_to) < 1  # it stopped where it settled


def test_a_whirl_drags_you_in():
    field = boss_tricks.Field()
    field.zones.append(Zone(pos=pygame.Vector2(HOME), radius=300, pull=150.0, ttl=5.0))
    player = _player(HOME + pygame.Vector2(200, 0))
    _tick(field, player, 0.5)
    assert player.pos.distance_to(HOME) < 200


def test_a_whirl_can_be_walked_out_of():
    # Wind that cannot be leaned against is a cage, not a current.
    assert config.BREEZE_PULL < config.PLAYER_SPEED
    assert config.GALE_DRIFT < config.PLAYER_SPEED


def test_the_wind_cannot_push_you_through_the_wall():
    field = boss_tricks.Field()
    field.zones.append(
        Zone(pos=pygame.Vector2(HOME), radius=9000, drift=pygame.Vector2(600, 0), ttl=9.0)
    )
    player = _player(HOME)
    _tick(field, player, 6.0)
    assert HOME.distance_to(player.pos) <= RADIUS


# --- the three -----------------------------------------------------------


def test_the_basic_puts_a_whirl_where_you_were():
    field, player = _cast("breeze")
    assert len(field.zones) == 1
    assert field.zones[0].pos.distance_to(player.pos) < 1
    assert field.zones[0].pull > 0


def test_the_basic_grows():
    field, player = _cast("breeze")
    was = field.zones[0].radius
    _tick(field, _player(HOME + pygame.Vector2(2000, 0)), 1.0)
    assert field.zones[0].radius > was


def test_ignoring_the_basic_is_what_costs_you():
    field, player = _cast("breeze", player_at=HOME)
    _tick(field, player, 2.0)
    assert player.hp < player.max_hp


def test_the_greater_fills_the_whole_room():
    field, player = _cast("gale")
    assert len(field.zones) == 1
    assert field.zones[0].radius >= RADIUS
    assert field.zones[0].drift.length() > 0


def test_the_greater_blows_away_from_the_boss():
    field, player = _cast("gale", boss_at=HOME, player_at=HOME + pygame.Vector2(250, 0))
    assert field.zones[0].drift.x > 0  # the player was to the right of it


def test_the_greater_pushes_you_downwind():
    field, player = _cast("gale", player_at=HOME + pygame.Vector2(250, 0))
    before = pygame.Vector2(player.pos)
    _tick(field, player, 1.0)
    assert player.pos.x > before.x


def test_the_greater_does_not_hold_the_boss_still():
    # The point of a current is what the boss does to you while you lean.
    field = boss_tricks.Field()
    held = boss_tricks.cast(
        "gale", field, pygame.Vector2(HOME), HOME + pygame.Vector2(200, 0), room=HOME
    )
    assert held == 0.0


def test_the_supreme_announces_all_of_them_at_once():
    field, player = _cast("stormcore")
    assert len(field.falling) == config.STORMCORE_BURSTS


def test_the_supreme_bursts_them_in_order():
    field, player = _cast("stormcore")
    waits = [spot.left for spot in field.falling]
    assert waits == sorted(waits)
    assert waits[-1] > waits[0]  # a sequence, not six at once


def test_the_supreme_leaves_a_gap_to_stand_in():
    # Six circles that between them cover the ring would be a timer on the
    # fight rather than a thing to read.
    field, player = _cast("stormcore")
    places = [spot.pos for spot in field.falling]
    gaps = [min(a.distance_to(b) for b in places if b is not a) for a in places]
    assert min(gaps) > config.FALL_RADIUS


def test_the_supreme_holds_the_boss_while_it_turns():
    field = boss_tricks.Field()
    held = boss_tricks.cast("stormcore", field, pygame.Vector2(HOME), HOME, rng=random.Random(1))
    assert held > 1.0


def test_every_plateau_trick_is_built():
    from game.entities.boss import BOSS_KINDS

    gale = next(k for k in BOSS_KINDS if k.biome.key == "wind_plateau")
    for key in gale.tricks:
        field, player = _cast(key)
        assert field.zones or field.falling, key


def test_the_second_phase_makes_all_three_hit_harder():
    places = {"breeze": HOME, "gale": HOME, "stormcore": None}

    def hurt(key, might):
        field, player = _cast(key, player_at=places[key], might=might)
        if key == "stormcore":
            field.falling[0].pos.update(player.pos)  # one of the six overhead
        _tick(field, player, 4.0)
        return player.max_hp - player.hp

    for key in ("breeze", "gale", "stormcore"):
        assert hurt(key, 1.6) > hurt(key, 1.0), key
