"""What can be made here, and what making it costs.

Pure functions over injected state, like the rest of ``systems/``. The table of
what turns into what is ``items/recipes``; this decides whether a player can
afford a row and moves the goods when they do.

Materials are counted across the pack AND the hotbar, because crafting has to
work bare-handed -- a player with no backpack has only the hotbar, and the
first recipes exist precisely for them.

Spending is all-or-nothing. Taking the wood and then discovering there is no
stone would evaporate the wood, so nothing moves until everything is known to
be there and the result is known to have somewhere to land.
"""

from __future__ import annotations

from game.inventory.hotbar import Hotbar
from game.inventory.storage import Container
from game.items.item_kinds import ItemKind
from game.items.recipes import RECIPES, Recipe
from game.systems import carrying


def _carried(kind: ItemKind, backpack: Container | None, hotbar: Hotbar) -> int:
    in_pack = backpack.count(kind) if backpack is not None else 0
    return in_pack + hotbar.count(kind)


def spend(kind: ItemKind, n: int, backpack: Container | None, hotbar: Hotbar) -> None:
    """Take ``n`` of ``kind``, pack first.

    The hotbar is what a death spares, so it is spent last. Public because a
    station job spends its inputs up front and then runs on its own.
    """
    taken = backpack.remove(kind, n) if backpack is not None else 0
    hotbar.remove(kind, n - taken)


def affordable(recipe: Recipe, backpack: Container | None, hotbar: Hotbar) -> bool:
    return all(_carried(kind, backpack, hotbar) >= n for kind, n in recipe.inputs)


def available(
    stations: set[str], backpack: Container | None, hotbar: Hotbar
) -> list[tuple[Recipe, bool]]:
    """Every row workable from where the player stands, flagged by affordability.

    A set of stations rather than one, because several can be in reach at once
    and they are not a single ladder -- a smelter and a hearth do different
    jobs, so both lists show.
    """
    return [(r, affordable(r, backpack, hotbar)) for r in RECIPES if r.station in stations]


def craft(recipe: Recipe, backpack: Container | None, hotbar: Hotbar) -> ItemKind | None:
    """Spend the inputs and hand over the output. Return None if nothing happened.

    The inputs are spent BEFORE the room check, because spending them is what
    frees the room -- a full pack of wood has space for the pickaxe the moment
    the wood leaves. If the result still will not fit, the inputs go back.
    """
    if not affordable(recipe, backpack, hotbar):
        return None
    for kind, n in recipe.inputs:
        spend(kind, n, backpack, hotbar)
    if carrying.store(recipe.output, recipe.count, backpack, hotbar) == recipe.count:
        return recipe.output
    for kind, n in recipe.inputs:  # nowhere to put it -- undo
        carrying.store(kind, n, backpack, hotbar)
    return None
