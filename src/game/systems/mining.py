"""One mining step. The cursor picks WHICH fragment (nearest to the aim point)
among those within the tool's range of the PLAYER; the tool then channels
damage into it. On depletion the fragment is removed and banked to the backpack.
A full backpack blocks mining without touching the fragment."""

from __future__ import annotations

import pygame

from game.entities.fragment import Fragment
from game.inventory.storage import Container
from game.items.tools import MiningTool

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
    backpack: Container,
) -> str:
    if not held or not isinstance(active_tool, MiningTool):
        return IDLE
    target = _pick_target(aim_world, player_pos, fragments, active_tool.range)
    if target is None:
        return OUT_OF_RANGE
    if backpack.fits(target.kind, 1) == 0:
        return FULL  # block before damaging -> fragment preserved
    if target.damage(active_tool.dps * dt):
        backpack.add(target.kind, 1)
        fragments.remove(target)
        return COLLECTED
    return MINING
