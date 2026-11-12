"""Start holding a staff, knowing every shape.

    python dev/magic.py          every shape, out in the grassland
    python dev/magic.py 1        the same, standing on the burnt forest's altar

Finding seventeen shapes takes a run. Drawing them takes a minute, and a minute
is what this is for: the shapes are listed down the right-hand edge, what you
are drawing shows in the corner, and the arrow keys are the whole interface.

The player is unkillable when a boss number is given, because the point then is
watching what the shapes do rather than surviving what the boss does.
"""

from __future__ import annotations

import sys

import pygame
from _launch import run

from game import config
from game.items import glyphs as glyph_table
from game.items.item_kinds import STAFF_ITEM
from game.scenes.play import PlayScene


class Unkillable(PlayScene):
    def update(self, dt: float) -> None:
        super().update(dt)
        self.player.iframe_timer = 999.0


def _arm(scene: PlayScene) -> None:
    """A staff in hand, and every shape already found."""
    scene.core.ignite()
    scene.hotbar.add(STAFF_ITEM, 1)
    for index, slot in enumerate(scene.hotbar.slots):
        if getattr(slot, "kind", None) is STAFF_ITEM:
            scene.hotbar.select(index)
            break
    for glyph in glyph_table.GLYPHS:
        scene.grimoire.learn(glyph)


def _at_the_altar(scene: PlayScene, which: int) -> None:
    temple = scene.temples[which]
    temple.guards_down = True
    scene.player.pos.update(temple.pos + pygame.Vector2(temple.radius * 0.6, 0))
    scene.update(config.FIXED_DT)  # walking in is what draws the room
    assert temple.layout is not None
    scene.player.pos.update(temple.layout.altar)
    scene.camera.center_on(scene.player.pos)
    print(f"{temple.biome.name} 사원 · 제단 위 · E를 누르세요")


if __name__ == "__main__":
    picked = int(sys.argv[1]) - 1 if len(sys.argv) > 1 else None
    scene: PlayScene = PlayScene() if picked is None else Unkillable()
    _arm(scene)
    if picked is not None:
        _at_the_altar(scene, picked)
    print("방향키로 긋고 0.4초 멈추면 나갑니다 · 오른쪽 목록이 아는 모양")
    run("shapes", len(scene.grimoire.learned), lambda _s: None, scene=scene)
