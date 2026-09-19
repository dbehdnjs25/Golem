"""One mining step.

The cursor picks WHICH node (nearest to the aim point) among those within the
tool's range of the PLAYER; the tool then channels damage into it. On depletion
the node is removed and what it held is handed to ``carrying``.

Returns ``(status, kind)`` -- the kind only on a collect, and only because a
backpack is worn the moment it is dug up rather than stored, so the scene has
to be told what came out.

Nowhere to put it blocks the swing BEFORE any damage lands, so the node is
preserved rather than destroyed into a full pack.
"""

from __future__ import annotations

import pygame

from game.entities.fragment import Fragment
from game.inventory.hotbar import Hotbar
from game.inventory.storage import Container
from game.items.item_kinds import ItemKind
from game.items.tools import MiningTool
from game.systems import carrying

IDLE = "idle"
MINING = "mining"
OUT_OF_RANGE = "out_of_range"
FULL = "full"
COLLECTED = "collected"


def _pick_target(
    aim_world: pygame.Vector2,
    player_pos: pygame.Vector2,
    fragments: list[Fragment],
    reach: float,
) -> Fragment | None:
    candidates = [
        f for f in fragments if not f.is_depleted and player_pos.distance_to(f.pos) <= reach
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda f: aim_world.distance_to(f.pos))


def update_mining(
    dt: float,
    *,
    active_tool: object | None,
    held: bool,
    aim_world: pygame.Vector2,
    player_pos: pygame.Vector2,
    fragments: list[Fragment],
    backpack: Container | None,
    hotbar: Hotbar,
) -> tuple[str, ItemKind | None]:
    if not held or not isinstance(active_tool, MiningTool):
        return IDLE, None
    target = _pick_target(aim_world, player_pos, fragments, active_tool.range)
    if target is None:
        return OUT_OF_RANGE, None
    if carrying.room_for(target.kind, backpack, hotbar) == 0:
        return FULL, None  # block before damaging -> the node is preserved
    if target.damage(active_tool.dps * dt):
        carrying.store(target.kind, 1, backpack, hotbar)
        fragments.remove(target)
        return COLLECTED, target.kind
    return MINING, None
