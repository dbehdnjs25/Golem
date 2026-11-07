"""What a dead boss opens.

Three things come off one kill, and the spec keeps them apart on purpose: the
supreme glyph is learned on the spot, the cap is a thing to carry home, and the
biome's golems start turning up in raids.
"""

import pygame

from game import config
from game.entities.boss import BOSS_KINDS
from game.entities.core import Core
from game.entities.enemy import GOLEM_KINDS, PLAIN_GOLEM, raid_kinds
from game.items import glyphs as glyph_table
from game.items.item_kinds import CORE_SIGIL
from game.systems import spoils
from game.world import biomes


def _lit() -> Core:
    core = Core(pos=pygame.Vector2(100, 100))
    core.ignite()
    return core


# --- the supreme glyph ----------------------------------------------------


def test_a_dead_boss_gives_up_its_own_supreme_glyph():
    for kind in BOSS_KINDS:
        glyph = spoils.glyph_of(kind)
        assert glyph.biome is kind.biome
        assert glyph.tier == glyph_table.SUPREME


def test_the_supreme_glyphs_come_from_nowhere_else():
    # Ruins hold the basic cut and temples the greater one. If a supreme could
    # be found in a chest, the fight would be optional.
    for glyph in glyph_table.GLYPHS:
        if glyph.tier == glyph_table.SUPREME:
            assert glyph.source == glyph_table.FROM_BOSS


def test_the_glyph_a_boss_gives_is_the_trick_it_was_throwing():
    # The spec's one rule for this step: the thing done to you becomes the
    # thing in your hand. Different names would break that on sight.
    from game.entities.boss import TRICKS

    for kind in BOSS_KINDS:
        assert spoils.glyph_of(kind).name == TRICKS[kind.tricks[2]].name


# --- the cap has to be carried home --------------------------------------


def test_a_dead_boss_drops_a_sigil():
    for kind in BOSS_KINDS:
        assert spoils.drop_of(kind) is CORE_SIGIL


def test_killing_a_boss_does_not_raise_the_cap_by_itself():
    # Otherwise the ladder climbs from wherever the player happens to be
    # standing, and there is never a reason to walk home.
    core = _lit()
    before = core.level_cap
    core.bosses_killed += 1
    assert core.level_cap == before


def test_offering_the_sigil_raises_the_cap():
    core = _lit()
    before = core.level_cap
    assert core.offer_sigil()
    assert core.level_cap == before + 10


def test_the_cap_stops_once_every_boss_has_been_answered_for():
    core = _lit()
    for _ in range(len(config.CORE_LEVEL_CAPS) - 1):
        assert core.offer_sigil()
    assert core.level_cap == config.CORE_LEVEL_CAPS[-1]
    assert not core.offer_sigil()  # nothing left to raise
    assert core.level_cap == config.CORE_LEVEL_CAPS[-1]


def test_an_unlit_core_takes_nothing():
    # There is no ladder before the core burns, so a sigil offered to a cold
    # pedestal would simply be gone.
    assert not Core(pos=pygame.Vector2(0, 0)).offer_sigil()


def test_the_cap_a_sigil_opens_is_real_headroom():
    core = _lit()
    for _ in range(config.CORE_LEVEL_CAPS[0] - 1):
        assert core.upgrade()
    assert not core.upgrade()  # at the cap
    core.offer_sigil()
    assert core.upgrade()


# --- the biome golems join the raids -------------------------------------


def test_there_is_a_golem_kind_for_every_ring_biome():
    assert len(GOLEM_KINDS) == len(biomes.RING_BIOMES) + 1  # plus the plain one
    for biome in biomes.RING_BIOMES:
        assert any(k.biome is biome for k in GOLEM_KINDS if k.biome is not None)


def test_a_biome_golem_is_tougher_than_a_plain_one():
    for kind in GOLEM_KINDS:
        if kind.biome is not None:
            assert kind.hp > PLAIN_GOLEM.hp


def test_a_biome_golem_carries_no_gimmick():
    # Numbers only. Give them their biome's trick and a raid becomes five
    # bosses at once, which is not what a raid is for.
    for kind in GOLEM_KINDS:
        assert not hasattr(kind, "trick")
        assert not hasattr(kind, "tricks")


def test_only_the_plain_golem_comes_before_any_boss_is_dead():
    assert raid_kinds(0) == (PLAIN_GOLEM,)


def test_each_dead_boss_adds_its_biome_s_golem():
    for killed in range(1, len(biomes.RING_BIOMES) + 1):
        kinds = raid_kinds(killed)
        assert len(kinds) == killed + 1
        joined = [k.biome for k in kinds if k.biome is not None]
        assert joined == list(biomes.RING_BIOMES[:killed])


