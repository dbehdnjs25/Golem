"""Staying alive: healing inside the ward.

Pure functions over injected state, like the rest of ``systems/``.

There is no healing in the field at all. The ward is the only place HP comes
back for free, and it comes back slowly at first -- the rate climbs the longer
the player stays and resets the moment they step out, so touching the edge
between fights banks nothing. Potions stay worth carrying because they are the
only healing that is instant.
"""

from __future__ import annotations

from game import config
from game.entities.core import Core
from game.entities.player import Player


def update_regen(dt: float, player: Player, core: Core) -> None:
    """Heal the player if they are inside the ward, at a rate that ramps up."""
    if player.hp <= 0 or not core.is_in_ward(player.pos):
        player.ward_time = 0.0
        return
    rate = min(
        config.WARD_REGEN_MAX,
        config.WARD_REGEN_BASE + config.WARD_REGEN_RAMP * player.ward_time,
    )
    player.ward_time += dt
    player.hp = min(player.max_hp, player.hp + rate * dt)
