import pygame

from game import config
from game.entities.loot import LootPile
from game.inventory.storage import Container
from game.items.item_kinds import CORE_SHARD, WORN_PACK


def _pile() -> LootPile:
    contents = Container.empty(4)
    contents.add(CORE_SHARD, 3)
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
