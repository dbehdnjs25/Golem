"""The five blows a boss has that have nothing to do with its element.

Each one is wind, act, rest. The wind is what makes the fight a fight: it
commits the boss to an aim before anything can happen, so every blow can be
read and stepped out of. Without it they would all be "you are near it, so you
are hurt", which is what the contact damage already is.
"""

import pygame

from game import config
from game.entities.boss import BOSS_KINDS, COMMONS, Boss
from game.entities.player import Player
from game.systems import boss_moves

ROOM = pygame.Vector2(4000, 4000)
RADIUS = config.TEMPLE_RADIUS


def _boss(index: int = 0, at=None) -> Boss:
    return Boss(pos=pygame.Vector2(at or ROOM), kind=BOSS_KINDS[index])


def _player(at=None) -> Player:
    return Player(pos=pygame.Vector2(at or (ROOM + pygame.Vector2(200, 0))))


# How long until a forced blow has actually landed.
TO_BLOW = config.BOSS_MOVE_GAP + config.BOSS_WIND + 0.05


def _run(brawl, boss, player, seconds, move=None, pin=True):
    """Tick for ``seconds``, by default keeping the player where they stand.

    Pinned, because most of these ask what a blow does to someone who did not
    move. The arm's tests pass pin=False: being dragged somewhere else is the
    thing they are checking, and a pin would undo it every frame.
    """
    stood = pygame.Vector2(player.pos)
    for _ in range(int(seconds / config.FIXED_DT)):
        brawl.update(config.FIXED_DT, boss, player, ROOM, RADIUS, forced=move)
        if brawl.move is not None:
            move = None  # only force the first choice
        if pin:
            player.pos.update(stood)


# --- the shape every blow shares -----------------------------------------


def test_nothing_happens_before_the_first_gap():
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player()
    brawl.update(config.FIXED_DT, boss, player, ROOM, RADIUS)
    assert brawl.move is None


def test_a_blow_winds_up_before_it_lands():
    # The whole reason a boss is a fight rather than a wall.
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player()
    _run(brawl, boss, player, config.BOSS_MOVE_GAP + 0.05, move="slam")
    assert brawl.move == "slam"
    assert brawl.phase == boss_moves.WIND
    assert player.hp == player.max_hp  # nothing yet


def test_it_commits_to_an_aim_when_the_wind_starts():
    # Fixed at the wind, not re-read at the blow. Tracking you through the
    # wind-up means the telegraph tells you nothing.
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player()
    _run(brawl, boss, player, config.BOSS_MOVE_GAP + 0.05, move="charge")
    aimed = pygame.Vector2(brawl.aim)
    player.pos.update(ROOM + pygame.Vector2(0, 400))
    brawl.update(config.FIXED_DT, boss, player, ROOM, RADIUS)
    assert brawl.aim == aimed


def test_every_common_can_be_thrown():
    for key in COMMONS:
        brawl = boss_moves.Brawl()
        boss, player = _boss(), _player()
        _run(brawl, boss, player, config.BOSS_MOVE_GAP + 2.5, move=key)
        assert brawl.struck, key  # it reached its blow


def test_it_only_throws_what_its_kind_holds():
    for index, kind in enumerate(BOSS_KINDS):
        brawl = boss_moves.Brawl()
        boss, player = _boss(index), _player()
        seen = set()
        for _ in range(4000):
            brawl.update(config.FIXED_DT, boss, player, ROOM, RADIUS)
            if brawl.move is not None:
                seen.add(brawl.move)
        assert seen <= set(kind.commons), (kind.key, seen)
        assert seen  # and it does throw


def test_a_dodging_player_takes_nothing():
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player(ROOM)
    player.iframe_timer = 99.0
    _run(brawl, boss, player, config.BOSS_MOVE_GAP + 2.5, move="slam")
    assert player.hp == player.max_hp


def test_it_rests_before_the_next_one():
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player()
    _run(brawl, boss, player, config.BOSS_MOVE_GAP + 2.5, move="slam")
    first = brawl.thrown
    brawl.update(config.FIXED_DT, boss, player, ROOM, RADIUS)
    assert brawl.thrown == first  # not straight into another


# --- what each one actually does -----------------------------------------


def test_a_slam_hurts_what_is_standing_on_it():
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player(ROOM)
    _run(brawl, boss, player, config.BOSS_MOVE_GAP + 2.5, move="slam")
    assert player.hp < player.max_hp


