"""The snowfield's three, and the two pieces they needed.

Fire fell, walked and burst. Ice is thrown, swept and dropped: a ball that
breaks apart on the wall, a fan that leaves the floor slick, and columns that
land where they were announced and then stand in the way.

Two new things come with them. A BALL, because nothing yet travelled and then
did something on arrival. And a PILLAR, because nothing in the game had ever
been in the way -- which is the whole of what the snowfield's last trick asks.
"""

import random

import pygame

from game import config
from game.entities.hazard import Ball, Pillar
from game.entities.patch import FROST
from game.entities.player import Player
from game.systems import boss_tricks

HOME = pygame.Vector2(3000, 3000)
ROOM = pygame.Vector2(HOME)
RADIUS = config.TEMPLE_RADIUS


def _player(at=None) -> Player:
    return Player(pos=pygame.Vector2(at or HOME))


def _tick(field, player, seconds, patches=None, room=None, radius=RADIUS):
    patches = [] if patches is None else patches
    for _ in range(int(seconds / config.FIXED_DT)):
        boss_tricks.update(
            config.FIXED_DT, field, player, patches, room=room or ROOM, radius=radius
        )
    return patches


# --- a ball that breaks on the wall --------------------------------------


def test_a_ball_travels():
    field = boss_tricks.Field()
    ball = Ball(pos=pygame.Vector2(HOME), vel=pygame.Vector2(300, 0))
    field.balls.append(ball)
    _tick(field, _player(HOME + pygame.Vector2(9000, 0)), 0.3)
    assert ball.pos.x > HOME.x


def test_a_ball_hurts_what_it_reaches():
    field = boss_tricks.Field()
    field.balls.append(Ball(pos=pygame.Vector2(HOME), vel=pygame.Vector2(300, 0), damage=11.0))
    player = _player(HOME + pygame.Vector2(60, 0))
    _tick(field, player, 0.5)
    assert player.hp < player.max_hp


def test_a_ball_breaks_apart_at_the_wall():
    # Nothing to dodge while it crosses the room; the danger is where it ends,
    # which is what makes standing near a wall the mistake.
    field = boss_tricks.Field()
    field.balls.append(
        Ball(pos=pygame.Vector2(HOME), vel=pygame.Vector2(600, 0), splits=5, damage=9.0)
    )
    # Looked at just after it breaks: the shards then fly on and are gone off
    # the wall themselves, so a later look finds an empty room.
    for _ in range(int(3.0 / config.FIXED_DT)):
        boss_tricks.update(config.FIXED_DT, field, _player(HOME), [], room=ROOM, radius=RADIUS)
        if len(field.balls) != 1:
            break
    assert len(field.balls) == 5
    assert all(b.splits == 0 for b in field.balls)  # shards do not split again


def test_the_shards_fly_apart():
    field = boss_tricks.Field()
    field.balls.append(Ball(pos=pygame.Vector2(HOME), vel=pygame.Vector2(600, 0), splits=4))
    for _ in range(int(3.0 / config.FIXED_DT)):
        boss_tricks.update(config.FIXED_DT, field, _player(HOME), [], room=ROOM, radius=RADIUS)
        if len(field.balls) != 1:
            break
    ways = {tuple(round(c, 2) for c in b.vel.normalize()) for b in field.balls}
    assert len(ways) == 4  # four directions, not four copies of one


def test_a_shard_runs_out():
    field = boss_tricks.Field()
    field.balls.append(Ball(pos=pygame.Vector2(HOME), vel=pygame.Vector2(600, 0), splits=3))
    _tick(field, _player(HOME), 12.0)
    assert not field.balls


# --- a pillar that stands in the way -------------------------------------


def test_a_pillar_pushes_you_out_of_it():
    field = boss_tricks.Field()
    field.pillars.append(Pillar(pos=pygame.Vector2(HOME)))
    player = _player(HOME)  # standing inside it
    _tick(field, player, 0.1)
    assert player.pos.distance_to(HOME) >= config.PILLAR_RADIUS


def test_a_pillar_leaves_someone_outside_it_alone():
    field = boss_tricks.Field()
    field.pillars.append(Pillar(pos=pygame.Vector2(HOME)))
    away = HOME + pygame.Vector2(config.PILLAR_RADIUS * 3, 0)
    player = _player(away)
    _tick(field, player, 0.2)
    assert player.pos == away


