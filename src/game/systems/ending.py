"""Whether the run is over, and how.

Two ways out. The core is ground to nothing, or the player lives through the
night that comes after the fifth sigil is carried home. Both were missing: the
scene set a ``defeated`` flag nobody read, and winning had no shape at all.

Pure, like the raid calendar it sits beside. It is handed three facts a step --
how many sigils are home, whether it is night, whether the core is gone -- and
it owns nothing else, so "does surviving the last night win" is a question a
test can ask in one line.

An ending is FINAL. Not because anything would obviously go wrong otherwise,
but because a run that could un-lose itself is a run whose ending the player
cannot trust.
"""

from __future__ import annotations

from dataclasses import dataclass

from game import config

WON = "won"
LOST = "lost"


@dataclass
class Ending:
    outcome: str | None = None
    # Whether the last night is happening right now. The scene reads this to
    # break the ward and to throw everything the player has beaten at them,
    # which is why it is not simply derived at the moment of asking: the night
    # has to end for the morning to mean anything.
    standing: bool = False

    @property
    def over(self) -> bool:
        return self.outcome is not None

    def update(self, *, sigils_taken: int, is_night: bool, core_destroyed: bool) -> None:
        """Advance one step. A no-op once the run has ended."""
        if self.over:
            return
        if core_destroyed:
            # Losing beats winning in the same step, and losing ON the last
            # night is still losing -- which is the whole tension of it.
            self.outcome = LOST
            self.standing = False
            return
        called = sigils_taken >= config.SIGILS_TO_END
        if called and is_night:
            self.standing = True
        elif self.standing and not is_night:
            # Morning. Nothing is asked of the player but to have been alive
            # for it.
            self.standing = False
            self.outcome = WON
