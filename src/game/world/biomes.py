"""The catalogue of biomes. Data only -- a frozen row per biome, no behaviour.

Same shape as ``items/item_kinds.py``: the table lives here, the code that acts
on it lives in ``world/map.py``. Adding a biome is adding a row.

``key`` is the stable identifier that goes into save files; ``name`` is what the
player reads. The grassland carries neither an element nor a material on
purpose: grade comes from the grassland and attributes come from the biomes, and
the two ladders never mix.

Boss gimmicks are NOT here. This table says what the ground is, not what guards
it -- the bosses arrive with the temples.
"""

from __future__ import annotations

from dataclasses import dataclass

from game.items.item_kinds import (
    BOG_MOSS,
    FROST_CRYSTAL,
    OBSIDIAN,
    THUNDER_STONE,
    WEATHERED_STONE,
    ItemKind,
)

# Attribute magic families. One per ring biome; the grassland has none.
FIRE = "fire"
ICE = "ice"
WIND = "wind"
POISON = "poison"
LIGHTNING = "lightning"


@dataclass(frozen=True)
class Biome:
    key: str  # stable id, used for saves and comparison
    name: str  # shown to the player
    element: str | None  # the attribute its glyphs grant; None in the grassland
    material: ItemKind | None  # what only this biome yields; None in the grassland
    color: tuple[int, int, int]  # flat fill until real tiles exist


GRASSLAND = Biome("grassland", "초원", None, None, (90, 130, 72))

# Ring order is difficulty order. Volcano first because lava is a visible,
# stationary hazard -- the easiest kind to read. Bog fourth because its stamina
# drain is unfair before cooking and potions exist. Wasteland last because raids
# come in crowds and chaining is the answer to the final gauntlet.
VOLCANO = Biome("volcano", "화산지대", FIRE, OBSIDIAN, (126, 54, 44))
SNOWFIELD = Biome("snowfield", "설원", ICE, FROST_CRYSTAL, (206, 219, 230))
WIND_PLATEAU = Biome("wind_plateau", "바람 고원", WIND, WEATHERED_STONE, (150, 152, 140))
BOG = Biome("bog", "늪지", POISON, BOG_MOSS, (55, 62, 42))
WASTELAND = Biome("wasteland", "황무지", LIGHTNING, THUNDER_STONE, (152, 122, 80))

RING_BIOMES: tuple[Biome, ...] = (VOLCANO, SNOWFIELD, WIND_PLATEAU, BOG, WASTELAND)
BIOMES: tuple[Biome, ...] = (GRASSLAND, *RING_BIOMES)

BIOME_BY_KEY: dict[str, Biome] = {biome.key: biome for biome in BIOMES}
