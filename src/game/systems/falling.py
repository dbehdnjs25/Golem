"""Going over the edge on the wind plateau.

A fall costs health and puts the player back on solid ground. It does not keep
them: the point of a hole is being pushed into one, not dying at the bottom,
and a death pit would simply make the biome unvisitable.

Nothing is dropped. Losing a full pack to a stumble would mean nobody ever
walked out there with anything worth carrying, which is the opposite of what
terrain is for.

The cost is once per fall, not once per frame. Set down on the rim, a
per-frame rule would shake someone to death while they stood still.
"""

from __future__ import annotations

import pygame

from game import config
from game.entities.chasm import Chasm
from game.entities.player import Player
from game.world import chasms


def update_fall(dt: float, player: Player, holes: list[Chasm]) -> bool:
    """Catch the player if the ground is not there. True if they fell."""
    if player.hp <= 0:
        return False  # left where they lie
    hole = chasms.over(player.pos, holes)
    if hole is None:
        return False
    player.hp -= config.FALL_DAMAGE
    _set_down(player, hole, holes)
    return True


def _set_down(player: Player, hole: Chasm, holes: list[Chasm]) -> None:
    """Put them back outside the rim, and not inside the next hole along.

    Pushed straight out from the centre, which is the shortest way to ground
    and keeps the direction they fell from -- being teleported across a chasm
    would be a worse surprise than the fall.
    """
    away = player.pos - hole.pos
    if away.length_squared() == 0:
        away = pygame.Vector2(1, 0)
    step = away.normalize()
    for push in range(1, config.FALL_SET_DOWN_TRIES + 1):
        spot = hole.pos + step * (hole.radius + config.FALL_CLEARANCE * push)
        if chasms.over(spot, holes) is None:
            player.pos.update(spot)
            return
    # Every way out lands in another hole: leave them on this rim rather than
    # somewhere arbitrary. The next step will simply catch them again.
    player.pos.update(hole.pos + step * (hole.radius + config.FALL_CLEARANCE))
