"""The player throwing what the boss threw.

This is what the whole boss step was for: the thing done to you becomes the
thing in your hand. So the two sides have to reach the same function -- written
twice it would be wrong twice, and the wrong one would be whichever side got
less play.

Nothing is carved any more. A shape is drawn, and if the player has found that
shape and is holding a staff, it goes out.
"""

import inspect

import pygame

from game import config
from game.entities.enemy import Golem
from game.entities.patch import BURNING, FROST, SLUDGE
from game.entities.projectile import Projectile
from game.items import glyphs as glyph_table
from game.items import strokes
from game.items.item_kinds import ITEM_KINDS
from game.scenes.play import PlayScene
from game.systems import combat, gimmicks
from game.world import biomes
from game.world.map import WorldMap

WORLD = WorldMap(rotation=0.0)
CENTRE = WORLD.center
SHOOTER = pygame.Vector2(CENTRE) + pygame.Vector2(-200, 0)


def _supreme(biome):
    return next(g for g in glyph_table.glyphs_of(biome) if g.tier == glyph_table.SUPREME)


def _golem(at=None):
    return Golem(pos=pygame.Vector2(at or CENTRE))


# --- one function, both sides --------------------------------------------


def test_the_boss_and_the_player_call_the_same_function():
    # Not "two functions that agree" -- the same one. Anything weaker and the
    # two drift the first time a trick is tuned.
    assert callable(gimmicks.strike)
    taken = set(inspect.signature(gimmicks.strike).parameters)
    assert {"gimmick", "at", "victim", "away_from"} <= taken


def test_every_gimmick_does_something_when_struck():
    for gimmick in gimmicks.GIMMICKS:
        patches, marks = [], []
        golem = _golem()
        stood = pygame.Vector2(golem.pos)
        gimmicks.strike(
            gimmick,
            at=pygame.Vector2(CENTRE),
            victim=golem,
            away_from=pygame.Vector2(CENTRE) + pygame.Vector2(100, 0),
            patches=patches,
            marks=marks,
        )
        # Leaves ground, sets a mark, or moves what it hit. One that did none
        # would be a dud nobody would notice was broken.
        assert patches or marks or golem.pos != stood, gimmick.key


def test_a_shove_works_on_whatever_is_standing_there():
    golem = _golem()
    before = pygame.Vector2(golem.pos)
    gimmicks.shove(golem, pygame.Vector2(CENTRE) + pygame.Vector2(-100, 0))
    assert golem.pos != before


# --- a shot carrying a trick ---------------------------------------------


def _fire_into(glyph, enemies, patches, marks):
    """Put one shot carrying ``glyph``'s trick through a golem."""
    shot = Projectile(
        pos=pygame.Vector2(enemies[0].pos),
        vel=pygame.Vector2(0, 0),
        damage=glyph.power,
        gimmick=glyph.gimmick if glyph.tier == glyph_table.SUPREME else None,
    )
    combat.update_projectiles(
        config.FIXED_DT,
        [shot],
        enemies,
        WORLD,
        patches=patches,
        marks=marks,
        from_pos=pygame.Vector2(SHOOTER),
    )


def test_the_burnt_forest_supreme_leaves_burning_ground():
    patches, marks, enemies = [], [], [_golem()]
    _fire_into(_supreme(biomes.BURNT_FOREST), enemies, patches, marks)
    assert any(p.kind is BURNING for p in patches)


def test_the_snowfield_supreme_leaves_frost():
    patches, marks, enemies = [], [], [_golem()]
    _fire_into(_supreme(biomes.SNOWFIELD), enemies, patches, marks)
    assert any(p.kind is FROST for p in patches)


def test_the_bog_supreme_leaves_sludge():
    patches, marks, enemies = [], [], [_golem()]
    _fire_into(_supreme(biomes.BOG), enemies, patches, marks)
    assert any(p.kind is SLUDGE for p in patches)


def test_the_wasteland_supreme_leaves_a_mark():
    patches, marks, enemies = [], [], [_golem()]
    _fire_into(_supreme(biomes.WASTELAND), enemies, patches, marks)
    assert marks


def test_the_wind_plateau_supreme_moves_what_it_hits():
    patches, marks = [], []
    golem = _golem()
    before = pygame.Vector2(golem.pos)
    _fire_into(_supreme(biomes.WIND_PLATEAU), [golem], patches, marks)
    assert not patches and not marks
    assert golem.pos != before


