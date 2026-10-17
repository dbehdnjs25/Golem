"""What turns into what, and where it has to be done.

The table lives here; deciding whether a player can afford a row lives in
``systems/crafting``. Same split as ``item_kinds`` and ``inventory``.

Where a recipe can be worked is the progression. Wooden tools and the first
bench need nothing standing; the bench opens the smelters and the better tools;
the fine bench opens the furnace. So "where can I make this" is the progress
bar, and opening the menu somewhere new is itself the reward.

Bench work is instant and smelting is not. Shaping a handle is not something to
wait for; a furnace is, and that waiting is what turns the ward into somewhere
run rather than somewhere visited.
"""

from __future__ import annotations

from dataclasses import dataclass

from game.items.item_kinds import (
    BENCH,
    BLAST_FURNACE,
    BOG_DETECTOR,
    BOG_MOSS,
    BRASS_AXE,
    BRASS_INGOT,
    BRASS_PICK,
    BURNT_FOREST_DETECTOR,
    CHARCOAL,
    CHARRED_WOOD,
    CHISEL,
    COOKED_MEAT,
    COPPER_AXE,
    COPPER_INGOT,
    COPPER_ORE,
    COPPER_PICK,
    CRUDE_AXE,
    FINE_BENCH,
    FROST_CRYSTAL,
    FROZEN_WOOD,
    GOLD_AXE,
    GOLD_INGOT,
    GOLD_ORE,
    GOLD_PICK,
    GRASS,
    GREATER_STAFF_ITEM,
    HEARTH,
    HIDE,
    IRON_AXE,
    IRON_INGOT,
    IRON_ORE,
    IRON_PICK,
    LEATHER_PACK,
    OBSIDIAN,
    PARCHED_WOOD,
    PEBBLE,
    POTION,
    RAW_MEAT,
    SMELTER,
    SNOWFIELD_DETECTOR,
    SODDEN_WOOD,
    STAFF_ITEM,
    STEEL_AXE,
    STEEL_INGOT,
    STEEL_PICK,
    STONE,
    STONE_AXE,
    STONE_PICK,
    SUPREME_STAFF_ITEM,
    THUNDER_STONE,
    TWIG,
    TWISTED_WOOD,
    WASTELAND_DETECTOR,
    WEATHERED_STONE,
    WIND_DETECTOR,
    WOOD,
    WOOD_AXE,
    WOOD_PICK,
    WORN_PACK,
    ZINC_ORE,
    ItemKind,
)

# Where a recipe can be worked.
NOWHERE = "nowhere"  # an empty hand, standing anywhere
BENCH_S = "bench"
FINE_S = "fine_bench"
SMELTER_S = "smelter"
HEARTH_S = "hearth"
FURNACE_S = "blast_furnace"


@dataclass(frozen=True)
class Recipe:
    output: ItemKind
    count: int
    inputs: tuple[tuple[ItemKind, int], ...]
    station: str
    seconds: float = 0.0


def _tool(output: ItemKind, metal: ItemKind, station: str = BENCH_S) -> Recipe:
    """Every tool is a handle and three of something harder."""
    return Recipe(output, 1, ((WOOD, 2), (metal, 3)), station)