def test_a_slam_misses_anyone_who_stepped_out():
    brawl = boss_moves.Brawl()
    boss = _boss()
    player = _player(ROOM + pygame.Vector2(config.SLAM_RADIUS * 2, 0))
    _run(brawl, boss, player, config.BOSS_MOVE_GAP + 2.5, move="slam")
    assert player.hp == player.max_hp


def test_a_charge_crosses_the_room():
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player(ROOM + pygame.Vector2(300, 0))
    start = pygame.Vector2(boss.pos)
    _run(brawl, boss, player, config.BOSS_MOVE_GAP + 2.5, move="charge")
    assert boss.pos.distance_to(start) > 100


def test_a_charge_hurts_what_it_runs_through():
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player(ROOM + pygame.Vector2(250, 0))
    _run(brawl, boss, player, config.BOSS_MOVE_GAP + 2.5, move="charge")
    assert player.hp < player.max_hp


def test_a_charge_stops_at_the_wall():
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player(ROOM + pygame.Vector2(RADIUS * 2, 0))
    _run(brawl, boss, player, config.BOSS_MOVE_GAP + 3.0, move="charge")
    assert ROOM.distance_to(boss.pos) <= RADIUS


def test_a_sweep_catches_what_is_in_front():
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player(ROOM + pygame.Vector2(config.SWEEP_RANGE * 0.6, 0))
    _run(brawl, boss, player, config.BOSS_MOVE_GAP + 2.5, move="sweep")
    assert player.hp < player.max_hp


def test_a_sweep_misses_what_is_behind():
    # Walking through it is the answer, which is only an answer if behind is
    # safe.
    brawl = boss_moves.Brawl()
    boss = _boss()
    player = _player(ROOM + pygame.Vector2(config.SWEEP_RANGE * 0.6, 0))
    _run(brawl, boss, player, config.BOSS_MOVE_GAP + 0.05, move="sweep")
    player.pos.update(ROOM - pygame.Vector2(config.SWEEP_RANGE * 0.6, 0))
    _run(brawl, boss, player, 2.5)
    assert player.hp == player.max_hp


def test_a_leap_lands_where_you_were():
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player(ROOM + pygame.Vector2(350, 0))
    where = pygame.Vector2(player.pos)
    _run(brawl, boss, player, config.BOSS_MOVE_GAP + 2.5, move="leap")
    assert boss.pos.distance_to(where) < config.LEAP_RADIUS


def test_a_leap_hurts_where_it_lands():
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player(ROOM + pygame.Vector2(350, 0))
    _run(brawl, boss, player, config.BOSS_MOVE_GAP + 2.5, move="leap")
    assert player.hp < player.max_hp


def test_a_grab_throws_the_arm():
    brawl = boss_moves.Brawl()
    boss, player = _boss(1), _player(ROOM + pygame.Vector2(2000, 0))
    _run(brawl, boss, player, TO_BLOW, move="grab")
    assert brawl.arm.out


def test_a_caught_player_is_dragged_in():
    brawl = boss_moves.Brawl()
    boss, player = _boss(1), _player(ROOM + pygame.Vector2(300, 0))
    far = pygame.Vector2(player.pos)
    _run(brawl, boss, player, TO_BLOW + 2.0, move="grab", pin=False)
    assert player.pos.distance_to(boss.pos) < far.distance_to(boss.pos)


def test_the_close_blows_wait_while_the_arm_is_away():
    brawl = boss_moves.Brawl()
    boss, player = _boss(1), _player(ROOM + pygame.Vector2(2000, 0))
    _run(brawl, boss, player, TO_BLOW + 0.3, move="grab")
    assert brawl.arm.out
    assert brawl.move == "grab"  # it has not moved on to a close blow


# --- the second phase hits harder ----------------------------------------


def test_the_second_phase_hits_harder():
    def damage_done(phase_two: bool) -> float:
        brawl = boss_moves.Brawl()
        boss, player = _boss(), _player(ROOM)
        if phase_two:
            boss.damage(boss.kind.hp * 0.6)
        _run(brawl, boss, player, config.BOSS_MOVE_GAP + 2.5, move="slam")
        return player.max_hp - player.hp

    assert damage_done(True) > damage_done(False)
