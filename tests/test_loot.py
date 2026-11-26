import pygame

from game import config
from game.entities.loot import LootPile
from game.inventory.storage import Container
from game.items.item_kinds import CORE_SHARD, STONE, WORN_PACK


def _pile() -> LootPile:
    # Ordinary goods. A pile holding a core shard keeps forever -- see the
    # tests at the foot of this file -- so the clock cannot be measured with
    # one in it.
    contents = Container.empty(4)
    contents.add(STONE, 3)
    return LootPile(pos=pygame.Vector2(0, 0), contents=contents, pack=WORN_PACK)


def test_a_fresh_pile_has_its_whole_lifetime():
    pile = _pile()
    assert pile.ttl == config.LOOT_LIFETIME
    assert pile.is_gone is False


def test_time_runs_it_down():
    pile = _pile()
    pile.update(10.0)
    assert pile.ttl == config.LOOT_LIFETIME - 10.0
    assert pile.is_gone is False


def test_it_is_gone_once_the_clock_runs_out():
    pile = _pile()
    pile.update(config.LOOT_LIFETIME)
    assert pile.is_gone is True


def test_the_clock_does_not_run_below_zero():
    # Otherwise a long-dead pile would keep accruing a meaningless debt.
    pile = _pile()
    pile.update(config.LOOT_LIFETIME * 5)
    assert pile.ttl == 0.0


def test_the_lifetime_is_shorter_than_a_day():
    # It has to bite inside the day it happened, or it is not a deadline.
    assert 0 < config.LOOT_LIFETIME < config.DAY_TOTAL


# --- the one thing a pile will not let rot --------------------------------


def test_a_pile_holding_a_shard_waits_forever():
    # The world scatters exactly as many as the core asks for. One rotting on
    # the ground would leave a run that can never be started, and the player
    # would have no way of knowing why.
    pack = Container.empty(4)
    pack.add(CORE_SHARD, 1)
    pile = LootPile(pos=pygame.Vector2(0, 0), contents=pack)
    pile.update(config.LOOT_LIFETIME * 10)
    assert not pile.is_gone
    assert pile.ttl == config.LOOT_LIFETIME  # its clock never even started


def test_an_ordinary_pile_still_runs_out():
    pack = Container.empty(4)
    pack.add(STONE, 3)
    pile = LootPile(pos=pygame.Vector2(0, 0), contents=pack)
    pile.update(config.LOOT_LIFETIME + 1)
    assert pile.is_gone


def test_taking_the_shard_out_starts_the_clock():
    # Not a special pile: a pile that happens to hold one. Once it does not,
    # it is as perishable as any other.
    pack = Container.empty(4)
    pack.add(CORE_SHARD, 1)
    pack.add(STONE, 2)
    pile = LootPile(pos=pygame.Vector2(0, 0), contents=pack)
    pile.update(config.LOOT_LIFETIME * 2)
    assert not pile.is_gone
    pack.remove(CORE_SHARD, 1)
    pile.update(config.LOOT_LIFETIME + 1)
    assert pile.is_gone
