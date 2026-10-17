"""Storms, as a function of the clock.

Two of them: the snowfield's blizzard, which shortens what can be seen, and
the wasteland's sandstorm, which slows the breath coming back. Neither does
damage. They make a place harder to be in rather than harder to survive.

Read off ``DayNight.elapsed`` rather than rolled, because a gust rolled every
frame flickers instead of gusting -- and because a pure function of the time
needs no seed, no state, and no reset when a scene is rebuilt.

Two sine waves of different periods, offset from each other so the two storms
never march in lockstep: that would read as one effect wearing two coats.
"""

from __future__ import annotations

import math

from game import config


def _gust(elapsed: float, period: float, offset: float) -> float:
    """A 0..1 wave, flattened so it is calm more often than it is blowing.

    Squaring the raised sine keeps the peaks short and the lulls long, which
    is what makes a gust feel like an event rather than a setting.
    """
    phase = math.sin((elapsed + offset) * math.tau / period)
    return ((phase + 1.0) / 2.0) ** 2


def blizzard_at(elapsed: float) -> float:
    return _gust(elapsed, config.BLIZZARD_PERIOD, 0.0)


def sandstorm_at(elapsed: float) -> float:
    return _gust(elapsed, config.SANDSTORM_PERIOD, config.SANDSTORM_OFFSET)


def sight_radius(strength: float) -> float:
    """How far can be seen through a blizzard of ``strength``.

    Never zero. Blind is not a mechanic, it is a black screen.
    """
    strength = max(0.0, min(1.0, strength))
    span = config.BLIZZARD_SIGHT_MAX - config.BLIZZARD_SIGHT_MIN
    return config.BLIZZARD_SIGHT_MAX - span * strength


def regen_mult(strength: float) -> float:
    """How fast breath comes back in a sandstorm of ``strength``.

    Never zero. The bog is already the place where nothing comes back at all,
    and two places doing the same thing would leave one of them spare -- the
    wasteland slows the recovery rather than stopping it.
    """
    strength = max(0.0, min(1.0, strength))
    span = 1.0 - config.WASTELAND_REGEN_FLOOR
    return 1.0 - span * strength
