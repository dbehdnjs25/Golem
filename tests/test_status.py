import pygame

from game import config
from game.entities.player import Player
from game.systems import status


def _lit(seconds: float = config.BURN_SECONDS) -> Player:
    player = Player(pos=pygame.Vector2(0, 0))
    status.ignite(player, seconds)
    return player


def test_a_fresh_player_is_not_burning():
    assert not Player(pos=pygame.Vector2(0, 0)).burning


def test_catching_fire_sets_a_clock():
    player = _lit()
    assert player.burning
    assert player.burn_timer == config.BURN_SECONDS


def test_burning_costs_health_over_time():
    player = _lit()
    status.update_burn(1.0, player)
    assert player.hp == config.PLAYER_MAX_HP - config.BURN_DPS


def test_it_goes_out_on_its_own():
    player = _lit()
    status.update_burn(config.BURN_SECONDS + 1.0, player)
    assert not player.burning


def test_it_only_charges_for_the_time_it_was_actually_alight():
    # Handed a step longer than the remaining burn, it must not bill for the
    # overhang -- a long frame would otherwise cost more than the fire did.
    player = _lit(1.0)
    status.update_burn(10.0, player)
    assert player.hp == config.PLAYER_MAX_HP - config.BURN_DPS * 1.0


def test_catching_fire_again_refreshes_rather_than_stacks():
    # Standing in lava relights every frame. Stacking would turn a two-second
    # wade into a minute of burning.
    player = _lit()
    status.update_burn(3.0, player)
    status.ignite(player, config.BURN_SECONDS)
    assert player.burn_timer == config.BURN_SECONDS


def test_a_longer_fire_is_not_cut_short_by_a_weaker_one():
    player = _lit(12.0)
    status.ignite(player, config.BURN_SECONDS)
    assert player.burn_timer == 12.0


def test_burning_cannot_kill_you_from_nothing():
    # It is a tail on something else, not an execution in its own right.
    player = _lit()
    player.hp = 1.0
    status.update_burn(config.BURN_SECONDS, player)
    assert player.hp > 0


def test_a_corpse_does_not_burn():
    player = _lit()
    player.hp = 0
    status.update_burn(1.0, player)
    assert player.hp == 0


def test_the_total_of_one_burn_is_small_next_to_the_lava_itself():
    # The lingering is the point, not the damage. A burn that outweighed the
    # pool would make the pool the lesser hazard.
    whole = config.BURN_DPS * config.BURN_SECONDS
    assert whole < config.LAVA_DPS


def test_standing_in_the_fire_does_not_bill_twice():
    # Being in lava AND on fire is one fire, not two. The pool charges its own
    # rate; the burn must not stack on top of the thing that lit it.
    player = _lit()
    status.update_burn(1.0, player, at_source=True)
    assert player.hp == config.PLAYER_MAX_HP


def test_the_clock_does_not_run_down_at_the_source_either():
    # Otherwise a long wade would burn the five seconds off before the player
    # ever got out, and stepping clear would cost nothing at all.
    player = _lit()
    status.update_burn(4.0, player, at_source=True)
    assert player.burn_timer == config.BURN_SECONDS


def test_it_starts_charging_the_moment_you_are_clear():
    player = _lit()
    status.update_burn(3.0, player, at_source=True)
    status.update_burn(1.0, player)
    assert player.hp == config.PLAYER_MAX_HP - config.BURN_DPS
