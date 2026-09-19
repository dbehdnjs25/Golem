from game.items import grades
from game.items.grades import AXE, GRADES, PICKAXE
from game.items.item_kinds import (
    COPPER_ORE,
    GOLD_ORE,
    IRON_ORE,
    ITEM_KINDS,
    OBSIDIAN,
    POTION,
    STONE,
    WOOD,
    ZINC_ORE,
)


def test_the_ladder_runs_from_wood_to_steel():
    assert [g.key for g in GRADES] == [
        "wood",
        "stone",
        "copper",
        "iron",
        "gold",
        "brass",
        "steel",
    ]


def test_rank_and_speed_both_climb_with_the_ladder():
    assert [g.rank for g in GRADES] == list(range(len(GRADES)))
    speeds = [g.speed for g in GRADES]
    assert speeds == sorted(speeds)
    assert len(set(speeds)) == len(speeds)  # every step is worth taking


def test_stone_and_copper_only_need_a_wooden_pick():
    # This is what lets the opening work: wood makes the first tool, and the
    # first tool opens the first two ores.
    for kind in (STONE, COPPER_ORE):
        need = grades.need_for(kind)
        assert need.family == PICKAXE
        assert need.grade is grades.WOOD_G


def test_the_gates_climb_with_the_ore():
    assert grades.need_for(IRON_ORE).grade is grades.COPPER_G
    assert grades.need_for(GOLD_ORE).grade is grades.IRON_G
    assert grades.need_for(ZINC_ORE).grade is grades.IRON_G


def test_biome_materials_are_what_gold_is_for():
    # Ore stops at gold, so without this the top three grades would open
    # nothing at all and be a speed bonus dressed as a ladder.
    assert grades.need_for(OBSIDIAN).grade is grades.GOLD_G


def test_wood_wants_an_axe_at_the_bottom_of_the_ladder():
    need = grades.need_for(WOOD)
    assert need.family == AXE
    assert need.grade is GRADES[0]


def test_every_ore_wants_a_pickaxe():
    for kind, need in grades.NEEDS.items():
        if kind is not WOOD:
            assert need.family == PICKAXE


def test_the_table_only_names_real_catalogue_rows():
    for kind in grades.NEEDS:
        assert ITEM_KINDS[kind.key] is kind


def test_something_not_in_the_table_needs_nothing_special():
    assert grades.need_for(POTION).grade is GRADES[0]


def test_a_grade_can_be_compared_to_another():
    assert grades.IRON_G.rank > grades.COPPER_G.rank
    assert grades.WOOD_G.rank < grades.STEEL_G.rank
