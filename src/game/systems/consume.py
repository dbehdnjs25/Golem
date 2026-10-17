"""Eating and drinking.

Meat buys back wind; a potion buys back blood. Neither is a hunger clock --
the spec rules hunger out -- they are the supplies a trip is stocked with,
which is why the walk home is for restocking rather than for healing.

Raw meat gives the same breath as cooked and takes it out of your health. That
is the whole trade: cooking is free but only happens at a hearth, and hearths
only stand inside the ward.

What a thing does is a row in ``EDIBLE`` rather than a branch, so a food added
to the catalogue cannot quietly do nothing.
"""

from __future__ import annotations

from dataclasses import dataclass

from game import config
from game.entities.player import Player
from game.items.item_kinds import COOKED_MEAT, RAW_MEAT, ItemKind


@dataclass(frozen=True)
class Food:
    stamina: float  # wind given back
    hp: float  # health given back; negative is a price paid


EDIBLE: dict[ItemKind, Food] = {
    COOKED_MEAT: Food(stamina=config.MEAT_STAMINA, hp=0.0),
    RAW_MEAT: Food(stamina=config.MEAT_STAMINA, hp=-config.RAW_MEAT_HP_COST),
}


def eat(kind: ItemKind, player: Player) -> bool:
    """Use one up. False if it would do nothing, and then nothing is used.

    Refusing on a full tank matters: a stack quietly spent for no effect is
    worse than the key doing nothing at all.
    """
    food = EDIBLE.get(kind)
    if food is None or player.hp <= 0:
        return False
    if food.stamina and player.stamina >= player.max_stamina:
        return False
    if food.hp > 0 and player.hp >= player.max_hp:
        return False
    player.stamina = min(player.max_stamina, player.stamina + food.stamina)
    # Floored at one: dying of a snack reads as a bug rather than as the hard
    # choice it is meant to be.
    player.hp = max(1.0, min(player.max_hp, player.hp + food.hp))
    return True
