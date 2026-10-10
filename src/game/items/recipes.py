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
    BRASS_AXE,
    BRASS_INGOT,
    BRASS_PICK,
    CHARCOAL,
    COPPER_AXE,
    COPPER_INGOT,
    COPPER_ORE,
    COPPER_PICK,
    CRUDE_AXE,
    FINE_BENCH,
    GOLD_AXE,
    GOLD_INGOT,
    GOLD_ORE,
    GOLD_PICK,
    GRASS,
    HEARTH,
    IRON_AXE,
    IRON_INGOT,
    IRON_ORE,
    IRON_PICK,
    PEBBLE,
    SMELTER,
    STEEL_AXE,
    STEEL_INGOT,
    STEEL_PICK,
    STONE,
    STONE_AXE,
    STONE_PICK,
    TWIG,
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
    Recipe(WORN_PACK, 1, ((WOOD, 12),), BENCH_S),
    Recipe(FINE_BENCH, 1, ((BRASS_INGOT, 4), (GOLD_INGOT, 2), (WOOD, 20)), BENCH_S),
    _tool(STONE_PICK, STONE),
    _tool(STONE_AXE, STONE),
    _tool(COPPER_PICK, COPPER_INGOT),
    _tool(COPPER_AXE, COPPER_INGOT),
    _tool(IRON_PICK, IRON_INGOT),
    _tool(IRON_AXE, IRON_INGOT),
    _tool(GOLD_PICK, GOLD_INGOT),
    _tool(GOLD_AXE, GOLD_INGOT),
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
