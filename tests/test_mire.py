import random

import pygame

from game import config
from game.entities.mire import Mire
from game.entities.player import Player
from game.systems import survival
from game.world import biomes, mires
from game.world.map import WorldMap

WORLD = WorldMap(rotation=23.0)


def _placed(seed: int = 1) -> list[Mire]:
    return mires.place(WORLD, random.Random(seed))


def test_mires_only_form_in_the_bog():
    for seed in range(8):
        for mire in _placed(seed):
            assert WORLD.biome_at(mire.pos) is biomes.BOG


def test_the_same_seed_makes_the_same_mires():
    assert [(m.pos, m.radius) for m in _placed(4)] == [(m.pos, m.radius) for m in _placed(4)]


def test_different_seeds_move_them():
    assert [m.pos for m in _placed(1)] != [m.pos for m in _placed(2)]


def test_they_do_not_overlap():
    for seed in range(8):
        pools = _placed(seed)
        for i, a in enumerate(pools):
            for b in pools[i + 1 :]:
                assert a.pos.distance_to(b.pos) > a.radius + b.radius


def test_there_are_enough_to_matter():
    for seed in range(8):
        assert len(_placed(seed)) >= config.MIRES_MIN


def test_standing_in_one_is_standing_in_one():
    mire = Mire(pos=pygame.Vector2(0, 0), radius=300.0)
    assert mires.holds(pygame.Vector2(0, 0), [mire])
    assert mires.holds(pygame.Vector2(299, 0), [mire])
    assert not mires.holds(pygame.Vector2(301, 0), [mire])


# --- what it costs --------------------------------------------------------


def _wading(moving: bool, dt: float = 1.0) -> Player:
    mire = Mire(pos=pygame.Vector2(0, 0), radius=300.0)
    player = Player(pos=pygame.Vector2(0, 0))
    survival.update_mire(dt, player, [mire], moving=moving)
    return player


def test_wading_through_costs_breath():
    assert _wading(moving=True).stamina == config.PLAYER_MAX_STAMINA - config.MIRE_DRAIN


def test_standing_still_in_one_costs_nothing():
    # The mire taxes WADING. Someone who has stopped is not fighting it.
    assert _wading(moving=False).stamina == config.PLAYER_MAX_STAMINA


def test_there_is_no_catching_your_breath_in_a_mire():
    # Standing still stops the drain but gets nothing back: the mire holds the
    # recovery off whether you move or not. The way through is out of it.
    mire = Mire(pos=pygame.Vector2(0, 0), radius=300.0)
    player = Player(pos=pygame.Vector2(0, 0))
    player.stamina = 0
    for _ in range(int((config.STAMINA_DELAY + 10.0) / config.FIXED_DT)):
        survival.update_mire(config.FIXED_DT, player, [mire], moving=False)
        survival.update_stamina(config.FIXED_DT, player)
    assert player.stamina == 0


def test_stepping_out_lets_you_breathe_again():
    mire = Mire(pos=pygame.Vector2(0, 0), radius=300.0)
    player = Player(pos=pygame.Vector2(10_000, 0))
    player.stamina = 0
    for _ in range(int((config.STAMINA_DELAY + 3.0) / config.FIXED_DT)):
        survival.update_mire(config.FIXED_DT, player, [mire], moving=False)
        survival.update_stamina(config.FIXED_DT, player)
    assert player.stamina > 0


def test_a_meal_still_works_in_a_mire():
    # With resting ruled out, food is the only way to breathe in there -- which
    # is what the spec means by stamina being recovered with meat.
    from game.items.item_kinds import COOKED_MEAT
    from game.systems import consume

    mire = Mire(pos=pygame.Vector2(0, 0), radius=300.0)
    player = Player(pos=pygame.Vector2(0, 0))
    player.stamina = 0
    survival.update_mire(1.0, player, [mire], moving=False)
    assert consume.eat(COOKED_MEAT, player) is True
    assert player.stamina > 0


def test_moving_outside_a_mire_costs_nothing():
    mire = Mire(pos=pygame.Vector2(0, 0), radius=300.0)
    player = Player(pos=pygame.Vector2(10_000, 0))
    survival.update_mire(1.0, player, [mire], moving=True)
    assert player.stamina == config.PLAYER_MAX_STAMINA


def test_it_drains_rather_than_refusing():
    mire = Mire(pos=pygame.Vector2(0, 0), radius=300.0)
    player = Player(pos=pygame.Vector2(0, 0))
    player.stamina = 1.0
    survival.update_mire(5.0, player, [mire], moving=True)
    assert player.stamina == 0