def test_a_pillar_can_be_broken():
    field = boss_tricks.Field()
    pillar = Pillar(pos=pygame.Vector2(HOME))
    field.pillars.append(pillar)
    pillar.damage(config.PILLAR_HP)
    _tick(field, _player(HOME + pygame.Vector2(500, 0)), 0.1)
    assert not field.pillars


def test_a_pillar_melts_on_its_own_eventually():
    # Left standing for the rest of the fight, one bad cast would wall the room
    # off permanently.
    field = boss_tricks.Field()
    field.pillars.append(Pillar(pos=pygame.Vector2(HOME)))
    _tick(field, _player(HOME + pygame.Vector2(500, 0)), config.PILLAR_SECONDS + 0.5)
    assert not field.pillars


# --- the three -----------------------------------------------------------


def _cast(key, boss_at=None, player_at=None, might=1.0):
    field = boss_tricks.Field()
    player = _player(player_at or (HOME + pygame.Vector2(250, 0)))
    boss_tricks.cast(
        key,
        field,
        pygame.Vector2(boss_at or HOME),
        player.pos,
        might=might,
        rng=random.Random(5),
    )
    return field, player


def test_the_basic_throws_one_ball_at_you():
    field, player = _cast("frost")
    assert len(field.balls) == 1
    assert field.balls[0].vel.x > 0  # the player is to the right
    assert field.balls[0].splits > 1


def test_the_greater_sweeps_a_fan_and_leaves_it_slick():
    field, player = _cast("coldsnap", player_at=HOME + pygame.Vector2(120, 0))
    patches = _tick(field, player, 0.1)
    assert any(p.kind is FROST for p in patches)


def test_the_greater_catches_what_is_in_front():
    field = boss_tricks.Field()
    player = _player(HOME + pygame.Vector2(120, 0))
    boss_tricks.cast("coldsnap", field, pygame.Vector2(HOME), player.pos, rng=random.Random(1))
    _tick(field, player, 0.1)  # the swing lands on the next step
    assert player.hp < player.max_hp


def test_the_greater_misses_what_is_behind():
    field = boss_tricks.Field()
    aim = HOME + pygame.Vector2(120, 0)
    player = _player(HOME - pygame.Vector2(120, 0))
    boss_tricks.cast("coldsnap", field, pygame.Vector2(HOME), aim, rng=random.Random(1))
    _tick(field, player, 0.1)
    # The fan was aimed the other way; nothing lands on someone behind it.
    assert player.hp == player.max_hp


def test_the_supreme_announces_where_the_columns_land():
    field, player = _cast("absolute")
    assert len(field.falling) == config.ABSOLUTE_PILLARS
    assert not field.pillars  # nothing standing yet


def test_the_columns_stand_where_they_landed():
    field, player = _cast("absolute", player_at=HOME)
    _tick(field, player, config.FALL_WARNING + 0.1)
    assert len(field.pillars) == config.ABSOLUTE_PILLARS


def test_standing_under_one_hurts():
    field = boss_tricks.Field()
    player = _player(HOME)
    boss_tricks.cast("absolute", field, pygame.Vector2(HOME), player.pos, rng=random.Random(5))
    field.falling[0].pos.update(player.pos)  # make sure one is overhead
    _tick(field, player, config.FALL_WARNING + 0.1)
    assert player.hp < player.max_hp


def test_every_snowfield_trick_is_built():
    from game.entities.boss import BOSS_KINDS

    snow = next(k for k in BOSS_KINDS if k.biome.key == "snowfield")
    for key in snow.tricks:
        field, player = _cast(key)
        assert field.balls or field.falling or field.rings or field.walls, key


def test_the_second_phase_makes_all_three_hit_harder():
    # Each is stood where it actually lands: a thrown ball at the body, a fan
    # an arm's length in front of the swing, a column overhead. Standing
    # somewhere a trick misses would be comparing nothing with nothing.
    places = {"frost": HOME, "coldsnap": HOME + pygame.Vector2(120, 0), "absolute": HOME}

    def hurt(key, might):
        boss_tricks._SPIN.seed(3)
        field = boss_tricks.Field()
        player = _player(places[key])
        boss_tricks.cast(
            key, field, pygame.Vector2(HOME), player.pos, might=might, rng=random.Random(5)
        )
        if key == "absolute":
            field.falling[0].pos.update(player.pos)  # one of the four overhead
        _tick(field, player, 4.0)
        return player.max_hp - player.hp

    for key in ("frost", "coldsnap", "absolute"):
        assert hurt(key, 1.6) > hurt(key, 1.0), key