def test_they_join_in_the_order_the_bosses_fall():
    # Ring order is difficulty order, so the raid thickens the same way the
    # map does rather than all at once.
    first = raid_kinds(1)
    assert first[-1].biome is biomes.RING_BIOMES[0]


def test_more_kills_than_bosses_asks_for_nothing_extra():
    assert raid_kinds(99) == raid_kinds(len(biomes.RING_BIOMES))


def test_a_joined_golem_still_marches_on_the_core():
    from game.entities.enemy import TARGET_CORE

    for kind in GOLEM_KINDS:
        assert kind.target == TARGET_CORE


# --- the spawner draws from what has been opened -------------------------


def test_an_ordinary_night_is_plain_golems_only():
    # Biome golems are raid weight. On a working night the threat is the trip
    # out, and that is scaled by distance already.
    import random

    from game.systems.enemy_spawner import EnemySpawner
    from game.world.map import WorldMap

    world = WorldMap(rotation=0.0)
    core = Core(pos=pygame.Vector2(world.center))
    core.ignite()
    core.bosses_killed = 5
    far = core.pos + pygame.Vector2(core.ward_radius * 2, 0)
    for seed in range(20):
        enemies = []
        EnemySpawner().update(
            config.GOLEM_SPAWN_INTERVAL, enemies, far, core, random.Random(seed), world
        )
        for golem in enemies:
            assert golem.kind is PLAIN_GOLEM


def test_a_raid_before_any_boss_is_plain_golems_only():
    import random

    from game.systems.enemy_spawner import EnemySpawner
    from game.world.map import WorldMap

    world = WorldMap(rotation=0.0)
    core = Core(pos=pygame.Vector2(world.center))
    core.ignite()
    for seed in range(20):
        enemies = []
        EnemySpawner().update(
            config.RAID_SPAWN_INTERVAL,
            enemies,
            core.pos,
            core,
            random.Random(seed),
            world,
            raid=True,
        )
        for golem in enemies:
            assert golem.kind is PLAIN_GOLEM


def test_a_raid_after_a_kill_can_bring_that_biome_s_golem():
    import random

    from game.systems.enemy_spawner import EnemySpawner
    from game.world.map import WorldMap

    world = WorldMap(rotation=0.0)
    core = Core(pos=pygame.Vector2(world.center))
    core.ignite()
    core.bosses_killed = 5
    seen = set()
    for seed in range(120):
        enemies = []
        EnemySpawner().update(
            config.RAID_SPAWN_INTERVAL,
            enemies,
            core.pos,
            core,
            random.Random(seed),
            world,
            raid=True,
        )
        for golem in enemies:
            seen.add(golem.kind.key)
    assert len(seen) > 1  # the crowd is mixed, not one sort repeated
    assert seen <= {k.key for k in raid_kinds(5)}


# --- offering it at the core ---------------------------------------------


def _at_core(scene):
    scene.player.pos.update(scene.core.pos)


def test_carrying_a_sigil_to_the_lit_core_opens_the_next_cap():
    import pygame as pg

    from game.scenes.play import PlayScene

    scene = PlayScene()
    scene.core.ignite()
    scene.hotbar.add(CORE_SIGIL, 1)
    before = scene.core.level_cap
    _at_core(scene)
    scene.handle_event(pg.event.Event(pg.KEYDOWN, key=pg.K_e))
    scene.update(config.FIXED_DT)
    assert scene.core.level_cap == before + 10
    assert scene._carried(CORE_SIGIL) == 0  # it is spent, not kept


def test_a_sigil_is_not_spent_when_there_is_no_cap_left():
    import pygame as pg

    from game.scenes.play import PlayScene

    scene = PlayScene()
    scene.core.ignite()
    scene.core.sigils_taken = len(config.CORE_LEVEL_CAPS) - 1
    scene.hotbar.add(CORE_SIGIL, 1)
    _at_core(scene)
    scene.handle_event(pg.event.Event(pg.KEYDOWN, key=pg.K_e))
    scene.update(config.FIXED_DT)
    assert scene._carried(CORE_SIGIL) == 1


def test_an_unlit_core_does_not_take_one():
    import pygame as pg

    from game.scenes.play import PlayScene

    scene = PlayScene()
    scene.hotbar.add(CORE_SIGIL, 1)
    _at_core(scene)
    scene.handle_event(pg.event.Event(pg.KEYDOWN, key=pg.K_e))
    scene.update(config.FIXED_DT)
    assert scene._carried(CORE_SIGIL) == 1
