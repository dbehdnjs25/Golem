"""The day/night clock. Pure: it advances only on the ``dt`` it is handed, never
on a wall clock, so a run is reproducible and the whole thing is testable
headlessly.

``elapsed`` is the position within the current day, not since the start of the
run -- keeping it bounded means a long session cannot lose precision in it.
"""

from __future__ import annotations

from dataclasses import dataclass

from game import config

DAY = "day"
NIGHT = "night"


@dataclass
class DayNight:
    elapsed: float = 0.0  # seconds into the current day, 0 <= elapsed < DAY_TOTAL
    day: int = 1

    def update(self, dt: float) -> None:
        self.elapsed += dt
        while self.elapsed >= config.DAY_TOTAL:
            self.elapsed -= config.DAY_TOTAL
            self.day += 1

    @property
    def phase(self) -> str:
        return DAY if self.elapsed < config.DAY_LENGTH else NIGHT

    @property
    def is_night(self) -> bool:
        return self.phase == NIGHT

    @property
    def phase_fraction(self) -> float:
        """How far through the current phase, 0.0 to 1.0."""
        if self.elapsed < config.DAY_LENGTH:
            return self.elapsed / config.DAY_LENGTH
        return (self.elapsed - config.DAY_LENGTH) / config.NIGHT_LENGTH
