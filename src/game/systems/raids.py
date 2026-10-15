"""When the raids fall.

Pure arithmetic over two numbers: what day it is, and how many bosses are
down. No clock, no state, nothing to tick -- so "what happens on day forty"
is a question a test can ask in one line.

The spec ties the calendar to progress rather than to a difficulty dial. Every
boss killed takes a day off the gap, so the nights crowd in as the player gets
stronger and the whole thing reads as "you are paying for this".
"""

from __future__ import annotations

from game import config


def interval(bosses_killed: int) -> int:
    """How many days between raids, given how many bosses are down.

    Clamped at the end of the table. Nothing should be able to kill a sixth
    boss, but an index error here would crash the last minutes of a run --
    the worst place in the game to find one.
    """
    if bosses_killed < 0:
        raise ValueError(f"bosses_killed cannot be negative: {bosses_killed}")
    return config.RAID_INTERVALS[min(bosses_killed, len(config.RAID_INTERVALS) - 1)]


def days_until(day: int, bosses_killed: int) -> int:
    """Days left before the next raid. Zero means tonight.

    Day 1 counts as a cycle that has only just begun, so it answers a whole
    interval rather than zero. That is not a special case bolted on to keep the
    first night quiet -- it is what makes the first night quiet, and it is why
    this and ``is_raid_night`` can never disagree about which night it is.
    A raid before the player owns a pick is not difficulty, it is a joke.
    """
    every = interval(bosses_killed)
    elapsed = day - 1
    return every if elapsed == 0 else -elapsed % every


def is_raid_night(day: int, bosses_killed: int) -> bool:
    return days_until(day, bosses_killed) == 0
