"""The interval accumulator shared by the time-based spawners, plus the retry cap.

Keeping the cadence rule in one place means the node and golem spawners cannot
drift apart on it. Where a spawn may land is the map's business, not this
module's -- see ``WorldMap.random_point``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SPAWN_ATTEMPTS = 20  # capped retries so a saturated world cannot hang the loop


@dataclass
class TimedSpawner:
    """Interval accumulator: ``is_due`` returns True once per ``interval`` of dt.

    It subtracts the interval rather than zeroing the accumulator, so leftover
    time carries into the next tick and the spawn rate stays exact under any
    step size."""

    interval: float
    _accumulator: float = field(default=0.0, init=False)

    def is_due(self, dt: float) -> bool:
        self._accumulator += dt
        if self._accumulator < self.interval:
            return False
        self._accumulator -= self.interval
        return True
