import pygame

from game.entities.projectile import Projectile
from game.items.tools import MiningTool, WeaponTool
from game.systems import combat


def _fire(steps, dt, *, held=True, weapon=None):
    weapon = weapon or WeaponTool(fire_rate=2.0)  # interval 0.5s
    timer = 0.0
    shots = []
    for _ in range(steps):
        timer, new = combat.fire_weapon(
            dt,
            weapon=weapon,
            held=held,
            aim_world=pygame.Vector2(100, 0),
            player_pos=pygame.Vector2(0, 0),
            fire_timer=timer,
        )
        shots.extend(new)
    return shots


def test_fires_at_fire_rate_when_held():
    shots = _fire(steps=4, dt=0.5)  # dt == interval -> one shot per step
    assert len(shots) == 4
    assert all(isinstance(s, Projectile) for s in shots)


def test_projectile_aims_at_target():
    shots = _fire(steps=1, dt=0.5)
    assert shots[0].vel.x > 0 and shots[0].vel.y == 0


def test_no_fire_when_not_held():
    assert _fire(steps=4, dt=0.5, held=False) == []


def test_no_fire_with_non_weapon_tool():
    assert _fire(steps=4, dt=0.5, weapon=MiningTool()) == []


def test_no_fire_on_degenerate_aim():
    timer, shots = combat.fire_weapon(
        0.5,
        weapon=WeaponTool(fire_rate=2.0),
        held=True,
        aim_world=pygame.Vector2(0, 0),
        player_pos=pygame.Vector2(0, 0),
        fire_timer=0.0,
    )
    assert shots == []
