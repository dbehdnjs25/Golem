"""Play faster or slower on foot.

    python dev/speed.py 400

Only the walk. Sprinting still multiplies it, dodging still multiplies it, and
the wasteland still takes its cut -- all of those are factors applied to this,
so the relationships between them stay the ones the game has.
"""

from __future__ import annotations

from _launch import number, run

from game import config

if __name__ == "__main__":
    pace = number(config.PLAYER_SPEED * 2)
    run("player speed", pace, lambda scene: setattr(scene.player, "speed", pace))
