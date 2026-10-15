from game.items import grades
from game.items.grades import AXE, GRADES, PICKAXE
from game.items.item_kinds import (
    COPPER_ORE,
    GOLD_ORE,
    IRON_ORE,
    ITEM_KINDS,
    POTION,
    STONE,
    TWIG,
    WOOD,
    ZINC_ORE,
)


def test_the_ladder_runs_from_wood_to_steel():
    assert [g.key for g in GRADES] == [
        "crude",
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
    # Obsidian itself is never swung at -- the studded stone by the lava is.
    assert grades.need_for(ITEM_KINDS["obsidian_stone"]).grade is grades.GOLD_G


def test_only_litter_answers_to_an_empty_hand():
    # The bootstrap. A twig, a pebble and some grass are all a player with
    # nothing can take, and together they make the axe that fells the first
    # tree. Everything else demands a tool.
    from game.items.item_kinds import GRASS, PEBBLE

    hand_jobs = {k for k, need in grades.NEEDS.items() if need.family == grades.HAND}
    assert hand_jobs == {TWIG, PEBBLE, GRASS}


def test_a_tree_wants_an_axe_and_the_crude_one_counts():
    need = grades.need_for(WOOD)
    assert need.family == AXE
    assert need.grade is grades.CRUDE_G


def test_every_ore_wants_a_pickaxe():
    # Everything that is dug rather than gathered or felled.
    from game.items.item_kinds import GRASS, PEBBLE

    # Charred wood is a tree, not ore -- burnt or not, an axe is what fells it.
    gathered = {TWIG, PEBBLE, GRASS, WOOD, ITEM_KINDS["charred_wood"]}
    for kind, need in grades.NEEDS.items():
        if kind not in gathered:
            assert need.family == PICKAXE


def test_the_table_only_names_real_catalogue_rows():
    for kind in grades.NEEDS:
        assert ITEM_KINDS[kind.key] is kind


def test_something_not_in_the_table_needs_nothing_special():
    assert grades.need_for(POTION).grade is GRADES[0]


def test_a_grade_can_be_compared_to_another():
    assert grades.IRON_G.rank > grades.COPPER_G.rank
    assert grades.WOOD_G.rank < grades.STEEL_G.rank


def test_every_grade_but_the_crude_one_has_both_families():
    # Crude is a branch and a stone. Enough to hack at a tree, nowhere near
    # enough to break rock -- so there is no crude pickaxe to have.
    for grade in GRADES:
        assert grade in grades.AXE_OF
        assert (grade in grades.PICK_OF) is (grade is not grades.CRUDE_G)


def test_tool_items_map_back_to_their_family_and_grade():
    for grade, item in grades.PICK_OF.items():
        assert grades.TOOL_ITEMS[item] == (PICKAXE, grade)
    for grade, item in grades.AXE_OF.items():
        assert grades.TOOL_ITEMS[item] == (grades.AXE, grade)


def test_a_tool_item_is_never_mistaken_for_two_things():
    assert len(grades.TOOL_ITEMS) == len(GRADES) + len(GRADES) - 1  # no crude pick


def test_tool_items_are_real_catalogue_rows_that_do_not_stack():
    for item in grades.TOOL_ITEMS:
        assert ITEM_KINDS[item.key] is item
        assert item.stack_max == 1  # you hold one, you do not hoard them