def test_it_never_touches_health():
    assert _wading(moving=True, dt=30.0).hp == config.PLAYER_MAX_HP


def test_a_corpse_is_left_alone():
    mire = Mire(pos=pygame.Vector2(0, 0), radius=300.0)
    player = Player(pos=pygame.Vector2(0, 0))
    player.hp = 0
    player.stamina = 50
    survival.update_mire(1.0, player, [mire], moving=True)
    assert player.stamina == 50


def test_the_bog_outside_its_mires_asks_for_nothing():
    # The drain is the mires' doing, not the biome's. Walking the bog between
    # them should be no different from walking anywhere else.
    import math

    index = biomes.RING_BIOMES.index(biomes.BOG)
    radians = math.radians(WORLD.rotation + (index + 0.5) * WORLD.sector_degrees)
    reach = WORLD.grassland_radius + WORLD.ring_width * 0.5
    spot = pygame.Vector2(
        WORLD.center.x + math.cos(radians) * reach,
        WORLD.center.y + math.sin(radians) * reach,
    )
    pools = [m for m in _placed(1) if m.pos.distance_to(spot) < m.radius]
    if pools:
        return  # that seed happened to put one right there; nothing to prove
    player = Player(pos=spot)
    survival.update_mire(5.0, player, _placed(1), moving=True)
    assert player.stamina == config.PLAYER_MAX_STAMINA


# --- going under ----------------------------------------------------------


def _sinking(stamina: float, moving: bool = False, dt: float = 1.0) -> Player:
    mire = Mire(pos=pygame.Vector2(0, 0), radius=300.0)
    player = Player(pos=pygame.Vector2(0, 0))
    player.stamina = stamina
    survival.update_mire(dt, player, [mire], moving=moving)
    return player


def test_running_out_in_a_mire_starts_costing_blood():
    # Nothing left to wade with, and a mire does not let you rest. From here
    # the only ways out are walking out of it or eating.
    assert _sinking(0.0).hp == config.PLAYER_MAX_HP - config.MIRE_SINK_DPS


def test_standing_still_does_not_save_you():
    # The drain stops when you stop; this does not. Stopping was never an
    # answer in a mire and running out is where that bites.
    assert _sinking(0.0, moving=False).hp < config.PLAYER_MAX_HP
    assert _sinking(0.0, moving=True).hp < config.PLAYER_MAX_HP


def test_with_breath_left_it_costs_nothing():
    assert _sinking(1.0, moving=False).hp == config.PLAYER_MAX_HP
    assert _sinking(60.0, moving=True).hp == config.PLAYER_MAX_HP


def test_outside_a_mire_an_empty_tank_is_harmless():
    mire = Mire(pos=pygame.Vector2(0, 0), radius=300.0)
    player = Player(pos=pygame.Vector2(10_000, 0))
    player.stamina = 0
    survival.update_mire(10.0, player, [mire], moving=True)
    assert player.hp == config.PLAYER_MAX_HP


def test_a_long_enough_sinking_does_kill():
    assert _sinking(0.0, dt=40.0).hp <= 0


def test_it_is_slower_than_the_lava():
    # A mire is somewhere to get out of; lava is somewhere to not be. Reaching
    # the edge of a middling mire on an empty tank has to be survivable.
    assert config.MIRE_SINK_DPS < config.LAVA_DPS
    crossing = config.MIRE_RADIUS_MAX / config.PLAYER_SPEED
    assert crossing * config.MIRE_SINK_DPS < config.PLAYER_MAX_HP


def test_a_corpse_is_still_left_alone():
    player = _sinking(0.0, dt=1.0)
    player.hp = 0
    survival.update_mire(1.0, player, [Mire(pos=pygame.Vector2(0, 0), radius=300.0)], moving=True)
    assert player.hp == 0


def test_sinking_does_not_quietly_let_your_breath_back():
    # The mire blocks recovery whatever it happens to be taking at the time.
    # Missed once: the empty-tank branch took health and forgot to hold the
    # recovery off, so stamina climbed back while the player drowned.
    mire = Mire(pos=pygame.Vector2(0, 0), radius=300.0)
    player = Player(pos=pygame.Vector2(0, 0))
    player.stamina = 0
    for _ in range(int(6.0 / config.FIXED_DT)):
        survival.update_mire(config.FIXED_DT, player, [mire], moving=False)
        survival.update_stamina(config.FIXED_DT, player)
    assert player.stamina == 0
    assert player.hp < config.PLAYER_MAX_HP
