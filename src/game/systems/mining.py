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
from game.items import grades
from game.items.item_kinds import ItemKind
from game.items.tools import MiningTool
from game.systems import carrying

IDLE = "idle"
MINING = "mining"
OUT_OF_RANGE = "out_of_range"
FULL = "full"
WRONG_TOOL = "wrong_tool"  # an axe at ore, a pickaxe at a tree
TOO_HARD = "too_hard"  # the right family, too low a grade
COLLECTED = "collected"


def pick_target(
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
    target = pick_target(aim_world, player_pos, fragments, active_tool.range)
    if target is None:
        return OUT_OF_RANGE, None
    # Qualification is checked BEFORE any damage lands. A node that cannot be
    # finished must not be left half-chewed, or an unreachable ore sits there
    # ruined for whoever comes back with the right tool.
    need = grades.need_for(target.kind)
    if active_tool.family != need.family:
        return WRONG_TOOL, None
    if active_tool.grade.rank < need.grade.rank:
        return TOO_HARD, None
    if carrying.room_for(target.kind, backpack, hotbar) == 0:
        return FULL, None  # block before damaging -> the node is preserved
    if target.damage(active_tool.dps * dt):
        carrying.store(target.kind, 1, backpack, hotbar)
        fragments.remove(target)
        return COLLECTED, target.kind
    return MINING, None


def can_take(tool: object, kind: ItemKind) -> bool:
    """Whether ``tool`` is allowed at a node of ``kind`` at all.

    The same two checks ``update_mining`` makes, exposed so the scene can show
    an unusable node without duplicating the rule and drifting from it.
    """
    if not isinstance(tool, MiningTool):
        return False
    need = grades.need_for(kind)
    return tool.family == need.family and tool.grade.rank >= need.grade.rank