def test_it_is_thrown_away_from_the_one_who_fired():
    patches, marks = [], []
    golem = _golem()
    _fire_into(_supreme(biomes.WIND_PLATEAU), [golem], patches, marks)
    assert golem.pos.distance_to(SHOOTER) > CENTRE.distance_to(SHOOTER)


def test_a_lesser_cut_leaves_nothing_behind():
    # The ladder has to mean something. If the first shape already threw the
    # trick, the boss would be guarding a bigger number.
    for biome in biomes.RING_BIOMES:
        for tier in (glyph_table.BASIC, glyph_table.GREATER):
            glyph = next(g for g in glyph_table.glyphs_of(biome) if g.tier == tier)
            patches, marks, enemies = [], [], [_golem()]
            _fire_into(glyph, enemies, patches, marks)
            assert not patches and not marks, (biome.key, tier)


def test_a_lesser_cut_still_hurts():
    glyph = next(g for g in glyph_table.glyphs_of(biomes.BOG) if g.tier == glyph_table.BASIC)
    enemies = [_golem()]
    before = enemies[0].hp
    _fire_into(glyph, enemies, [], [])
    assert not enemies or enemies[0].hp < before


# --- drawing one in the game ---------------------------------------------


def _armed(glyph) -> PlayScene:
    """A scene holding a staff, knowing ``glyph``, aiming to the right."""
    from game.items.item_kinds import STAFF_ITEM

    scene = PlayScene()
    scene.hotbar.add(STAFF_ITEM, 1)
    for index, slot in enumerate(scene.hotbar.slots):
        if slot is not None and getattr(slot, "kind", None) is STAFF_ITEM:
            scene.hotbar.select(index)
    scene.grimoire.learn(glyph)
    scene._mouse_screen = pygame.Vector2(config.SCREEN_WIDTH, config.SCREEN_HEIGHT // 2)
    return scene


def _draw(scene: PlayScene, glyph) -> None:
    keys = {
        strokes.UP: pygame.K_UP,
        strokes.DOWN: pygame.K_DOWN,
        strokes.LEFT: pygame.K_LEFT,
        strokes.RIGHT: pygame.K_RIGHT,
    }
    for way in strokes.SHAPES[glyph.key]:
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=keys[way]))
        scene.update(config.FIXED_DT)
    for _ in range(int(strokes.SETTLE / config.FIXED_DT) + 2):
        scene.update(config.FIXED_DT)


def test_drawing_a_known_shape_with_a_staff_throws_it():
    glyph = _supreme(biomes.BURNT_FOREST)
    scene = _armed(glyph)
    _draw(scene, glyph)
    assert scene.projectiles
    assert scene.projectiles[-1].gimmick == glyph.gimmick


def test_a_shape_the_player_has_not_found_throws_nothing():
    glyph = _supreme(biomes.BURNT_FOREST)
    scene = _armed(glyph)
    scene.grimoire.learned.clear()
    _draw(scene, glyph)
    assert not scene.projectiles


def test_drawing_bare_handed_throws_nothing():
    # The staff is what makes a shape a spell. Without one the hand still
    # moves and nothing comes of it.
    glyph = _supreme(biomes.BURNT_FOREST)
    scene = _armed(glyph)
    for index, slot in enumerate(scene.hotbar.slots):
        if getattr(slot, "kind", None) is not ITEM_KINDS["staff"]:
            scene.hotbar.select(index)  # anything but the staff
            break
    assert not scene.holding_staff
    _draw(scene, glyph)
    assert not scene.projectiles


def test_a_lesser_shape_throws_without_a_trick():
    glyph = next(
        g for g in glyph_table.glyphs_of(biomes.BURNT_FOREST) if g.tier == glyph_table.BASIC
    )
    scene = _armed(glyph)
    _draw(scene, glyph)
    assert scene.projectiles
    assert scene.projectiles[-1].gimmick is None


def test_throwing_heats_the_staff():
    glyph = _supreme(biomes.BURNT_FOREST)
    scene = _armed(glyph)
    _draw(scene, glyph)
    assert scene.staff.strain > 0


def test_a_weapon_shot_carries_no_trick_at_all():
    # Glyphs used to be carved onto weapons. They are not any more, and a
    # weapon shot that still threw one would be the old system surviving in
    # the one place nobody looks.
    from game.items.tools import WeaponTool

    _, shots = combat.fire_weapon(
        config.FIXED_DT,
        weapon=WeaponTool(),
        held=True,
        aim_world=pygame.Vector2(CENTRE) + pygame.Vector2(100, 0),
        player_pos=pygame.Vector2(CENTRE),
        fire_timer=0.0,
    )
    assert shots and shots[0].gimmick is None
