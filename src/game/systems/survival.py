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
from game.entities.mire import Mire
from game.entities.player import Player
from game.systems import status
from game.world import lava, mires


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
        # And it stays alight after. Relit every frame while in it, so the
        # clock starts over from the moment of stepping out.
        status.ignite(player)


def update_stamina(dt: float, player: Player, regen_mult: float = 1.0) -> None:
    """Let wind come back, once the player has stopped spending it.

    The hold is what makes the cost real: without it a dodge would be paid for
    and refunded inside the same second.

    ``regen_mult`` is how the wasteland's sandstorm slows the breath without
    stopping it. Everywhere else simply leaves it alone.
    """
    if player.stamina_hold > 0:
        player.stamina_hold = max(0.0, player.stamina_hold - dt)
        return
    gain = config.STAMINA_REGEN * regen_mult * dt
    player.stamina = min(player.max_stamina, player.stamina + gain)


def update_mire(dt: float, player: Player, pools: list[Mire], moving: bool) -> None:
    """Wading a mire takes breath. Standing in one gets none back.

    This is the bog's gimmick, and it takes BREATH rather than blood -- which
    makes it a nuisance to a player who has cooked and stocked up and a trap
    to one who has not, with no damage number to balance.

    Three rules, all pulling the same way. Only moving costs breath, so a
    player who stops is not actively losing; a mire holds the recovery off
    whether they move or not, so stopping buys nothing; and once the breath is
    gone it starts taking blood instead, standing or not.

    So there is no waiting a mire out. The way through is out of it, or a
    meal, and the sinking is slow enough that walking to the edge of even a
    wide one on an empty tank is survivable.
    """
    if player.hp <= 0 or not mires.holds(player.pos, pools):
        return
    # First, unconditionally: a mire gives nothing back, moving or still,
    # empty or not. Everything below only decides what it TAKES.
    player.stamina_hold = config.STAMINA_DELAY
    if player.winded:
        # Nothing left to wade with. Standing still does not help here, which
        # is the point: stopping was never an answer in a mire.
        player.hp -= config.MIRE_SINK_DPS * dt
    elif moving:
        player.drain(config.MIRE_DRAIN * dt)
