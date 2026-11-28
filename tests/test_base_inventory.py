"""Every player carries a small base inventory, pack or no pack.

Five slots from the start. A pack adds its own slots on top (a worn pack
makes 25, a leather one 45) and keeps what was already carried. A death
drops all of it -- the base slots too -- along with the pack, and the player
comes back with five empty slots.
"""

import pygame

from game import config
from game.inventory.storage import Container
from game.items.item_kinds import LEATHER_PACK, STONE, TWIG, WORN_PACK
from game.scenes.play import PlayScene

BASE = config.BASE_INVENTORY_SLOTS


def _scene() -> PlayScene:
    scene = PlayScene()
    scene.player.pos = scene.core.pos + pygame.Vector2(5_000, 0)  # out of the ward
    return scene


def _die(scene: PlayScene) -> None:
    scene.player.hp = 0
    scene.update(config.FIXED_DT)


def test_a_new_run_starts_with_the_base_inventory():
    scene = PlayScene()
    assert BASE == 5
    assert scene.backpack is not None
    assert scene.backpack.size == BASE
    assert scene.worn_pack is None


def test_a_pickup_goes_into_the_base_inventory_not_the_hotbar():
    scene = _scene()
    before = scene.hotbar.count(TWIG)
    from game.systems import carrying

    carrying.store(TWIG, 3, scene.backpack, scene.hotbar)
    assert scene.backpack.count(TWIG) == 3
    assert scene.hotbar.count(TWIG) == before


def test_a_pack_adds_its_slots_and_keeps_what_was_carried():
    scene = _scene()
    scene.backpack.add(STONE, 10)
    scene._wear_if_pack(WORN_PACK)
    assert scene.backpack.size == BASE + config.BACKPACK_SLOTS
    assert scene.backpack.count(STONE) == 10
    assert scene.worn_pack is WORN_PACK


def test_a_bigger_pack_replaces_a_smaller_one_and_keeps_everything():
    scene = _scene()
    scene._wear_if_pack(WORN_PACK)
    scene.backpack.add(STONE, 200)
    scene._wear_if_pack(LEATHER_PACK)
    assert scene.backpack.size == BASE + config.BACKPACK_SLOTS * 2
    assert scene.backpack.count(STONE) == 200
    assert scene.worn_pack is LEATHER_PACK


def test_a_smaller_pack_does_not_shrink_a_bigger_one():
    scene = _scene()
    scene._wear_if_pack(LEATHER_PACK)
    scene._wear_if_pack(WORN_PACK)
    assert scene.backpack.size == BASE + config.BACKPACK_SLOTS * 2
    assert scene.worn_pack is LEATHER_PACK


def test_death_drops_the_base_slots_too():
    scene = _scene()
    scene.backpack.add(STONE, 4)
    _die(scene)
    assert len(scene.loot) == 1
    assert scene.loot[0].contents.count(STONE) == 4
    assert scene.loot[0].pack is None


def test_death_drops_the_pack_and_everything_in_it():
    scene = _scene()
    scene._wear_if_pack(WORN_PACK)
    scene.backpack.add(STONE, 300)
    _die(scene)
    assert scene.loot[0].contents.count(STONE) == 300
    assert scene.loot[0].pack is WORN_PACK


def test_after_death_the_base_inventory_is_back_and_empty():
    scene = _scene()
    scene._wear_if_pack(WORN_PACK)
    scene.backpack.add(STONE, 4)
    _die(scene)
    assert scene.backpack is not None
    assert scene.backpack.size == BASE
    assert scene.backpack.used == 0
    assert scene.worn_pack is None


def test_dying_with_nothing_leaves_no_pile():
    scene = _scene()
    _die(scene)
    assert scene.loot == []


def test_walking_back_to_the_pile_returns_the_pack_and_the_goods():
    scene = _scene()
    where = pygame.Vector2(scene.player.pos)
    scene._wear_if_pack(WORN_PACK)
    scene.backpack.add(STONE, 300)
    _die(scene)
    scene._respawn_timer = 0.0
    scene.player.hp = scene.player.max_hp
    scene.player.pos = where
    scene.update(config.FIXED_DT)
    assert scene.loot == []
    assert scene.worn_pack is WORN_PACK
    assert scene.backpack.size == BASE + config.BACKPACK_SLOTS
    assert scene.backpack.count(STONE) == 300


def test_a_save_from_before_the_base_inventory_gets_one():
    # Saves pickle the whole scene, so an old one can load with no pack at all.
    scene = _scene()
    scene.backpack = None
    scene.update(config.FIXED_DT)
    assert isinstance(scene.backpack, Container)
    assert scene.backpack.size == BASE


# --- what a craft hands over ---------------------------------------------------


def test_a_crafted_tool_goes_into_the_hand_not_the_inventory():
    from game.items.item_kinds import WOOD, WOOD_PICK
    from game.items.recipes import RECIPES
    from game.systems import crafting

    scene = _scene()
    scene.backpack.add(WOOD, 10)
    recipe = next(r for r in RECIPES if r.output is WOOD_PICK)
    assert crafting.craft(recipe, scene.backpack, scene.hotbar) is WOOD_PICK
    assert scene.hotbar.count(WOOD_PICK) == 1
    assert scene.backpack.count(WOOD_PICK) == 0


def test_a_crafted_tool_falls_back_to_the_inventory_when_the_hand_is_full():
    from game.items.item_kinds import WOOD, WOOD_PICK
    from game.items.recipes import RECIPES
    from game.items.tools import WeaponTool
    from game.systems import crafting

    scene = _scene()
    for i in range(len(scene.hotbar.slots)):
        scene.hotbar.slots[i] = WeaponTool()
    scene.backpack.add(WOOD, 10)
    recipe = next(r for r in RECIPES if r.output is WOOD_PICK)
    assert crafting.craft(recipe, scene.backpack, scene.hotbar) is WOOD_PICK
    assert scene.backpack.count(WOOD_PICK) == 1


def test_crafted_materials_go_into_the_inventory():
    from game.inventory import packs
    from game.items.recipes import RECIPES
    from game.items.staff import STAFF_ITEMS
    from game.items.tools import tool_for
    from game.systems import crafting

    recipe = next(
        r
        for r in RECIPES
        if r.seconds == 0
        and tool_for(r.output) is None
        and r.output not in STAFF_ITEMS
        and not packs.is_pack(r.output)
        and sum(1 for _ in r.inputs) <= BASE
    )
    scene = _scene()
    scene._wear_if_pack(packs.PACK_SLOTS and next(iter(packs.PACK_SLOTS)))  # room to spare
    for kind, n in recipe.inputs:
        scene.backpack.add(kind, n)
    assert crafting.craft(recipe, scene.backpack, scene.hotbar) is recipe.output
    assert scene.backpack.count(recipe.output) == recipe.count
    assert scene.hotbar.count(recipe.output) == 0
