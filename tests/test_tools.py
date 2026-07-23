from game import config
from game.items.tools import MiningTool, WeaponTool


def test_weapon_defaults():
    w = WeaponTool()
    assert w.damage == config.WEAPON_DAMAGE
    assert w.fire_rate == config.WEAPON_FIRE_RATE
    assert w.projectile_speed == config.PROJECTILE_SPEED
    assert isinstance(w.name, str)


def test_weapon_is_immutable_and_upgradable():
    strong = WeaponTool(damage=99, fire_rate=8, name="Overclocked")
    assert strong.damage == 99
    assert MiningTool().name != strong.name
