import math

import pygame

from game import config
from game.entities.core import Core


def _core() -> Core:
    return Core(pos=pygame.Vector2(0, 0))


def test_point_inside_sync_range():
    c = Core(pos=pygame.Vector2(1000, 800), sync_radius=100)
    assert c.is_in_sync_range(pygame.Vector2(1050, 800)) is True


def test_point_outside_sync_range():
    c = Core(pos=pygame.Vector2(1000, 800), sync_radius=100)
    assert c.is_in_sync_range(pygame.Vector2(1200, 800)) is False


def test_point_exactly_on_sync_boundary_is_inside():
    # dist == sync_radius must count as in-range (impl uses <=)
    c = Core(pos=pygame.Vector2(1000, 800), sync_radius=100)
    assert c.is_in_sync_range(pygame.Vector2(1100, 800)) is True


def test_an_unignited_core_has_no_ward_at_all():
    core = _core()
    assert core.level == 0
    assert core.ignited is False
    assert core.ward_radius == 0.0
    # Nothing is sheltered before ignition -- that is the pressure to build it.
    assert core.is_in_ward(pygame.Vector2(0, 0)) is False


def test_ignition_puts_the_core_at_level_one():
    core = _core()
    core.ignite()
    assert core.ignited is True
    assert core.level == 1
    assert core.ward_radius == config.WARD_RADIUS_BASE


def test_igniting_twice_changes_nothing():
    core = _core()
    core.ignite()
    core.upgrade()
    core.ignite()
    assert core.level == 2


def test_the_full_ward_reaches_its_stated_maximum():
    core = _core()
    core.bosses_killed = len(config.CORE_LEVEL_CAPS)
    core.ignite()
    while core.upgrade():
        pass
    assert core.level == config.CORE_MAX_LEVEL
    assert math.isclose(core.ward_radius, config.WARD_RADIUS_MAX, rel_tol=1e-9)


def test_fifty_levels_treble_the_ward():
    # The opening ward is a third of the full one, so the ladder is worth
    # climbing without the first day feeling cramped.
    assert math.isclose(config.WARD_RADIUS_MAX / config.WARD_RADIUS_BASE, 3.0, rel_tol=1e-9)


def test_the_ward_grows_by_the_same_ratio_every_level():
    # Absolute growth would make an early level invisible and a late one
    # enormous. A constant ratio makes every upgrade feel the same size.
    core = _core()
    core.bosses_killed = len(config.CORE_LEVEL_CAPS)
    core.ignite()
    ratios = []
    for _ in range(10):
        before = core.ward_radius
        core.upgrade()
        ratios.append(core.ward_radius / before)
    assert max(ratios) - min(ratios) < 1e-9


def test_the_level_cap_starts_at_ten_and_a_boss_opens_each_one():
    core = _core()
    core.ignite()
    assert core.level_cap == config.CORE_LEVEL_CAPS[0] == 10
    for killed, cap in enumerate(config.CORE_LEVEL_CAPS[1:], start=1):
        core.bosses_killed = killed
        assert core.level_cap == cap


def test_upgrading_stops_dead_at_the_cap():
    core = _core()
    core.ignite()
    while core.upgrade():
        pass
    assert core.level == config.CORE_LEVEL_CAPS[0]
    assert core.can_upgrade is False
    core.bosses_killed = 1  # a boss item lifts it
    assert core.can_upgrade is True
    assert core.upgrade() is True
    assert core.level == config.CORE_LEVEL_CAPS[0] + 1


def test_an_unignited_core_cannot_be_upgraded():
    core = _core()
    assert core.can_upgrade is False
    assert core.upgrade() is False
    assert core.level == 0


def test_the_ward_is_a_circle_around_the_core():
    core = _core()
    core.ignite()
    r = core.ward_radius
    assert core.is_in_ward(pygame.Vector2(r - 1, 0)) is True
    assert core.is_in_ward(pygame.Vector2(r + 1, 0)) is False


def test_the_ward_stops_growing_at_its_own_cap():
    core = _core()
    core.bosses_killed = len(config.CORE_LEVEL_CAPS)
    core.ignite()
    while core.level < config.WARD_MAX_LEVEL:
        core.upgrade()
    full = core.ward_radius
    assert math.isclose(full, config.WARD_RADIUS_MAX, rel_tol=1e-9)
    # Every level past it is the same ward. Core levels keep going -- what they
    # buy beyond this point is not radius.
    while core.upgrade():
        assert core.ward_radius == full
    assert core.level == config.CORE_MAX_LEVEL


def test_the_ward_cap_sits_below_the_level_cap():
    assert 1 < config.WARD_MAX_LEVEL < config.CORE_MAX_LEVEL


# --- hit points -----------------------------------------------------------


def test_an_unlit_core_has_nothing_to_damage():
    # There is no ward, no raid and no stake before ignition. A pedestal with
    # a health bar would be promising a fight that cannot happen yet.
    core = Core(pos=pygame.Vector2(0, 0))
    assert core.max_hp == 0
    assert core.hp == 0
    assert not core.is_destroyed


def test_lighting_it_brings_it_up_at_full_health():
    core = Core(pos=pygame.Vector2(0, 0))
    core.ignite()
    assert core.max_hp > 0
    assert core.hp == core.max_hp


def test_levelling_raises_the_ceiling_and_the_gain_is_given():
    # Growing the core is the only way to make it tougher, so a level must not
    # merely raise a cap the player then has to pay to fill.
    core = Core(pos=pygame.Vector2(0, 0))
    core.ignite()
    before_cap, before_hp = core.max_hp, core.hp
    core.upgrade()
    assert core.max_hp > before_cap
    assert core.hp == before_hp + (core.max_hp - before_cap)


def test_damage_stops_at_zero_and_reads_as_destroyed():
    core = Core(pos=pygame.Vector2(0, 0))
    core.ignite()
    core.damage(core.max_hp * 10)
    assert core.hp == 0  # never negative; the bar would draw backwards
    assert core.is_destroyed


def test_repair_spends_whole_units_and_never_overfills():
    core = Core(pos=pygame.Vector2(0, 0))
    core.ignite()
    core.damage(config.CORE_REPAIR_PER_ITEM * 2)
    assert core.repair(10) == 2  # only two were needed, so only two are taken
    assert core.hp == core.max_hp


def test_repairing_a_whole_core_takes_nothing():
    core = Core(pos=pygame.Vector2(0, 0))
    core.ignite()
    assert core.repair(5) == 0
    assert core.hp == core.max_hp


def test_a_destroyed_core_can_still_be_repaired():
    # Defeat is a signal this far; whether a run can come back from it is the
    # ending's business, not the core's.
    core = Core(pos=pygame.Vector2(0, 0))
    core.ignite()
    core.damage(core.max_hp)
    assert core.repair(1) == 1
    assert not core.is_destroyed
