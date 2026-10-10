"""A crafting station, standing where it was put.

Stations only go inside the ward. That is one of the three reasons the spec
gives for coming home at all -- the others being full slots and an empty health
bar -- so the rule is load-bearing rather than flavour.

The blast furnace additionally wants a wide ward. It takes up room, and that
requirement is what puts steel behind levelling the core rather than behind
grinding more ore.

Placement and lookup are free functions over a list rather than methods on a
manager: there is no state to keep between them, and the scene already owns
the list.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config
from game.entities.core import Core
from game.items.item_kinds import BLAST_FURNACE, ItemKind
from game.items.recipes import NOWHERE, STATION_OF


@dataclass
class Station:
    pos: pygame.Vector2
    kind: ItemKind


def can_place(kind: ItemKind, at: pygame.Vector2, built: list[Station], core: Core) -> bool:
    """Whether ``kind`` may stand at ``at`` right now."""
    if not core.is_in_ward(at):
        return False
    if kind is BLAST_FURNACE and core.ward_radius < config.BLAST_FURNACE_MIN_WARD:
        return False
    return all(s.pos.distance_to(at) > config.STATION_RADIUS * 2 for s in built)


def place(kind: ItemKind, at: pygame.Vector2, built: list[Station], core: Core) -> bool:
    """Put one down. Returns False and changes nothing if it cannot stand there."""
    if not can_place(kind, at, built, core):
        return False
    built.append(Station(pos=pygame.Vector2(at), kind=kind))
    return True


def stations_at(pos: pygame.Vector2, built: list[Station]) -> set[str]:
    """Every bench open to someone standing at ``pos``.

    A set rather than a winner, because stations are not one ladder. A bench
    and a fine bench are, but a smelter and a hearth are different jobs -- so
    standing between two means both lists are open, and nothing has to be
    ranked against something it has no relation to.

    ``NOWHERE`` is always in it: an empty hand works anywhere.
    """
    open_here = {NOWHERE}
    for station in built:
        if pos.distance_to(station.pos) <= config.STATION_REACH:
            open_here |= STATION_OF.get(station.kind, set())
    return open_here
