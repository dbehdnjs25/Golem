"""Shared plumbing for the tuning scripts.

These are DEV TOOLS, not part of the game. Nothing in ``src/game`` imports
them, so a knob turned here cannot leak into a build -- which is the whole
reason they live in their own folder instead of behind a debug key.

Each script next to this one changes one number and then starts the real game
with the real window. You are playing the actual game, just with that number
set to whatever you asked for.

Why they set the number on the OBJECT rather than on ``config``: the dataclass
defaults -- ``speed: float = config.PLAYER_SPEED`` and the rest -- are read
once, when the class is created at import time. Reassigning the constant
afterwards changes nothing at all, silently, which is the worst kind of knob.
"""

from __future__ import annotations

import sys
from collections.abc import Callable

from game.core.app import Game
from game.items.tools import WeaponTool
from game.scenes.play import PlayScene


def number(default: float) -> float:
    """The value asked for on the command line, or ``default``."""
    if len(sys.argv) < 2:
        return default
    try:
        return float(sys.argv[1])
    except ValueError:
        sys.exit(f"'{sys.argv[1]}' is not a number")


def weapon_of(scene: PlayScene) -> WeaponTool:
    """The weapon the player starts holding."""
    for slot in scene.hotbar.slots:
        if isinstance(slot, WeaponTool):
            return slot
    raise SystemExit("no weapon in the hotbar; the scene's opening kit changed")


def run(
    label: str,
    value: float,
    tune: Callable[[PlayScene], None],
    scene: PlayScene | None = None,
) -> None:
    """Build a scene, turn the one knob, say so, and play.

    ``scene`` is for the scripts that need a scene set up before the knob --
    standing somewhere, or a subclass that changes a rule.
    """
    scene = PlayScene() if scene is None else scene
    tune(scene)
    print(f"{label} = {value:g}")
    Game().run(scene)
