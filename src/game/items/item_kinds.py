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

# --- Litter ---------------------------------------------------------------------
# Lying on the ground, free to anyone with hands. The whole bootstrap rests on
# these three: they are the only things a player with nothing can pick up, and
# together they make the crude axe that starts everything else.
TWIG = ItemKind("twig", "나뭇가지", _STACK, (138, 104, 66))
PEBBLE = ItemKind("pebble", "조약돌", _STACK, (160, 158, 150))
GRASS = ItemKind("grass", "풀", _STACK, (118, 158, 86))

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
# A chisel is three cuts and gone, so it stacks like a consumable, not like
# the one-of-a-kind bag it sits next to.
# Staves. One of each, like a pack -- what matters about yours is what is
# carved on it, so two identical ones would be two of the same decision.
STAFF_ITEM = ItemKind("staff", "지팡이", 1, (140, 110, 170))
GREATER_STAFF_ITEM = ItemKind("greater_staff", "상급 지팡이", 1, (170, 130, 210))
SUPREME_STAFF_ITEM = ItemKind("supreme_staff", "최상급 지팡이", 1, (210, 160, 250))
CHISEL = ItemKind("chisel", "새김 도구", 8, (205, 185, 150))
WORN_PACK = ItemKind("worn_pack", "낡은 배낭", 1, (120, 95, 70))
LEATHER_PACK = ItemKind("leather_pack", "가죽 배낭", 1, (160, 115, 75))

# --- Tools ----------------------------------------------------------------------
# One row per family per grade. Verbose on purpose: a tool is an item like any
# other, so it lands in slots, rides in a pack, and is lost with it. Which grade
# a row belongs to lives in items/grades.py -- the catalogue says what exists.
CRUDE_AXE = ItemKind("crude_axe", "조잡한 도끼", 1, (124, 112, 84))
WOOD_PICK = ItemKind("wood_pick", "나무 곡괭이", 1, (150, 110, 70))
STONE_PICK = ItemKind("stone_pick", "돌 곡괭이", 1, (140, 140, 150))
COPPER_PICK = ItemKind("copper_pick", "구리 곡괭이", 1, (205, 130, 85))
IRON_PICK = ItemKind("iron_pick", "철 곡괭이", 1, (185, 185, 195))
GOLD_PICK = ItemKind("gold_pick", "금 곡괭이", 1, (240, 205, 95))
BRASS_PICK = ItemKind("brass_pick", "황동 곡괭이", 1, (215, 180, 90))
STEEL_PICK = ItemKind("steel_pick", "강철 곡괭이", 1, (120, 130, 150))

WOOD_AXE = ItemKind("wood_axe", "나무 도끼", 1, (128, 95, 60))
STONE_AXE = ItemKind("stone_axe", "돌 도끼", 1, (120, 120, 132))
COPPER_AXE = ItemKind("copper_axe", "구리 도끼", 1, (180, 112, 72))
IRON_AXE = ItemKind("iron_axe", "철 도끼", 1, (160, 160, 172))
GOLD_AXE = ItemKind("gold_axe", "금 도끼", 1, (214, 180, 82))
BRASS_AXE = ItemKind("brass_axe", "황동 도끼", 1, (190, 158, 78))
STEEL_AXE = ItemKind("steel_axe", "강철 도끼", 1, (102, 112, 132))

# --- Stations -------------------------------------------------------------------
# Carried as an item, then placed inside the ward. What each one unlocks is in
# items/recipes.py; this is only what they are.
BENCH = ItemKind("bench", "제작대", 1, (146, 112, 74))
SMELTER = ItemKind("smelter", "용광로", 1, (112, 104, 110))
HEARTH = ItemKind("hearth", "화덕", 1, (150, 92, 68))
FINE_BENCH = ItemKind("fine_bench", "고급 제작대", 1, (176, 146, 96))
BLAST_FURNACE = ItemKind("blast_furnace", "고로", 1, (92, 96, 112))

# --- Consumed -----------------------------------------------------------------
# Meat restores stamina only; raw costs HP on top. Potions are the HP answer in
# the field and are deliberately scarce.
HIDE = ItemKind("hide", "가죽", _STACK, (164, 120, 86))
RAW_MEAT = ItemKind("raw_meat", "생고기", 16, (200, 110, 115))
COOKED_MEAT = ItemKind("cooked_meat", "익힌 고기", 16, (165, 105, 65))
POTION = ItemKind("potion", "물약", 8, (210, 80, 130))

# Draw order for the inventory grid. Fixed on purpose: rows must not shuffle under
# the cursor as counts change, or drag targets move while the player is aiming.
CATALOGUE: tuple[ItemKind, ...] = (
    CORE_SHARD,
    TWIG,
    PEBBLE,
    GRASS,
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
    CRUDE_AXE,
    WOOD_PICK,
    STONE_PICK,
    COPPER_PICK,
    IRON_PICK,
    GOLD_PICK,
    BRASS_PICK,
    STEEL_PICK,
    WOOD_AXE,
    STONE_AXE,
    COPPER_AXE,
    IRON_AXE,
    GOLD_AXE,
    BRASS_AXE,
    STEEL_AXE,
    BENCH,
    SMELTER,
    HEARTH,
    FINE_BENCH,
    BLAST_FURNACE,
    CHISEL,
    STAFF_ITEM,
    GREATER_STAFF_ITEM,
    SUPREME_STAFF_ITEM,
    WORN_PACK,
    LEATHER_PACK,
    HIDE,
    RAW_MEAT,
    COOKED_MEAT,
    POTION,
)

ITEM_KINDS: dict[str, ItemKind] = {kind.key: kind for kind in CATALOGUE}
