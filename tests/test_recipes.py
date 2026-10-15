from game.entities.beast import BEAST_KINDS
from game.items import grades, recipes
from game.items.item_kinds import (
    BLAST_FURNACE,
    BRASS_INGOT,
    COPPER_ORE,
    FINE_BENCH,
    GOLD_ORE,
    IRON_ORE,
    ITEM_KINDS,
    STEEL_INGOT,
    STONE,
    WOOD,
    WOOD_AXE,
    WOOD_PICK,
    ZINC_ORE,
)

# What the world hands over without anything being crafted first.
# Everything an animal leaves behind. Read off the beast table rather than
# listed by hand, so a new drop cannot quietly go missing from this check.
HUNTED = {kind for beast in BEAST_KINDS for kind, _ in beast.drops}

MINED = {
    STONE,
    WOOD,
    COPPER_ORE,
    IRON_ORE,
    GOLD_ORE,
    ZINC_ORE,
    ITEM_KINDS["twig"],
    ITEM_KINDS["pebble"],
    ITEM_KINDS["grass"],
}


def _by_output(kind):
    return next(r for r in recipes.RECIPES if r.output is kind)


def test_every_input_and_output_is_a_real_catalogue_row():
    for recipe in recipes.RECIPES:
        assert ITEM_KINDS[recipe.output.key] is recipe.output
        for kind, _ in recipe.inputs:
            assert ITEM_KINDS[kind.key] is kind


def test_counts_are_positive():
    for recipe in recipes.RECIPES:
        assert recipe.count >= 1
        assert all(n >= 1 for _, n in recipe.inputs)
        assert recipe.seconds >= 0


def test_nothing_is_made_out_of_itself():
    for recipe in recipes.RECIPES:
        assert all(kind is not recipe.output for kind, _ in recipe.inputs)


def test_the_empty_handed_list_is_the_bootstrap_and_no_more():
    # A crude axe from litter, then the wooden tools and bench the wood buys.
    # Everything past that is something a station earns.
    free = {r.output for r in recipes.recipes_at(recipes.NOWHERE)}
    assert free == {
        ITEM_KINDS["crude_axe"],
        WOOD_PICK,
        WOOD_AXE,
        ITEM_KINDS["bench"],
    }


def test_the_crude_axe_is_made_of_nothing_that_needs_a_tool():
    from game.items import grades

    crude = _by_output(ITEM_KINDS["crude_axe"])
    assert crude.station == recipes.NOWHERE
    for kind, _ in crude.inputs:
        assert grades.need_for(kind).family == grades.HAND


def test_the_bench_chain_climbs_to_the_fine_bench():
    assert _by_output(FINE_BENCH).station == recipes.BENCH_S


def test_the_blast_furnace_is_the_fine_bench_s_job():
    assert _by_output(BLAST_FURNACE).station == recipes.FINE_S


def test_brass_comes_from_the_smelter_and_steel_from_the_furnace():
    assert _by_output(BRASS_INGOT).station == recipes.SMELTER_S
    assert _by_output(STEEL_INGOT).station == recipes.FURNACE_S


def test_smelting_takes_time_and_bench_work_does_not():
    # Standing at a bench to shape a handle is not a thing to wait for; a
    # furnace is, and waiting is what turns the ward into somewhere run rather
    # than somewhere visited.
    for recipe in recipes.RECIPES:
        if recipe.station in (recipes.NOWHERE, recipes.BENCH_S, recipes.FINE_S):
            assert recipe.seconds == 0
        else:
            assert recipe.seconds > 0


def test_steel_is_locked_behind_brass_which_is_locked_behind_zinc():
    # The chain the spec asks for: the furnace eats brass, brass eats zinc, and
    # zinc needs an iron pick -- so steel cannot be rushed.
    assert BRASS_INGOT in {k for k, _ in _by_output(BLAST_FURNACE).inputs}
    assert ZINC_ORE in {k for k, _ in _by_output(BRASS_INGOT).inputs}
    assert grades.need_for(ZINC_ORE).grade is grades.IRON_G


def test_every_recipe_is_reachable_from_an_empty_hand():
    # The most important test in this table. One broken link and the game is
    # unwinnable, and no amount of reading the rows will show it.
    #
    # The world hands out two ways, not one: what is mined and what is hunted.
    # Hide is only ever cut off an animal, so the walk has to start from both or
    # it would call the leather pack unreachable when it plainly is not.
    have = set(MINED) | set(HUNTED)
    stations = {recipes.NOWHERE}
    progress = True
    while progress:
        progress = False
        for recipe in recipes.RECIPES:
            if recipe.output in have or recipe.station not in stations:
                continue
            if all(kind in have for kind, _ in recipe.inputs):
                have.add(recipe.output)
                stations |= recipes.STATION_OF.get(recipe.output, set())
                progress = True
    unreachable = [r.output.name for r in recipes.RECIPES if r.output not in have]
    assert unreachable == []


def test_placing_a_station_is_what_opens_its_recipes():
    # The table has to say which built thing unlocks which bench, or the
    # reachability walk above would be checking nothing.
    assert recipes.STATION_OF[ITEM_KINDS["bench"]] == {recipes.BENCH_S}
    assert recipes.STATION_OF[FINE_BENCH] == {recipes.FINE_S}
    assert recipes.STATION_OF[BLAST_FURNACE] == {recipes.FURNACE_S}


def test_the_leather_pack_is_paid_for_in_hide():
    # The bigger pack costs nights spent out among the animals rather than ore,
    # which is the only reason to go near a wolf.
    from game.items.item_kinds import HIDE

    assert HIDE in {kind for kind, _ in _by_output(ITEM_KINDS["leather_pack"]).inputs}
