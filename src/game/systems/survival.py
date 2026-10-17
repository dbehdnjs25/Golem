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
from game.entities.lava import LavaPool
from game.entities.player import Player
from game.world import lava
from game.world.biomes import BOG
from game.world.map import WorldMap


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


def update_lava(dt: float, player: Player, pools: list[LavaPool]) -> None:
    """Burn whoever is standing in it.

    No ward check and no invulnerability check: the ward is a wall against
    things that walk, and i-frames are for blows that land. Hot ground is
    neither -- it is simply where you are standing.
    """
    if player.hp <= 0:
        return
    if lava.burns(player.pos, pools):
        player.hp -= config.LAVA_DPS * dt


def update_stamina(dt: float, player: Player) -> None:
    """Let wind come back, once the player has stopped spending it.

    The hold is what makes the cost real: without it a dodge would be paid for
    and refunded inside the same second.
    """
    if player.stamina_hold > 0:
        player.stamina_hold = max(0.0, player.stamina_hold - dt)
        return
    player.stamina = min(player.max_stamina, player.stamina + config.STAMINA_REGEN * dt)


def update_bog(dt: float, player: Player, world: WorldMap) -> None:
    """Wading drains wind, nowhere else does.

    This is why the bog sits fourth. It takes BREATH rather than blood, which
    makes it a nuisance to a player who has cooked and stocked up and a trap
    to one who has not -- exactly the gate the spec wanted, with no damage
    number to balance.

    Because draining holds the recovery off, there is no resting in a bog:
    standing still does not help and nine seconds empties a full tank. Meat is
    the only way to get breath back in there, which is where the spec's
    "recovered with meat" stops being a convenience and becomes the rule.
    """
    if player.hp <= 0:
        return
    if world.biome_at(player.pos) is BOG:
        player.drain(config.BOG_DRAIN * dt)
