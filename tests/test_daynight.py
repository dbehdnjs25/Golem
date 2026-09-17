from game import config
from game.systems.daynight import DAY, NIGHT, DayNight


def test_a_fresh_clock_starts_on_the_morning_of_day_one():
    clock = DayNight()
    assert clock.day == 1
    assert clock.phase == DAY
    assert clock.is_night is False
    assert clock.phase_fraction == 0.0


def test_day_turns_to_night_at_the_end_of_the_day_length():
    clock = DayNight()
    clock.update(config.DAY_LENGTH - 1)
    assert clock.phase == DAY
    clock.update(1)
    assert clock.phase == NIGHT
    assert clock.is_night is True
    assert clock.day == 1  # still the same day


def test_the_day_counter_rolls_over_after_a_full_cycle():
    clock = DayNight()
    clock.update(config.DAY_TOTAL)
    assert clock.day == 2
    assert clock.phase == DAY
    assert clock.elapsed == 0.0


def test_a_huge_step_advances_several_days_without_drifting():
    # The fixed timestep means this never happens in play, but a clock that
    # loses the remainder on a big step would drift, and that is worth pinning.
    clock = DayNight()
    clock.update(config.DAY_TOTAL * 3 + 10)
    assert clock.day == 4
    assert clock.elapsed == 10


def test_phase_fraction_runs_zero_to_one_within_each_phase():
    clock = DayNight()
    clock.update(config.DAY_LENGTH / 2)
    assert clock.phase_fraction == 0.5
    clock.update(config.DAY_LENGTH / 2 + config.NIGHT_LENGTH / 4)
    assert clock.phase == NIGHT
    assert clock.phase_fraction == 0.25


def test_many_small_steps_match_one_big_step():
    fine = DayNight()
    for _ in range(600):
        fine.update(config.FIXED_DT)
    coarse = DayNight()
    coarse.update(600 * config.FIXED_DT)
    assert fine.day == coarse.day
    assert abs(fine.elapsed - coarse.elapsed) < 1e-6
