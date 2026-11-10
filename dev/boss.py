"""Stand at a temple's altar, unkillable, and press E.

    python dev/boss.py        the burnt forest
    python dev/boss.py 2      the snowfield, and so on to 5

Skips the three minutes of walking and the guards, because what this is for is
watching a boss, not reaching one. The player cannot be hurt: every frame the
dodge's own invulnerability is topped back up, so you are free to stand in
everything and see what it actually does.

Being unhurtable is not the same as being untouched -- the arm still drags you
in and the charge still shoves past -- which is the point. You want to see
where the blows land, and the fastest way to see that is to not die to them.
"""

from __future__ import annotations

import sys

import pygame
from _launch import run

from game import config
from game.scenes.play import PlayScene


class Unkillable(PlayScene):
    """A play scene whose player is permanently mid-dodge."""

    def update(self, dt: float) -> None:
        super().update(dt)
        self.player.iframe_timer = 999.0
        self.player.stamina = self.player.max_stamina


def _at_the_altar(scene: PlayScene, which: int) -> None:
    temple = scene.temples[which]
    temple.guards_down = True  # the guards are a different afternoon
    scene.core.ignite()
    # Walking in is what draws the room, so step inside and let one frame run
    # before asking where the altar ended up.
    scene.player.pos.update(temple.pos + pygame.Vector2(temple.radius * 0.6, 0))
    scene.update(config.FIXED_DT)
    assert temple.layout is not None
    scene.player.pos.update(temple.layout.altar)
    scene.camera.center_on(scene.player.pos)
    print(f"{temple.biome.name} 사원 · 제단 위 · E를 누르세요")


if __name__ == "__main__":
    picked = int(sys.argv[1]) - 1 if len(sys.argv) > 1 else 0
    scene = Unkillable()
    _at_the_altar(scene, picked)
    run("boss", picked + 1, lambda _s: None, scene=scene)
