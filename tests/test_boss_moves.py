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
    # Fixed at the wind, not re-read at the blow: a telegraph that follows you
    # tells you nothing. The charge is the one exception and has its own test,
    # because its telegraph is a path rather than a place.
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player()
    _run(brawl, boss, player, config.BOSS_MOVE_GAP + 0.05, move="slam")
    aimed = pygame.Vector2(brawl.aim)
    player.pos.update(ROOM + pygame.Vector2(0, 400))
    brawl.update(config.FIXED_DT, boss, player, ROOM, RADIUS)
    assert brawl.aim == aimed


def test_every_common_can_be_thrown():
    for key in COMMONS:
        brawl = boss_moves.Brawl()
        boss, player = _boss(), _player()
        _run(brawl, boss, player, config.BOSS_MOVE_GAP + 2.5, move=key)
        assert brawl.landed, key  # it got all the way through its act beat


def test_it_only_throws_what_its_kind_holds():
    # Its two blows and, in the first phase, the one element trick it opens
    # with. Nothing from another boss's list and nothing from its own second
    # phase.
    for index, kind in enumerate(BOSS_KINDS):
        brawl = boss_moves.Brawl()
        boss, player = _boss(index), _player()
        allowed = set(kind.commons) | {kind.tricks[0]}
        seen = set()
        for _ in range(4000):
            brawl.update(config.FIXED_DT, boss, player, ROOM, RADIUS)
            if brawl.move is not None:
                seen.add(brawl.move)
        assert seen <= allowed, (kind.key, seen)
        assert seen  # and it does throw


def test_the_second_phase_puts_its_other_two_in_the_mix():
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player()
    boss.damage(boss.kind.hp * 0.6)
    seen = set()
    for _ in range(8000):
        brawl.update(config.FIXED_DT, boss, player, ROOM, RADIUS)
        if brawl.move is not None:
            seen.add(brawl.move)
    assert set(boss.kind.tricks) <= seen


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


# --- it moves, rather than arriving --------------------------------------


def _biggest_step(brawl, boss, player, seconds, move):
    """The furthest the boss travels in any single frame."""
    worst = 0.0
    for _ in range(int(seconds / config.FIXED_DT)):
        was = pygame.Vector2(boss.pos)
        brawl.update(config.FIXED_DT, boss, player, ROOM, RADIUS, forced=move)
        if brawl.move is not None:
            move = None
        worst = max(worst, was.distance_to(boss.pos))
    return worst


def test_a_charge_runs_rather_than_arriving():
    # It used to resolve in one frame, which on screen is a teleport: the boss
    # is here, then it is five hundred pixels away, and nothing was dodgeable
    # because nothing crossed the ground in between.
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player(ROOM + pygame.Vector2(300, 0))
    step = _biggest_step(brawl, boss, player, TO_BLOW + 2.5, "charge")
    assert step <= config.CHARGE_SPEED * config.FIXED_DT * 1.5


def test_a_leap_takes_to_the_air_rather_than_blinking():
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player(ROOM + pygame.Vector2(350, 0))
    step = _biggest_step(brawl, boss, player, TO_BLOW + 2.5, "leap")
    through_the_air = 350 / config.LEAP_SECONDS
    assert step <= through_the_air * config.FIXED_DT * 1.5


def test_a_leap_only_lands_when_it_lands():
    # The air time is the warning. Hurt on take-off, the jump itself would be
    # the blow and there would be nothing to step out of.
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player(ROOM + pygame.Vector2(350, 0))
    _run(brawl, boss, player, TO_BLOW + config.LEAP_SECONDS * 0.4, move="leap")
    assert player.hp == player.max_hp
    _run(brawl, boss, player, config.LEAP_SECONDS)
    assert player.hp < player.max_hp


# --- the charge takes aim while it winds ---------------------------------


def test_a_charge_follows_you_while_it_winds():
    # The one blow that tracks. It is the only one whose telegraph is a path
    # rather than a place, so a path aimed where you no longer are tells you
    # nothing and the boss simply runs past.
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player(ROOM + pygame.Vector2(300, 0))
    brawl.update(config.BOSS_MOVE_GAP + 0.01, boss, player, ROOM, RADIUS, forced="charge")
    assert brawl.phase == boss_moves.WIND
    first = pygame.Vector2(brawl.aim)
    player.pos.update(ROOM + pygame.Vector2(0, 300))
    brawl.update(config.FIXED_DT, boss, player, ROOM, RADIUS)
    assert brawl.aim != first
    assert brawl.aim == player.pos


def test_once_it_is_running_the_line_is_set():
    # Tracking through the run would be a homing missile, not a charge.
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player(ROOM + pygame.Vector2(300, 0))
    _run(brawl, boss, player, TO_BLOW, move="charge")
    assert brawl.phase == boss_moves.ACT
    going = pygame.Vector2(brawl.going)
    player.pos.update(ROOM + pygame.Vector2(0, 300))
    brawl.update(config.FIXED_DT, boss, player, ROOM, RADIUS)
    assert brawl.going == going


def test_the_other_blows_still_commit_at_the_wind():
    for key in ("slam", "sweep", "leap", "grab"):
        brawl = boss_moves.Brawl()
        boss, player = _boss(), _player(ROOM + pygame.Vector2(300, 0))
        brawl.update(config.BOSS_MOVE_GAP + 0.01, boss, player, ROOM, RADIUS, forced=key)
        aimed = pygame.Vector2(brawl.aim)
        player.pos.update(ROOM + pygame.Vector2(0, 300))
        brawl.update(config.FIXED_DT, boss, player, ROOM, RADIUS)
        assert brawl.aim == aimed, key


def test_a_blow_in_progress_says_so():
    # The scene stops walking the boss while this is true: winding up and
    # drifting forward at the same time makes the telegraph a lie.
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player()
    assert not brawl.busy
    brawl.update(config.BOSS_MOVE_GAP + 0.01, boss, player, ROOM, RADIUS, forced="slam")
    assert brawl.busy


def test_a_channel_keeps_the_boss_put_for_its_whole_length():
    # Ember lays one circle at a time. Able to walk out of its own channel,
    # the boss would be handing over a free hit rather than taking a risk.
    brawl = boss_moves.Brawl()
    boss, player = _boss(), _player()
    _run(brawl, boss, player, TO_BLOW, move="ember")
    assert brawl.phase == boss_moves.ACT
    stood = pygame.Vector2(boss.pos)
    held_for = config.EMBER_INTERVAL * (config.EMBER_DROPS - 1)
    _run(brawl, boss, player, held_for * 0.8)
    assert brawl.busy
    assert boss.pos == stood  # the scene stops walking it while busy
