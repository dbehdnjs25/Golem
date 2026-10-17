import pygame

from game import config
from game.entities.core import Core
from game.entities.player import Player
from game.systems import survival

CENTRE = pygame.Vector2(0, 0)


def _lit_core() -> Core:
    core = Core(pos=pygame.Vector2(CENTRE))
    core.ignite()
    return core


def _hurt(pos: pygame.Vector2, hp: float = 10.0) -> Player:
    return Player(pos=pos, hp=hp)


def test_there_is_no_healing_in_the_field():
    core = _lit_core()
    player = _hurt(pygame.Vector2(core.ward_radius + 100, 0))
    survival.update_regen(5.0, player, core)
    assert player.hp == 10.0
    assert player.ward_time == 0.0


def test_there_is_no_healing_before_the_core_is_lit():
    core = Core(pos=pygame.Vector2(CENTRE))  # unignited
    player = _hurt(pygame.Vector2(CENTRE))
    survival.update_regen(5.0, player, core)
    assert player.hp == 10.0


def test_healing_starts_slow_inside_the_ward():
    core = _lit_core()
    player = _hurt(pygame.Vector2(CENTRE))
    survival.update_regen(1.0, player, core)
    assert player.hp == 10.0 + config.WARD_REGEN_BASE


def test_healing_speeds_up_the_longer_you_stay():
    core = _lit_core()
    player = _hurt(pygame.Vector2(CENTRE))
    survival.update_regen(1.0, player, core)
    first = player.hp - 10.0
    before = player.hp
    survival.update_regen(1.0, player, core)
    second = player.hp - before
    assert second > first


def test_the_rate_stops_climbing_at_the_cap():
    core = _lit_core()
    player = _hurt(pygame.Vector2(CENTRE), hp=1.0)
    player.max_hp = 10_000.0  # room to keep healing
    for _ in range(100):
        survival.update_regen(1.0, player, core)
    before = player.hp
    survival.update_regen(1.0, player, core)
    assert player.hp - before == config.WARD_REGEN_MAX


def test_stepping_out_resets_the_ramp():
    # Otherwise tagging the ward's edge between fights would bank the fast rate.
    core = _lit_core()
    player = _hurt(pygame.Vector2(CENTRE))
    player.max_hp = 10_000.0
    for _ in range(30):
        survival.update_regen(1.0, player, core)
    assert player.ward_time > 0
    player.pos = pygame.Vector2(core.ward_radius + 100, 0)
    survival.update_regen(1.0, player, core)
    assert player.ward_time == 0.0
    player.pos = pygame.Vector2(CENTRE)
    before = player.hp
    survival.update_regen(1.0, player, core)
    assert player.hp - before == config.WARD_REGEN_BASE  # slow again


def test_healing_never_passes_full():
    core = _lit_core()
    player = Player(pos=pygame.Vector2(CENTRE), hp=config.PLAYER_MAX_HP - 1)
    survival.update_regen(10.0, player, core)
    assert player.hp == config.PLAYER_MAX_HP


def test_a_dead_player_is_not_healed():
    core = _lit_core()
    player = Player(pos=pygame.Vector2(CENTRE), hp=0.0)
    survival.update_regen(10.0, player, core)
    assert player.hp == 0.0
