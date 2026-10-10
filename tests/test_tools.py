from game import config
from game.items import grades, tools
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


def test_a_bare_mining_tool_is_a_wooden_pickaxe():
    t = MiningTool()
    assert t.family == grades.PICKAXE
    assert t.grade is grades.WOOD_G


def test_a_better_grade_digs_faster():
    assert tools.pickaxe(grades.IRON_G).dps > tools.pickaxe(grades.WOOD_G).dps


def test_dps_is_the_base_rate_scaled_by_the_grade():
    assert tools.pickaxe(grades.COPPER_G).dps == config.MINING_DPS * grades.COPPER_G.speed


def test_the_name_says_the_grade_and_the_family():
    assert tools.pickaxe(grades.IRON_G).name == "철 곡괭이"
    assert tools.axe(grades.WOOD_G).name == "나무 도끼"


def test_an_axe_is_a_different_family_from_a_pickaxe():
    assert tools.axe(grades.WOOD_G).family != tools.pickaxe(grades.WOOD_G).family


def test_tools_are_frozen():
    import dataclasses

    import pytest

    with pytest.raises(dataclasses.FrozenInstanceError):
        tools.pickaxe(grades.WOOD_G).grade = grades.STEEL_G  # type: ignore[misc]


def test_every_grade_can_make_both_families():
    for grade in grades.GRADES:
        assert tools.pickaxe(grade).grade is grade
        assert tools.axe(grade).grade is grade


def test_a_tool_item_says_which_tool_it_is():
    for grade, item in grades.PICK_OF.items():
        made = tools.tool_for(item)
        assert isinstance(made, MiningTool)
        assert made.family == grades.PICKAXE
        assert made.grade is grade


def test_an_ordinary_item_is_not_a_tool():
    from game.items.item_kinds import STONE

    assert tools.tool_for(STONE) is None
