"""The tool grade ladder, and what each node demands of the tool swung at it.

A grade is both a qualification and a speed: too low and the node cannot be
touched at all, high enough and it comes apart faster. Distance already decides
how dangerous ground is; grade decides whether being there is any use, so the
two axes meet and a player can walk somewhere they are not yet ready for.

Wood sits at the bottom because the opening has to make its first tool out of
whatever is lying around.

Biome materials answer to gold. Ore stops there, so without them the top three
grades would open nothing at all and the ladder's last half would be a speed
bonus wearing a ladder's clothes.

The table lives here and the checking lives in ``systems/mining`` -- the same
split as ``item_kinds`` and ``inventory``.
"""

from __future__ import annotations

from dataclasses import dataclass

from game.items.item_kinds import (
    BOG_MOSS,
    BRASS_AXE,
    BRASS_PICK,
    CHARRED_WOOD,
    COPPER_AXE,
    COPPER_ORE,
    COPPER_PICK,
    CRUDE_AXE,
    FROST_CRYSTAL,
    FROZEN_WOOD,
    GOLD_AXE,
    GOLD_ORE,
    GOLD_PICK,
    GRASS,
    IRON_AXE,
    IRON_ORE,
    IRON_PICK,
    OBSIDIAN_STONE,
    PARCHED_WOOD,
    PEBBLE,
    SODDEN_WOOD,
    STEEL_AXE,
    STEEL_PICK,
    STONE,
    STONE_AXE,
    STONE_PICK,
    THUNDER_STONE,
    TWIG,
    TWISTED_WOOD,
    WEATHERED_STONE,
    WOOD,
    WOOD_AXE,
    WOOD_PICK,
    ZINC_ORE,
    ItemKind,
)

# Tool families. A pickaxe cannot fell a tree and an axe cannot break rock;
# the wrong one in hand is a different problem from too weak a one.
#
# HAND is what an empty hand counts as. Only wood answers to it, and that is the
# bootstrap: wood wants an axe and an axe wants wood, so one of them has to
# give. Pulling at a branch by hand is the one that costs nothing to believe.
PICKAXE = "pickaxe"
AXE = "axe"
HAND = "hand"


@dataclass(frozen=True)
class Grade:
    key: str  # stable id, used for saves and comparison
    name: str  # shown to the player
    rank: int  # position on the ladder; the only thing gates compare
    speed: float  # multiplier on how fast a node comes apart


# Crude sits below wood: a branch lashed to a stone, made from litter by someone
# holding nothing. It only ever comes as an axe, which is the point -- it exists
# to fell the first tree, and everything else waits on the wood that gives.
CRUDE_G = Grade("crude", "조잡한", 0, 0.6)
WOOD_G = Grade("wood", "나무", 1, 1.0)
STONE_G = Grade("stone", "돌", 2, 1.4)
COPPER_G = Grade("copper", "구리", 3, 1.9)
IRON_G = Grade("iron", "철", 4, 2.5)
GOLD_G = Grade("gold", "금", 5, 3.2)
BRASS_G = Grade("brass", "황동", 6, 4.0)
STEEL_G = Grade("steel", "강철", 7, 5.0)

GRADES: tuple[Grade, ...] = (
    CRUDE_G,
    WOOD_G,
    STONE_G,
    COPPER_G,
    IRON_G,
    GOLD_G,
    BRASS_G,
    STEEL_G,
)
GRADE_BY_KEY: dict[str, Grade] = {grade.key: grade for grade in GRADES}


@dataclass(frozen=True)
class Need:
    family: str
    grade: Grade


NEEDS: dict[ItemKind, Need] = {
    # Litter: the only things an empty hand can take, and the whole bootstrap.
    TWIG: Need(HAND, CRUDE_G),
    PEBBLE: Need(HAND, CRUDE_G),
    GRASS: Need(HAND, CRUDE_G),
    # A tree wants an axe, and the crude one counts.
    WOOD: Need(AXE, CRUDE_G),
    STONE: Need(PICKAXE, WOOD_G),
    COPPER_ORE: Need(PICKAXE, WOOD_G),
    IRON_ORE: Need(PICKAXE, COPPER_G),
    GOLD_ORE: Need(PICKAXE, IRON_G),
    ZINC_ORE: Need(PICKAXE, IRON_G),
    # Each biome's timber takes a different axe, which is the whole of what
    # separates them at the stump. Burnt wood is the easiest -- the fire did
    # the hard part -- and frozen wood the worst, being a tree with ice in it.
    CHARRED_WOOD: Need(AXE, CRUDE_G),
    SODDEN_WOOD: Need(AXE, CRUDE_G),
    PARCHED_WOOD: Need(AXE, WOOD_G),
    TWISTED_WOOD: Need(AXE, STONE_G),
    FROZEN_WOOD: Need(AXE, COPPER_G),
    # The stone by the lava, not the glass. Obsidian is never lying about to be
    # picked up -- it is chipped out of this, beside the pool.
    OBSIDIAN_STONE: Need(PICKAXE, GOLD_G),
    FROST_CRYSTAL: Need(PICKAXE, GOLD_G),
    WEATHERED_STONE: Need(PICKAXE, GOLD_G),
    BOG_MOSS: Need(PICKAXE, GOLD_G),
    THUNDER_STONE: Need(PICKAXE, GOLD_G),
}

_ANYTHING = Need(HAND, GRADES[0])


def need_for(kind: ItemKind) -> Need:
    """What it takes to gather ``kind``. Anything unlisted asks for nothing."""
    return NEEDS.get(kind, _ANYTHING)


# Which item IS which tool. The catalogue says a steel pickaxe exists; this says
# where it sits on the ladder, so the two never have to agree by hand.
PICK_OF: dict[Grade, ItemKind] = {
    WOOD_G: WOOD_PICK,
    STONE_G: STONE_PICK,
    COPPER_G: COPPER_PICK,
    IRON_G: IRON_PICK,
    GOLD_G: GOLD_PICK,
    BRASS_G: BRASS_PICK,
    STEEL_G: STEEL_PICK,
}

# Crude has an axe and no pickaxe. It is a branch and a stone: enough to hack at
# a tree, nowhere near enough to break rock.
AXE_OF: dict[Grade, ItemKind] = {
    CRUDE_G: CRUDE_AXE,
    WOOD_G: WOOD_AXE,
    STONE_G: STONE_AXE,
    COPPER_G: COPPER_AXE,
    IRON_G: IRON_AXE,
    GOLD_G: GOLD_AXE,
    BRASS_G: BRASS_AXE,
    STEEL_G: STEEL_AXE,
}

# The reverse lookup, so an item in a slot can say what tool it is.
TOOL_ITEMS: dict[ItemKind, tuple[str, Grade]] = {
    **{item: (PICKAXE, grade) for grade, item in PICK_OF.items()},
    **{item: (AXE, grade) for grade, item in AXE_OF.items()},
}
