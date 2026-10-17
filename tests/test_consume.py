import pygame
import pytest

from game import config
from game.entities.player import Player
from game.items.item_kinds import COOKED_MEAT, ITEM_KINDS, RAW_MEAT, STONE
from game.systems import consume


def _hungry(stamina: float = 0.0, hp: float = config.PLAYER_MAX_HP) -> Player:
    player = Player(pos=pygame.Vector2(0, 0))
    player.stamina = stamina
    player.hp = hp
    return player


def test_cooked_meat_gives_wind_and_takes_nothing():
    player = _hungry()
    assert consume.eat(COOKED_MEAT, player) is True
    assert player.stamina == config.MEAT_STAMINA
    assert player.hp == config.PLAYER_MAX_HP


def test_raw_meat_gives_the_same_wind_and_takes_blood():
    # The spec's trade: the same breath back, paid for out of your health.
    # Walking to a hearth is what makes it free.
    player = _hungry()
    assert consume.eat(RAW_MEAT, player) is True
    assert player.stamina == config.MEAT_STAMINA
    assert player.hp == config.PLAYER_MAX_HP - config.RAW_MEAT_HP_COST


def test_raw_meat_cannot_kill_you():
    # Dying of a snack reads as a bug, not as a hard choice.
    player = _hungry(hp=1.0)
    assert consume.eat(RAW_MEAT, player) is True
    assert player.hp > 0


def test_eating_on_a_full_tank_is_refused_rather_than_wasted():
    player = _hungry(stamina=config.PLAYER_MAX_STAMINA)
    assert consume.eat(COOKED_MEAT, player) is False
    assert player.hp == config.PLAYER_MAX_HP


def test_wind_does_not_overflow():
    player = _hungry(stamina=config.PLAYER_MAX_STAMINA - 1)
    consume.eat(COOKED_MEAT, player)
    assert player.stamina == player.max_stamina


def test_a_pickaxe_is_not_food():
    player = _hungry()
    assert consume.eat(ITEM_KINDS["stone_pick"], player) is False
    assert consume.eat(STONE, player) is False
    assert player.stamina == 0


def test_a_corpse_does_not_eat():
    player = _hungry(hp=0.0)
    assert consume.eat(COOKED_MEAT, player) is False


def test_everything_edible_is_on_one_list():
    # So a new food cannot be added to the catalogue and silently not work.
    assert consume.EDIBLE
    for kind in consume.EDIBLE:
        assert consume.eat(kind, _hungry(hp=config.PLAYER_MAX_HP / 2)) is True


def test_cooking_happens_at_a_hearth_and_costs_time():
    from game.items import recipes

    cook = next(r for r in recipes.RECIPES if r.output is COOKED_MEAT)
    assert cook.station == recipes.HEARTH_S
    assert cook.seconds > 0
    assert {k for k, _ in cook.inputs} == {RAW_MEAT}


def test_cooked_meat_is_only_ever_made_indoors():
    # Stations go inside the ward, so cooking is a reason to walk home -- which
    # is the whole point of raw meat costing blood out in the field.
    from game.items import recipes

    assert recipes.STATION_OF.get(ITEM_KINDS["hearth"]) == {recipes.HEARTH_S}


def test_raw_meat_is_worth_carrying_home():
    with pytest.raises(StopIteration):
        # There is no bare-handed way to cook it.
        from game.items import recipes

        next(r for r in recipes.RECIPES if r.output is COOKED_MEAT and r.station == recipes.NOWHERE)


# --- the potion -----------------------------------------------------------

POTION = ITEM_KINDS["potion"]


def test_a_potion_gives_blood_back_at_once():
    player = _hungry(stamina=config.PLAYER_MAX_STAMINA, hp=10.0)
    assert consume.eat(POTION, player) is True
    assert player.hp == 10.0 + config.POTION_HEAL


def test_it_does_not_overflow():
    player = _hungry(stamina=0.0, hp=config.PLAYER_MAX_HP - 1)
    consume.eat(POTION, player)
    assert player.hp == player.max_hp


def test_drinking_at_full_health_is_refused_rather_than_wasted():
    player = _hungry(stamina=0.0, hp=config.PLAYER_MAX_HP)
    assert consume.eat(POTION, player) is False


def test_a_potion_gives_no_wind():
    # Meat is for breath and this is for blood. One item doing both would make
    # the other pointless.
    player = _hungry(stamina=0.0, hp=10.0)
    consume.eat(POTION, player)
    assert player.stamina == 0


def test_the_potion_is_brewed_out_of_the_snowfield_not_the_bog():
    # The spec puts the bog fourth because its drain is unfair "before cooking
    # and potions exist". A potion gated behind bog moss would be a circle.
    from game.items import recipes
    from game.world import biomes

    brew = next(r for r in recipes.RECIPES if r.output is POTION)
    wanted = {k for k, _ in brew.inputs}
    assert biomes.SNOWFIELD.material in wanted
    assert biomes.BOG.material not in wanted
    assert brew.station == recipes.HEARTH_S


def test_a_potion_is_dearer_than_a_meal():
    # It is the scarce answer; meat is the common one. If a potion were cheap
    # the ward's slow healing would never be worth standing still for.
    from game.items import recipes

    brew = next(r for r in recipes.RECIPES if r.output is POTION)
    cook = next(r for r in recipes.RECIPES if r.output is COOKED_MEAT)
    assert sum(n for _, n in brew.inputs) > sum(n for _, n in cook.inputs)
