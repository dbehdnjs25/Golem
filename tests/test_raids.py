import pytest

from game import config
from game.systems import raids


def test_the_interval_shortens_with_every_boss():
    assert [raids.interval(n) for n in range(6)] == list(config.RAID_INTERVALS)


def test_it_starts_at_a_week_and_bottoms_out_at_two_days():
    assert raids.interval(0) == 7
    assert raids.interval(5) == 2


def test_more_bosses_than_the_table_knows_does_not_blow_up():
    # Nothing should be able to kill six bosses, but an index error here would
    # be a crash at the very end of a run, which is the worst possible place.
    assert raids.interval(6) == 2
    assert raids.interval(99) == 2


def test_the_first_day_is_never_a_raid():
    # A raid before the player owns a pick is not difficulty, it is a joke.
    assert not raids.is_raid_night(1, 0)


def test_raids_land_on_the_interval():
    assert raids.is_raid_night(8, 0)  # day 1 + a week
    assert raids.is_raid_night(15, 0)
    assert not raids.is_raid_night(7, 0)
    assert not raids.is_raid_night(9, 0)


def test_killing_a_boss_brings_the_nights_closer_together():
    none_yet = [d for d in range(2, 40) if raids.is_raid_night(d, 0)]
    all_five = [d for d in range(2, 40) if raids.is_raid_night(d, 5)]
    assert len(all_five) > len(none_yet)


def test_the_countdown_reads_zero_on_the_night_itself():
    assert raids.days_until(8, 0) == 0
    assert raids.days_until(7, 0) == 1
    assert raids.days_until(1, 0) == 7


def test_the_countdown_never_goes_negative_or_past_the_interval():
    # A whole interval is a legal answer: it is what day 1 says, being a cycle
    # that has only just started.
    for bosses in range(6):
        for day in range(1, 60):
            left = raids.days_until(day, bosses)
            assert 0 <= left <= raids.interval(bosses)


def test_the_countdown_agrees_with_the_test_for_a_raid():
    # Two ways of asking the same question; they must never disagree, or the
    # warning on screen will point at the wrong night.
    for bosses in range(6):
        for day in range(1, 60):
            assert (raids.days_until(day, bosses) == 0) == raids.is_raid_night(day, bosses)


def test_negative_boss_counts_are_refused():
    with pytest.raises(ValueError):
        raids.interval(-1)
