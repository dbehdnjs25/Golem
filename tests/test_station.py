import pygame

from game import config
from game.entities.core import Core
from game.entities.station import Station, place, stations_at
from game.items import recipes
from game.items.item_kinds import BENCH, BLAST_FURNACE, FINE_BENCH, SMELTER


def _lit(level: int = 1) -> Core:
    core = Core(pos=pygame.Vector2(0, 0))
    core.ignite()
    core.bosses_killed = len(config.CORE_LEVEL_CAPS)
    while core.level < level:
        core.upgrade()
    return core


def _inside(core: Core, fraction: float = 0.5) -> pygame.Vector2:
    return core.pos + pygame.Vector2(core.ward_radius * fraction, 0)


def test_a_station_can_be_placed_inside_the_ward():
    core, built = _lit(), []
    assert place(BENCH, _inside(core), built, core) is True
    assert len(built) == 1
    assert built[0].kind is BENCH


def test_nothing_can_be_placed_outside_the_ward():
    # Stations in the ward is one of the three reasons the spec gives for
    # coming home at all.
    core, built = _lit(), []
    outside = core.pos + pygame.Vector2(core.ward_radius + 50, 0)
    assert place(BENCH, outside, built, core) is False
    assert built == []


def test_nothing_can_be_placed_before_the_core_is_lit():
    core, built = Core(pos=pygame.Vector2(0, 0)), []  # never ignited
    assert place(BENCH, core.pos, built, core) is False
    assert built == []


def test_stations_do_not_overlap():
    core, built = _lit(), []
    spot = _inside(core)
    assert place(BENCH, spot, built, core) is True
    assert place(SMELTER, spot, built, core) is False
    assert len(built) == 1


def test_a_station_may_stand_just_clear_of_another():
    core, built = _lit(), []
    spot = _inside(core)
    place(BENCH, spot, built, core)
    clear = spot + pygame.Vector2(config.STATION_RADIUS * 2 + 1, 0)
    assert place(SMELTER, clear, built, core) is True


def test_the_blast_furnace_needs_a_wide_enough_ward():
    # It takes up room, so it waits on the core -- which is what puts steel
    # behind levelling rather than behind grinding.
    narrow, built = _lit(1), []
    assert narrow.ward_radius < config.BLAST_FURNACE_MIN_WARD
    assert place(BLAST_FURNACE, _inside(narrow), built, narrow) is False

    wide = _lit(config.WARD_MAX_LEVEL)
    assert wide.ward_radius >= config.BLAST_FURNACE_MIN_WARD
    assert place(BLAST_FURNACE, _inside(wide), built, wide) is True


def test_the_furnace_requirement_sits_inside_the_ladder():
    # Unreachable would make steel impossible; reachable at level one would
    # make the requirement decorative.
    assert config.WARD_RADIUS_BASE < config.BLAST_FURNACE_MIN_WARD < config.WARD_RADIUS_MAX


def test_standing_near_a_bench_opens_the_bench():
    core, built = _lit(), []
    spot = _inside(core)
    place(BENCH, spot, built, core)
    assert stations_at(spot, built) == {recipes.NOWHERE, recipes.BENCH_S}


def test_standing_nowhere_near_anything_opens_nothing():
    core, built = _lit(), []
    place(BENCH, _inside(core), built, core)
    far = core.pos + pygame.Vector2(config.STATION_REACH * 5, 0)
    assert stations_at(far, built) == {recipes.NOWHERE}


def test_every_bench_in_reach_is_open_at_once():
    # Stations are not one ladder. A bench and a fine bench are, but a smelter
    # and a hearth are different jobs -- so standing between two opens both
    # lists rather than ranking one against something it has no relation to.
    core, built = _lit(config.WARD_MAX_LEVEL), []
    a = _inside(core, 0.2)
    b = a + pygame.Vector2(config.STATION_RADIUS * 2 + 1, 0)
    place(BENCH, a, built, core)
    place(FINE_BENCH, b, built, core)
    between = (a + b) / 2
    assert stations_at(between, built) == {recipes.NOWHERE, recipes.BENCH_S, recipes.FINE_S}


def test_a_station_is_what_it_was_placed_as():
    core, built = _lit(), []
    place(SMELTER, _inside(core), built, core)
    assert isinstance(built[0], Station)
    assert stations_at(built[0].pos, built) == {recipes.NOWHERE, recipes.SMELTER_S}