RECIPES: tuple[Recipe, ...] = (
    # --- empty-handed: enough to stop being empty-handed --------------------
    # A branch, a stone and a handful of grass to lash them together. The only
    # recipe that needs nothing already made, so the run begins here.
    Recipe(CRUDE_AXE, 1, ((TWIG, 2), (PEBBLE, 1), (GRASS, 2)), NOWHERE),
    Recipe(WOOD_PICK, 1, ((WOOD, 3),), NOWHERE),
    Recipe(WOOD_AXE, 1, ((WOOD, 3),), NOWHERE),
    Recipe(BENCH, 1, ((WOOD, 10), (STONE, 5)), NOWHERE),
    # --- the bench ----------------------------------------------------------
    Recipe(SMELTER, 1, ((STONE, 20),), BENCH_S),
    Recipe(HEARTH, 1, ((STONE, 12), (WOOD, 6)), BENCH_S),
    # Cheap to make and quick to use up. The scarcity that matters is the
    # three cuts it has in it, not the iron it took.
    Recipe(CHISEL, 1, ((IRON_INGOT, 1), (WOOD, 2)), BENCH_S),
    Recipe(WORN_PACK, 1, ((WOOD, 12),), BENCH_S),
    # Hide only comes off an animal, so the bigger pack is paid for in nights
    # spent out rather than in ore.
    Recipe(LEATHER_PACK, 1, ((HIDE, 8), (WOOD, 10)), BENCH_S),
    # The first staff is cheap; what it costs is the glyph you have to go and
    # find before it does anything at all.
    Recipe(STAFF_ITEM, 1, ((WOOD, 10), (GOLD_INGOT, 1)), BENCH_S),
    Recipe(FINE_BENCH, 1, ((BRASS_INGOT, 4), (GOLD_INGOT, 2), (WOOD, 20)), BENCH_S),
    _tool(STONE_PICK, STONE),
    _tool(STONE_AXE, STONE),
    _tool(COPPER_PICK, COPPER_INGOT),
    _tool(COPPER_AXE, COPPER_INGOT),
    _tool(IRON_PICK, IRON_INGOT),
    _tool(IRON_AXE, IRON_INGOT),
    _tool(GOLD_PICK, GOLD_INGOT),
    _tool(GOLD_AXE, GOLD_INGOT),
    # Each upgrade eats the one below it and a wider spread of biome material,
    # so the staff with the most room on it is the reward for having toured
    # the whole ring -- which is the only thing in the game that asks for that.
    Recipe(
        GREATER_STAFF_ITEM,
        1,
        ((STAFF_ITEM, 1), (OBSIDIAN, 4), (FROST_CRYSTAL, 4)),
        FINE_S,
    ),
    Recipe(
        SUPREME_STAFF_ITEM,
        1,
        ((GREATER_STAFF_ITEM, 1), (WEATHERED_STONE, 6), (BOG_MOSS, 6), (THUNDER_STONE, 6)),
        FINE_S,
    ),
    # One per biome, out of that biome's own material. Which means the fifth
    # temple can only be found after mining in the fifth biome -- the detectors
    # chain the tour rather than handing out the whole map at once.
    Recipe(BURNT_FOREST_DETECTOR, 1, ((OBSIDIAN, 3), (GOLD_INGOT, 1)), FINE_S),
    Recipe(SNOWFIELD_DETECTOR, 1, ((FROST_CRYSTAL, 3), (GOLD_INGOT, 1)), FINE_S),
    Recipe(WIND_DETECTOR, 1, ((WEATHERED_STONE, 3), (GOLD_INGOT, 1)), FINE_S),
    Recipe(BOG_DETECTOR, 1, ((BOG_MOSS, 3), (GOLD_INGOT, 1)), FINE_S),
    Recipe(WASTELAND_DETECTOR, 1, ((THUNDER_STONE, 3), (GOLD_INGOT, 1)), FINE_S),
    # --- the fine bench -----------------------------------------------------
    Recipe(BLAST_FURNACE, 1, ((BRASS_INGOT, 6), (STONE, 30)), FINE_S),
    _tool(BRASS_PICK, BRASS_INGOT, FINE_S),
    _tool(BRASS_AXE, BRASS_INGOT, FINE_S),
    _tool(STEEL_PICK, STEEL_INGOT, FINE_S),
    _tool(STEEL_AXE, STEEL_INGOT, FINE_S),
    # --- the smelter: ore in, ingots out, on a clock ------------------------
    Recipe(COPPER_INGOT, 1, ((COPPER_ORE, 2),), SMELTER_S, 10.0),
    Recipe(IRON_INGOT, 1, ((IRON_ORE, 2),), SMELTER_S, 15.0),
    Recipe(GOLD_INGOT, 1, ((GOLD_ORE, 2),), SMELTER_S, 20.0),
    Recipe(BRASS_INGOT, 1, ((COPPER_ORE, 2), (ZINC_ORE, 1)), SMELTER_S, 25.0),
    # --- the hearth: wood into charcoal -------------------------------------
    # The reason to walk into the burnt forest. Ordinary charcoal is three logs
    # burned for twelve seconds; this wood is already half burnt, so the fire
    # only has to finish it -- better rate and a quarter of the wait.
    #
    # Still at the hearth rather than bare-handed: the empty-handed list is the
    # bootstrap and nothing else, and a player holding nothing has no business
    # being told about charcoal.
    # The hearth's other job. Cooking is free where burning raw meat in the
    # field costs blood, and a hearth only ever stands inside the ward.
    # Every biome timber trims down to ordinary wood at a bench. None of them
    # is ever a dead end -- what a biome's tree costs is the axe it takes to
    # fell, not the risk of carrying home something unusable.
    #
    # At a bench rather than bare handed: the empty-handed list is the
    # bootstrap and nothing else, and five conversions would bury the four
    # rows a player with nothing actually needs to see. No wait on it --
    # trimming a log is bench work, and bench work is not something to stand
    # and watch.
    Recipe(WOOD, 1, ((CHARRED_WOOD, 1),), BENCH_S),
    Recipe(WOOD, 1, ((FROZEN_WOOD, 1),), BENCH_S),
    Recipe(WOOD, 1, ((TWISTED_WOOD, 1),), BENCH_S),
    Recipe(WOOD, 1, ((SODDEN_WOOD, 1),), BENCH_S),
    Recipe(WOOD, 1, ((PARCHED_WOOD, 1),), BENCH_S),
    Recipe(COOKED_MEAT, 1, ((RAW_MEAT, 1),), HEARTH_S, 6.0),
    # Herbs boiled down over a frost crystal. The snowfield is the second
    # biome and the bog the fourth, which is the order the spec needs: the
    # bog's drain is only fair once potions exist.
    Recipe(POTION, 1, ((GRASS, 10), (FROST_CRYSTAL, 1)), HEARTH_S, 8.0),
    Recipe(CHARCOAL, 2, ((CHARRED_WOOD, 2),), HEARTH_S, 3.0),
    Recipe(CHARCOAL, 2, ((WOOD, 3),), HEARTH_S, 12.0),
    # --- the blast furnace: the only way to steel ---------------------------
    Recipe(STEEL_INGOT, 1, ((IRON_INGOT, 2), (CHARCOAL, 2)), FURNACE_S, 40.0),
)

# Which built thing opens which bench. Placing it is what counts, not holding it.
STATION_OF: dict[ItemKind, set[str]] = {
    BENCH: {BENCH_S},
    FINE_BENCH: {FINE_S},
    SMELTER: {SMELTER_S},
    HEARTH: {HEARTH_S},
    BLAST_FURNACE: {FURNACE_S},
}


def recipes_at(station: str) -> tuple[Recipe, ...]:
    """Everything that can be worked at ``station``."""
    return tuple(recipe for recipe in RECIPES if recipe.station == station)
