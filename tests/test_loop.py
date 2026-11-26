"""Tests for the fixed-timestep accumulator (pure logic, no pygame)."""

from __future__ import annotations

import pytest

from game.core.loop import FixedTimestep


def test_accumulates_exact_steps() -> None:
    ts = FixedTimestep(dt=0.1, max_frame_time=1.0)
    assert ts.steps(0.25) == 2  # 0.25 -> two 0.1 steps, 0.05 left over
    assert ts.accumulator == pytest.approx(0.05)


def test_leftover_carries_into_next_frame() -> None:
    ts = FixedTimestep(dt=0.1, max_frame_time=1.0)
    ts.steps(0.05)  # 0 steps, 0.05 banked
    assert ts.steps(0.05) == 1  # 0.05 + 0.05 -> one step


def test_frame_time_clamped_prevents_spiral_of_death() -> None:
    ts = FixedTimestep(dt=0.1, max_frame_time=0.35)
    # A 10s hang must not produce ~100 steps; it's clamped to 0.35 -> 3 steps.
    assert ts.steps(10.0) == 3


def test_negative_frame_time_yields_no_steps() -> None:
    ts = FixedTimestep(dt=0.1, max_frame_time=1.0)
    assert ts.steps(-5.0) == 0


def test_alpha_is_normalised_fraction() -> None:
    ts = FixedTimestep(dt=0.1, max_frame_time=1.0)
    ts.steps(0.15)  # one step, 0.05 remainder
    assert ts.alpha == pytest.approx(0.5)


def test_non_positive_dt_rejected() -> None:
    with pytest.raises(ValueError):
        FixedTimestep(dt=0.0)


# --- vsync snapping --------------------------------------------------------------
# A 60 Hz display hands back frames of 14.5 to 18.7 ms, not 16.67 every time.
# Fed in raw, those wobbles add up to a frame with no step (the picture repeats)
# and then one with two (it jumps): a hitch about twice a second. A frame within
# a few milliseconds of a whole number of steps is that many steps exactly.

DT = 1 / 60


def test_a_wobbling_60hz_display_gets_exactly_one_step_a_frame() -> None:
    ts = FixedTimestep(dt=DT, max_frame_time=0.25)
    wobble = [0.0145, 0.0187, 0.0160, 0.0172, 0.0150, 0.0185, 0.0166, 0.0168] * 40
    assert {ts.steps(frame) for frame in wobble} == {1}


def test_a_frame_that_took_two_steps_long_gets_exactly_two() -> None:
    ts = FixedTimestep(dt=DT, max_frame_time=0.25)
    assert ts.steps(0.0345) == 2
    assert ts.accumulator == pytest.approx(0.0)


def test_a_frame_far_from_a_whole_step_still_banks_the_remainder() -> None:
    ts = FixedTimestep(dt=DT, max_frame_time=0.25)
    assert ts.steps(0.008) == 0  # half a step: nothing near to snap to
    assert ts.accumulator == pytest.approx(0.008)


def test_snapping_can_be_turned_off() -> None:
    ts = FixedTimestep(dt=DT, max_frame_time=0.25, snap=0.0)
    results = [ts.steps(frame) for frame in [0.0145, 0.0145, 0.0145, 0.0145, 0.0187] * 10]
    assert 0 in results  # raw accumulation: a short run comes out a step short
