"""Play with a bigger or smaller health bar.

    python dev/maxhp.py 1000

The ceiling only. Everything that hurts -- lava, a mire run dry, a golem's
touch, a boss -- still hits for what it hits for, so this buys time rather
than safety.
"""

from __future__ import annotations

from _launch import number, run

from game import config


def _tune(scene) -> None:
    scene.player.max_hp = health
    scene.player.hp = health  # start full; the bar reads as a fraction of max


if __name__ == "__main__":
    health = number(config.PLAYER_MAX_HP * 10)
    run("max hp", health, _tune)
