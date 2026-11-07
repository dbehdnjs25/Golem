"""Play with a bigger or smaller wind.

    python dev/stamina.py 400

The ceiling only. What spends it -- dodging, sprinting, mining, a mire -- is
unchanged, so a larger number buys more of each at the rates the game charges.
"""

from __future__ import annotations

from _launch import number, run

from game import config


def _tune(scene) -> None:
    scene.player.max_stamina = wind
    scene.player.stamina = wind  # start full, or the first number read is a lie


if __name__ == "__main__":
    wind = number(config.PLAYER_MAX_STAMINA * 4)
    run("max stamina", wind, _tune)
