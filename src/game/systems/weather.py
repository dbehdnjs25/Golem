"""Weather, as a function of the clock.

One storm: the wasteland's sandstorm, which slows the breath coming back. It
does no damage. It makes a place harder to be in rather than harder to
survive.

Read off ``DayNight.elapsed`` rather than rolled, because a gust rolled every
frame flickers instead of gusting -- and because a pure function of the time
needs no seed, no state, and no reset when a scene is rebuilt.

The snowfield had a blizzard here once, shortening what could be seen. It was
replaced by ice, which takes grip instead: a hazard that is read at its edge
and then committed to beats one that simply hides the map.
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


def sandstorm_at(elapsed: float) -> float:
    return _gust(elapsed, config.SANDSTORM_PERIOD, config.SANDSTORM_OFFSET)


def regen_mult(strength: float) -> float:
    """How fast breath comes back in a sandstorm of ``strength``.

    Never zero. The bog is already the place where nothing comes back at all,
    and two places doing the same thing would leave one of them spare -- the
    wasteland slows the recovery rather than stopping it.
    """
    strength = max(0.0, min(1.0, strength))
    span = 1.0 - config.WASTELAND_REGEN_FLOOR
    return 1.0 - span * strength
