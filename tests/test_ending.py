"""How a run ends.

Two ways out, and the whole of stage nine is making them both real. Until now
``defeated`` was a flag nobody read: the core could be ground to nothing and
the game carried on as though the run still had a point.

Winning had no shape at all. It has one now, and it is the shape the rest of
the game was already pointing at -- five sigils carried home, and then one
night with everything the player has beaten walking in at once. Live to
morning and the run is won.
"""

import pygame

from game import config
from game.entities.core import Core
from game.systems.ending import LOST, WON, Ending


def _ending(**kwargs) -> Ending:
    return Ending(**kwargs)


def _night(end: Ending, sigils: int = config.SIGILS_TO_END) -> None:
    end.update(sigils_taken=sigils, is_night=True, core_destroyed=False)


def _dawn(end: Ending, sigils: int = config.SIGILS_TO_END) -> None:
    end.update(sigils_taken=sigils, is_night=False, core_destroyed=False)


# --- nothing has happened yet --------------------------------------------


def test_a_run_starts_unfinished():
    end = Ending()
    assert end.outcome is None
    assert not end.over
    assert not end.standing


def test_an_ordinary_night_is_not_the_last_one():
    end = Ending()
    end.update(sigils_taken=0, is_night=True, core_destroyed=False)
    assert not end.standing
    assert not end.over


def test_four_sigils_is_not_enough():
    # Five bosses, five sigils. Four is the player most of the way there, and
    # most of the way there is not an ending.
    end = Ending()
    end.update(sigils_taken=config.SIGILS_TO_END - 1, is_night=True, core_destroyed=False)
    assert not end.standing


# --- losing ---------------------------------------------------------------


def test_a_destroyed_core_loses_the_run():
    end = Ending()
    end.update(sigils_taken=0, is_night=False, core_destroyed=True)
    assert end.outcome is LOST
    assert end.over


def test_losing_during_the_last_night_still_loses():
    end = Ending()
    _night(end)
    assert end.standing
    end.update(sigils_taken=config.SIGILS_TO_END, is_night=True, core_destroyed=True)
    assert end.outcome is LOST
    assert not end.standing


def test_an_ending_is_final():
    # Whatever happens afterwards, including a core that reads as destroyed
    # one step and not the next, the run ended when it ended.
    end = Ending()
    end.update(sigils_taken=0, is_night=False, core_destroyed=True)
    _dawn(end)
    _night(end)
    assert end.outcome is LOST


# --- winning --------------------------------------------------------------


def test_the_last_sigil_calls_the_last_night():
    end = Ending()
    _night(end)
    assert end.standing
    assert not end.over  # standing through it is not the same as surviving it


def test_morning_after_the_last_night_wins():
    end = Ending()
    _night(end)
    _dawn(end)
    assert end.outcome is WON
    assert end.over
    assert not end.standing


def test_the_day_the_last_sigil_arrives_is_not_a_win():
    # Carried home in daylight: the night still has to be lived through.
    end = Ending()
    _dawn(end)
    assert not end.over
    assert not end.standing


def test_a_morning_without_a_last_night_wins_nothing():
    end = Ending()
    end.update(sigils_taken=0, is_night=True, core_destroyed=False)
    end.update(sigils_taken=0, is_night=False, core_destroyed=False)
    assert not end.over


def test_the_last_night_lasts_as_long_as_the_night_does():
    end = Ending()
    for _ in range(50):
        _night(end)
    assert end.standing
    assert not end.over
    _dawn(end)
    assert end.outcome is WON


# --- the fifth sigil has somewhere to go ----------------------------------


def test_the_core_takes_one_sigil_for_every_boss():
    core = Core(pos=pygame.Vector2(0, 0))
    core.ignite()
    for _ in range(config.SIGILS_TO_END):
        assert core.offer_sigil()
    assert core.sigils_taken == config.SIGILS_TO_END


def test_the_core_refuses_a_sixth():
    core = Core(pos=pygame.Vector2(0, 0))
    core.ignite()
    for _ in range(config.SIGILS_TO_END):
        core.offer_sigil()
    assert not core.offer_sigil()


def test_the_last_sigil_opens_no_new_ceiling():
    # It is the key to the ending, not another rung. The ladder already ran
    # out, and a sixth cap would be a number nobody climbs.
    core = Core(pos=pygame.Vector2(0, 0))
    core.ignite()
    for _ in range(config.SIGILS_TO_END - 1):
        core.offer_sigil()
    before = core.level_cap
    core.offer_sigil()
    assert core.level_cap == before
    assert core.level_cap == config.CORE_LEVEL_CAPS[-1]


def test_an_unlit_core_takes_nothing():
    core = Core(pos=pygame.Vector2(0, 0))
    assert not core.offer_sigil()


# --- what the scene does with it ------------------------------------------


def test_the_last_night_breaks_the_ward_whatever_the_calendar_says():
    from game.scenes.play import PlayScene

    scene = PlayScene()
    scene.core.ignite()
    scene.core.sigils_taken = config.SIGILS_TO_END
    scene.clock.elapsed = config.DAY_LENGTH + 1  # night
    scene.update(config.FIXED_DT)
    assert scene.is_last_stand
    assert scene.is_raid


def test_an_ordinary_night_is_still_the_calendar_s_business():
    from game.scenes.play import PlayScene

    scene = PlayScene()
    scene.core.ignite()
    scene.clock.elapsed = config.DAY_LENGTH + 1
    scene.update(config.FIXED_DT)
    assert not scene.is_last_stand


def test_the_world_stops_once_the_run_is_over():
    # A run that keeps running underneath its own ending is not an ending.
    from game.scenes.play import PlayScene

    scene = PlayScene()
    scene.core.ignite()
    scene.core.hp = 0.0
    scene.update(config.FIXED_DT)
    assert scene.defeated
    day, elapsed = scene.clock.day, scene.clock.elapsed
    where = pygame.Vector2(scene.player.pos)
    for _ in range(30):
        scene.update(config.FIXED_DT)
    assert scene.clock.day == day
    assert scene.clock.elapsed == elapsed
    assert scene.player.pos == where


def test_surviving_the_last_night_wins_the_run():
    from game.scenes.play import PlayScene

    scene = PlayScene()
    scene.core.ignite()
    scene.core.sigils_taken = config.SIGILS_TO_END
    scene.clock.elapsed = config.DAY_TOTAL - 0.5  # the end of the last night
    scene.update(config.FIXED_DT)
    assert scene.is_last_stand
    for _ in range(int(1.0 / config.FIXED_DT)):
        scene.update(config.FIXED_DT)
    assert scene.won
    assert not scene.defeated


def test_losing_the_core_on_the_last_night_still_loses():
    from game.scenes.play import PlayScene

    scene = PlayScene()
    scene.core.ignite()
    scene.core.sigils_taken = config.SIGILS_TO_END
    scene.clock.elapsed = config.DAY_LENGTH + 1
    scene.update(config.FIXED_DT)
    scene.core.hp = 0.0
    scene.update(config.FIXED_DT)
    assert scene.defeated
    assert not scene.won
