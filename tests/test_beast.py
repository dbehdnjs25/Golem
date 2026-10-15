import random

import pygame

from game import config
from game.entities.beast import BEAST_KINDS, RABBIT, WOLF, Beast
from game.entities.core import Core
from game.entities.enemy import TARGET_PLAYER
from game.systems.beast_spawner import BeastSpawner
from game.world.map import WorldMap

WORLD = WorldMap()
CENTRE = WORLD.center


def _lit() -> Core:
    core = Core(pos=pygame.Vector2(CENTRE))
    core.ignite()
    return core


def test_every_beast_hunts_the_player_not_the_core():
    # That is the whole split. A golem walks past you to reach the core; an
    # animal is the thing in your way while you are out gathering.
    for kind in BEAST_KINDS:
        assert kind.target == TARGET_PLAYER


def test_a_wolf_closes_and_a_rabbit_runs():
    player = CENTRE + pygame.Vector2(200, 0)
    wolf = Beast(pos=pygame.Vector2(CENTRE), kind=WOLF)
    rabbit = Beast(pos=pygame.Vector2(CENTRE), kind=RABBIT)
    before = CENTRE.distance_to(player)
    wolf.update(0.5, player, WORLD)
    rabbit.update(0.5, player, WORLD)
    assert wolf.pos.distance_to(player) < before
    assert rabbit.pos.distance_to(player) > before


def test_a_rabbit_does_no_harm_by_touching_you():
    assert RABBIT.contact_dps == 0
    assert WOLF.contact_dps > 0


def test_beasts_stay_on_the_map():
    beast = Beast(pos=CENTRE + pygame.Vector2(WORLD.radius - 5, 0), kind=RABBIT)
    beast.update(2.0, pygame.Vector2(CENTRE), WORLD)  # flees outward
    assert WORLD.contains(beast.pos)


def test_a_beast_drops_what_its_kind_says():
    for kind in BEAST_KINDS:
        assert kind.drops
        for _item, n in kind.drops:
            assert n >= 1


def test_nothing_comes_out_in_daylight():
    spawner = BeastSpawner()
    beasts: list[Beast] = []
    spawner.update(
        config.BEAST_SPAWN_INTERVAL, beasts, CENTRE, _lit(), random.Random(1), WORLD, night=False
    )
    assert beasts == []  # daylight, so the hour stops it before anything else


def _at_the_rim(core: Core) -> pygame.Vector2:
    """Where a player standing at the ward's edge is -- within reach of them."""
    return core.pos + pygame.Vector2(core.ward_radius, 0)


def test_night_brings_them_out():
    core = _lit()
    spawner = BeastSpawner()
    beasts: list[Beast] = []
    spawner.update(
        config.BEAST_SPAWN_INTERVAL,
        beasts,
        _at_the_rim(core),
        core,
        random.Random(1),
        WORLD,
        night=True,
    )
    assert len(beasts) == 1


def test_deep_inside_the_ward_nothing_reaches_you_at_all():
    # Standing at the core, every spot within their reach is inside the ward,
    # so none is a legal place to appear. The safe ground is properly safe.
    core = _lit()
    spawner = BeastSpawner()
    beasts: list[Beast] = []
    spawner.update(
        config.BEAST_SPAWN_INTERVAL, beasts, core.pos, core, random.Random(1), WORLD, night=True
    )
    assert beasts == []


def test_they_come_before_the_core_is_lit():
    # The opening's only threat. Golems wait for the core; these do not, and
    # with nowhere to heal a night out is what makes lighting it worth doing.
    spawner = BeastSpawner()
    beasts: list[Beast] = []
    unlit = Core(pos=pygame.Vector2(CENTRE))
    spawner.update(
        config.BEAST_SPAWN_INTERVAL, beasts, CENTRE, unlit, random.Random(1), WORLD, night=True
    )
    assert len(beasts) == 1  # no ward yet, so nowhere is off limits


def test_they_gather_outside_the_ward_not_inside_it():
    # They press around the edge; the ward is still the one safe place.
    spawner = BeastSpawner()
    core = _lit()
    for seed in range(30):
        beasts: list[Beast] = []
        spawner = BeastSpawner()
        beast = spawner.update(
            config.BEAST_SPAWN_INTERVAL,
            beasts,
            _at_the_rim(core),
            core,
            random.Random(seed),
            WORLD,
            night=True,
        )
        if beast is not None:
            assert not core.is_in_ward(beast.pos)


def test_daylight_does_not_make_the_ones_already_out_vanish():
    # A wolf that evaporates at sunrise is a timer, not an animal.
    spawner = BeastSpawner()
    beasts = [Beast(pos=pygame.Vector2(CENTRE), kind=WOLF)]
    spawner.update(
        config.BEAST_SPAWN_INTERVAL, beasts, CENTRE, _lit(), random.Random(1), WORLD, night=False
    )
    assert len(beasts) == 1


def test_the_cap_holds():
    spawner = BeastSpawner()
    beasts = [Beast(pos=pygame.Vector2(CENTRE), kind=WOLF)] * config.BEAST_SPAWN_MAX
    assert (
        spawner.update(
            config.BEAST_SPAWN_INTERVAL,
            beasts,
            CENTRE,
            _lit(),
            random.Random(1),
            WORLD,
            night=True,
        )
        is None
    )


def test_a_rabbit_holds_still_until_you_are_close():
    far = CENTRE + pygame.Vector2(config.BEAST_FLEE_RANGE * 3, 0)
    rabbit = Beast(pos=pygame.Vector2(CENTRE), kind=RABBIT)
    rabbit.update(0.5, far, WORLD)
    assert rabbit.pos == CENTRE  # it has not noticed you


def test_the_ward_keeps_animals_out_too():
    # Otherwise a single wolf cancels the healing the ward exists to give, and
    # the safe ground stops being safe.
    from game.entities.player import Player
    from game.systems import combat

    core = _lit()
    player = Player(pos=pygame.Vector2(CENTRE))
    wolf = Beast(pos=pygame.Vector2(CENTRE), kind=WOLF)
    combat.update_beasts(0.1, [wolf], player, WORLD, core, random.Random(1), [])
    assert not core.is_in_ward(wolf.pos)
    assert player.hp == config.PLAYER_MAX_HP


def test_they_turn_up_near_a_player_who_has_walked_out():
    # The job is to tax the trip out. Pinned to the ward's rim, they would be
    # gathering twenty thousand units behind someone mining in the ring.
    spawner = BeastSpawner()
    core = _lit()
    far = core.pos + pygame.Vector2(WORLD.grassland_radius * 0.9, 0)
    beasts: list[Beast] = []
    beast = spawner.update(
        config.BEAST_SPAWN_INTERVAL, beasts, far, core, random.Random(3), WORLD, night=True
    )
    assert beast is not None
    assert beast.pos.distance_to(far) <= config.BEAST_RING


def test_you_can_outrun_a_wolf_and_run_down_a_rabbit():
    # The two numbers that decide whether a night out is a tax or a death
    # sentence. Slower than you, a wolf is a fight you may always refuse;
    # faster, and leaving the ward after dark would simply be a mistake.
    #
    # The rabbit is the other end: above your speed it could never be caught at
    # all, and an animal that cannot be caught reads as broken rather than shy.
    assert WOLF.kind.speed < config.PLAYER_SPEED
    assert RABBIT.kind.speed < config.PLAYER_SPEED
    assert RABBIT.kind.speed > WOLF.kind.speed  # still the harder one to corner
