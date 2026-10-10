from game.inventory.hotbar import Hotbar
from game.inventory.stack import Stack
from game.inventory.storage import Container
from game.items import recipes
from game.items.item_kinds import BENCH, COPPER_INGOT, WOOD, WOOD_PICK
from game.items.tools import MiningTool
from game.systems import crafting

PICK = next(r for r in recipes.RECIPES if r.output is WOOD_PICK)
BENCH_R = next(r for r in recipes.RECIPES if r.output is BENCH)


def test_what_is_offered_depends_on_where_you_stand():
    hb = Hotbar.create()
    free = {r.output for r, _ in crafting.available(recipes.NOWHERE, None, hb)}
    at_bench = {r.output for r, _ in crafting.available(recipes.BENCH_S, None, hb)}
    assert WOOD_PICK in free
    assert COPPER_INGOT not in free
    assert WOOD_PICK not in at_bench  # the bench shows the bench's own list
    assert free != at_bench


def test_a_row_is_marked_affordable_only_when_the_materials_are_there():
    hb, pack = Hotbar.create(), Container.empty(4)
    offered = dict(crafting.available(recipes.NOWHERE, pack, hb))
    assert offered[PICK] is False
    pack.add(WOOD, 3)
    offered = dict(crafting.available(recipes.NOWHERE, pack, hb))
    assert offered[PICK] is True


def test_materials_are_counted_across_the_pack_and_the_hotbar():
    # Crafting has to work bare-handed, which means out of the hotbar alone.
    hb, pack = Hotbar.create(), Container.empty(4)
    pack.add(WOOD, 1)
    hb.add(WOOD, 2)
    assert dict(crafting.available(recipes.NOWHERE, pack, hb))[PICK] is True


def test_crafting_takes_the_inputs_and_hands_back_the_output():
    hb, pack = Hotbar.create(), Container.empty(4)
    pack.add(WOOD, 5)
    assert crafting.craft(PICK, pack, hb) is WOOD_PICK
    assert pack.count(WOOD) == 2
    assert pack.count(WOOD_PICK) == 1


def test_crafting_works_with_no_backpack_at_all():
    hb = Hotbar.create()
    hb.add(WOOD, 3)
    assert crafting.craft(PICK, None, hb) is WOOD_PICK
    assert hb.count(WOOD_PICK) == 1
    assert hb.count(WOOD) == 0


def test_short_materials_change_nothing():
    hb, pack = Hotbar.create(), Container.empty(4)
    pack.add(WOOD, 2)
    assert crafting.craft(PICK, pack, hb) is None
    assert pack.count(WOOD) == 2  # not half-spent


def test_a_multi_input_recipe_is_all_or_nothing():
    # Spending the wood and then finding there is no stone would evaporate it.
    hb, pack = Hotbar.create(), Container.empty(4)
    pack.add(WOOD, 20)
    assert crafting.craft(BENCH_R, pack, hb) is None
    assert pack.count(WOOD) == 20


def test_nowhere_to_put_the_output_means_nothing_is_made():
    # Dropping it on the floor would give it a five-minute clock. Better to
    # refuse than to hand the player a countdown they did not ask for.
    hb = Hotbar.create()
    for i in range(len(hb.slots)):
        hb.slots[i] = MiningTool()
    pack = Container.empty(1)
    pack.add(WOOD, WOOD.stack_max)
    assert pack.free == 0
    assert crafting.craft(PICK, pack, hb) is None
    assert pack.count(WOOD) == WOOD.stack_max


def test_the_output_can_land_in_the_space_the_inputs_free_up():
    # Spending a full slot of wood leaves room the pickaxe can use.
    hb, pack = Hotbar.create(), Container.empty(1)
    pack.add(WOOD, 3)
    assert crafting.craft(PICK, pack, hb) is WOOD_PICK
    assert pack.count(WOOD_PICK) == 1


def test_a_station_recipe_cannot_be_crafted_from_nowhere():
    hb = Hotbar.create()
    assert all(
        r.station == recipes.NOWHERE for r, _ in crafting.available(recipes.NOWHERE, None, hb)
    )


def test_stacks_are_drawn_from_the_pack_before_the_hotbar():
    # The hotbar is what a death spares, so it is spent last.
    hb, pack = Hotbar.create(), Container.empty(4)
    pack.add(WOOD, 2)
    hb.add(WOOD, 4)
    crafting.craft(PICK, pack, hb)
    assert pack.count(WOOD) == 0
    assert hb.count(WOOD) == 3
    assert hb.slots[0] != Stack(WOOD, 4)
