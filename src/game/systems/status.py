"""Things that stay on the player after whatever caused them has stopped.

Only burning so far. Lava lights it and it keeps going for a few seconds
afterwards, which is what makes stepping out of a pool a relief rather than an
off switch -- and the burnt forest's supreme glyph is "the ground it crosses
keeps burning", so this is what that will light too.

Lighting an already-lit player REFRESHES rather than stacks. Standing in lava
relights every frame, and stacking would turn a two-second wade into a minute
of burning; a longer fire already running is not cut short by a shorter one
either.
"""

from __future__ import annotations

from game import config
from game.entities.player import Player


def ignite(player: Player, seconds: float = config.BURN_SECONDS) -> None:
    player.burn_timer = max(player.burn_timer, seconds)


def update_burn(dt: float, player: Player) -> None:
    """Tick the fire down and bill for the time it was alight.

    Billed for the burn's own remaining time rather than for ``dt``: handed a
    step longer than the fire has left, charging the whole step would cost
    more than the fire ever did.
    """
    if player.burn_timer <= 0 or player.hp <= 0:
        return
    alight = min(dt, player.burn_timer)
    player.burn_timer -= alight
    # Floored at one: burning is a tail on something else, not an execution in
    # its own right, and dying to the last tick of a fire you already escaped
    # reads as being cheated.
    player.hp = max(1.0, player.hp - config.BURN_DPS * alight)
