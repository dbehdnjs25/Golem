"""One mining step.

There is no cursor: every node in the fan in front of the player, within the
tool's reach, is dug at once. Each is checked on its own -- the wrong tool for
one does not stop the others -- and the tool's full rate goes into every one
of them. Wind is paid once per step, not once per node: it is the arm that
tires, and the arm swings once.

Returns ``(status, kinds)`` -- the kinds that came out this step, because a
backpack is worn the moment it is dug up rather than stored, so the scene has
to be told what came out.

Nowhere to put it blocks the swing at that node BEFORE any damage lands, so
the node is preserved rather than destroyed into a full pack.
"""

from __future__ import annotations

import pygame

from game import config
from game.entities.fragment import Fragment
from game.entities.player import Player
from game.inventory.hotbar import Hotbar
from game.inventory.storage import Container
from game.items import grades
from game.items.item_kinds import ItemKind, yield_of
from game.items.tools import BARE_HAND, MiningTool
from game.systems import aim, carrying

IDLE = "idle"
MINING = "mining"
OUT_OF_RANGE = "out_of_range"
FULL = "full"
WRONG_TOOL = "wrong_tool"  # an axe at ore, a pickaxe at a tree
TOO_HARD = "too_hard"  # the right family, too low a grade
COLLECTED = "collected"


def targets(
    facing: pygame.Vector2,
    player_pos: pygame.Vector2,
    fragments: list[Fragment],
    reach: float,
) -> list[Fragment]:
    """The live nodes in the fan in front of the player, nearest first."""
    live = [f for f in fragments if not f.is_depleted]
    return aim.in_front(player_pos, facing, live, reach)


def update_mining(
    dt: float,
    *,
    active_tool: object | None,
    held: bool,
    facing: pygame.Vector2,
    player_pos: pygame.Vector2,
    fragments: list[Fragment],
    backpack: Container | None,
    hotbar: Hotbar,
    player: Player | None = None,
    swing_timer: float = 0.0,
) -> tuple[str, list[ItemKind], float]:
    """One step of digging: a blow on its beat, not a continuous drain.

    Holding the key used to be a hose -- the number went down for as long as
    it was down, with nothing to see or hear. A tool lands on a beat now. The
    bite each blow takes is the rate times the beat, so a run of digging
    costs what it always did and only the shape of it changed.

    The timer runs down whether or not the key is held and whether or not the
    blow found anything, so letting go and pressing again buys nothing. The
    first blow of a press lands at once: a tool that waited before its first
    swing would feel broken rather than weighty.
    """
    swing_timer = max(0.0, swing_timer - dt)
    if not held:
        return IDLE, [], swing_timer
    if active_tool is None:
        active_tool = BARE_HAND  # nothing in hand is still a pair of hands
    if not isinstance(active_tool, MiningTool):
        return IDLE, [], swing_timer
    in_reach = targets(facing, player_pos, fragments, active_tool.range)
    if not in_reach:
        return OUT_OF_RANGE, [], swing_timer
    refused: str | None = None
    reachable = False
    for target in in_reach:
        why = _refusal(active_tool, target.kind, backpack, hotbar)
        if why is not None:
            refused = refused or why  # the nearest one's reason is the one shown
        else:
            reachable = True
    if not reachable:
        return refused or OUT_OF_RANGE, [], swing_timer
    if swing_timer > 0:
        return MINING, [], swing_timer  # mid-beat: the arm is still coming round

    bite = active_tool.dps * config.MINING_SWING
    if player is not None and player.winded:
        # Running out slows digging rather than stopping it. Blocked outright,
        # someone who came out for one bagful would be left standing still.
        bite *= config.WINDED_MINING_RATE
    collected: list[ItemKind] = []
    for target in in_reach:
        if _refusal(active_tool, target.kind, backpack, hotbar) is not None:
            continue
        if target.damage(bite):
            got = yield_of(target.kind)
            carrying.store(got, 1, backpack, hotbar)
            fragments.remove(target)
            collected.append(got)
    if player is not None:
        player.drain(config.MINING_DRAIN * config.MINING_SWING)
    return (COLLECTED if collected else MINING), collected, config.MINING_SWING


def _refusal(
    tool: MiningTool, kind: ItemKind, backpack: Container | None, hotbar: Hotbar
) -> str | None:
    """Why ``tool`` may not touch a node of ``kind`` right now, or None.

    Checked BEFORE any damage lands. A node that cannot be finished must not be
    left half-chewed, or an unreachable ore sits there ruined for whoever comes
    back with the right tool.
    """
    need = grades.need_for(kind)
    if not _suits(tool.family, need.family):
        return WRONG_TOOL
    if tool.grade.rank < need.grade.rank:
        return TOO_HARD
    # What comes out may not be what was swung at: the studded stone by the
    # lava gives obsidian.
    if carrying.room_for(yield_of(kind), backpack, hotbar) == 0:
        return FULL
    return None


def _suits(family: str, wanted: str) -> bool:
    """Whether a tool of ``family`` may be swung at something wanting ``wanted``.

    Anything suits a HAND job -- that is what makes wood gatherable with nothing
    in hand, which is where every run has to start.
    """
    return wanted == grades.HAND or family == wanted


def can_take(tool: object, kind: ItemKind) -> bool:
    """Whether ``tool`` is allowed at a node of ``kind`` at all.

    The same two checks ``update_mining`` makes, exposed so the scene can show
    an unusable node without duplicating the rule and drifting from it. ``None``
    means an empty hand, which can still take litter.
    """
    if tool is None:
        tool = BARE_HAND
    if not isinstance(tool, MiningTool):
        return False
    need = grades.need_for(kind)
    return _suits(tool.family, need.family) and tool.grade.rank >= need.grade.rank
