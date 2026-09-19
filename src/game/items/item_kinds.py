"""The catalogue of item kinds. Data only -- a frozen row per kind, no behaviour.

Same shape as ``items/tools.py``: the table lives here, the systems that act on
it live in ``systems/`` and ``inventory/``. Adding an item kind is adding a row.

``key`` is the stable identifier that goes into save files; ``name`` is what the
player reads. They are separate so renaming the display text never invalidates a
save.

Recipes are NOT here. This table says what exists, not what turns into what --
smelting and crafting arrive with the crafting stations.
"""

from __future__ import annotations

from dataclasses import dataclass

from game import config

_STACK = config.STACK_MAX_DEFAULT


@dataclass(frozen=True)
class ItemKind:
    key: str  # stable id, used for storage and comparison
    name: str  # shown in the inventory grid
    stack_max: int  # how many fit in one slot
    color: tuple[int, int, int]  # icon colour


# --- The core -----------------------------------------------------------------
# Scattered around the pedestal at the start. Assembling and placing them is what
# starts day one, so they stack low enough to be felt.
CORE_SHARD = ItemKind("core_shard", "코어 파편", 16, config.FRAGMENT_COLOR)

# --- Gathered -----------------------------------------------------------------
STONE = ItemKind("stone", "돌", _STACK, (140, 140, 150))
WOOD = ItemKind("wood", "나무", _STACK, (150, 110, 70))
CHARCOAL = ItemKind("charcoal", "숯", _STACK, (60, 58, 62))

# --- Mined --------------------------------------------------------------------
# Zinc is smelting-only: it never becomes a tool tier, it only feeds brass. It is
# rare and lives in the outer grassland, so brass costs distance, not depth.
COPPER_ORE = ItemKind("copper_ore", "구리 광석", _STACK, (190, 120, 80))
IRON_ORE = ItemKind("iron_ore", "철 광석", _STACK, (170, 170, 180))
GOLD_ORE = ItemKind("gold_ore", "금 광석", _STACK, (220, 190, 90))
ZINC_ORE = ItemKind("zinc_ore", "아연 광석", _STACK, (190, 200, 210))

# --- Smelted ------------------------------------------------------------------
# The tool grade ladder: 돌 -> 구리 -> 철 -> 금 -> 황동 -> 강철.
COPPER_INGOT = ItemKind("copper_ingot", "구리 주괴", _STACK, (205, 130, 85))
IRON_INGOT = ItemKind("iron_ingot", "철 주괴", _STACK, (185, 185, 195))
GOLD_INGOT = ItemKind("gold_ingot", "금 주괴", _STACK, (240, 205, 95))
BRASS_INGOT = ItemKind("brass_ingot", "황동 주괴", _STACK, (215, 180, 90))
STEEL_INGOT = ItemKind("steel_ingot", "강철 주괴", _STACK, (120, 130, 150))

# --- Biome materials ----------------------------------------------------------
# These never raise a grade. They feed magic and temple locators instead -- grade
# and attribute are two ladders that do not mix.
OBSIDIAN = ItemKind("obsidian", "흑요석", _STACK, (45, 35, 55))
FROST_CRYSTAL = ItemKind("frost_crystal", "서리 결정", _STACK, (150, 220, 240))
WEATHERED_STONE = ItemKind("weathered_stone", "풍화석", _STACK, (185, 175, 155))
BOG_MOSS = ItemKind("bog_moss", "늪 이끼", _STACK, (95, 130, 75))
THUNDER_STONE = ItemKind("thunder_stone", "뇌석", _STACK, (215, 200, 120))

# --- Worn ----------------------------------------------------------------------
# The only storage there is. Without one the hotbar is the whole of a player's
# belongings, so the first pack is the first real goal -- and losing one costs
# every slot at once. They do not stack: you wear one.
WORN_PACK = ItemKind("worn_pack", "낡은 배낭", 1, (120, 95, 70))
LEATHER_PACK = ItemKind("leather_pack", "가죽 배낭", 1, (160, 115, 75))

# --- Consumed -----------------------------------------------------------------
# Meat restores stamina only; raw costs HP on top. Potions are the HP answer in
# the field and are deliberately scarce.
RAW_MEAT = ItemKind("raw_meat", "생고기", 16, (200, 110, 115))
COOKED_MEAT = ItemKind("cooked_meat", "익힌 고기", 16, (165, 105, 65))
POTION = ItemKind("potion", "물약", 8, (210, 80, 130))

# Draw order for the inventory grid. Fixed on purpose: rows must not shuffle under
# the cursor as counts change, or drag targets move while the player is aiming.
CATALOGUE: tuple[ItemKind, ...] = (
    CORE_SHARD,
    STONE,
    WOOD,
    CHARCOAL,
    COPPER_ORE,
    IRON_ORE,
    GOLD_ORE,
    ZINC_ORE,
    COPPER_INGOT,
    IRON_INGOT,
    GOLD_INGOT,
    BRASS_INGOT,
    STEEL_INGOT,
    OBSIDIAN,
    FROST_CRYSTAL,
    WEATHERED_STONE,
    BOG_MOSS,
    THUNDER_STONE,
    WORN_PACK,
    LEATHER_PACK,
    RAW_MEAT,
    COOKED_MEAT,
    POTION,
)

ITEM_KINDS: dict[str, ItemKind] = {kind.key: kind for kind in CATALOGUE}
