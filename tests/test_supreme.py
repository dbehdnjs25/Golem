"""The player throwing what the boss threw.

This is what the whole step was for: the thing done to you becomes the thing in
your hand. So the two sides have to reach the same function -- written twice it
would be wrong twice, and the wrong one would be whichever got less play.
"""

import inspect

import pygame

from game import config
from game.entities.enemy import Golem
from game.entities.patch import BURNING, FROST, SLUDGE
from game.items import engraving
from game.items import glyphs as glyph_table
from game.items.glyphs import STAFF, WEAPON
from game.items.staff import Staff
from game.items.tools import WeaponTool
from game.systems import combat, gimmicks
from game.world import biomes
from game.world.map import WorldMap

WORLD = WorldMap(rotation=0.0)
CENTRE = WORLD.center


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


def test_every_gimmick_can_be_struck_at_a_point():
    # The boss aims it at the player; the player aims it where the shot landed.
    # Both are a point and a thing standing on it.
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
        # Every one of them does SOMETHING: leaves ground, sets a mark, or
        # moves what it hit. A gimmick that did none would be a dud nobody
        # would notice was broken.
        assert patches or marks or golem.pos != stood, gimmick.key


def test_a_shove_works_on_whatever_is_standing_there():
    # It used to take a Player by name. The player throws it at golems now.
    golem = _golem()
    before = pygame.Vector2(golem.pos)
    gimmicks.shove(golem, pygame.Vector2(CENTRE) + pygame.Vector2(-100, 0))
    assert golem.pos != before


# --- the five supreme glyphs each raise their own trick ------------------


SHOOTER = pygame.Vector2(CENTRE) + pygame.Vector2(-200, 0)


def _fire_into(glyph, enemies, patches, marks):
    """Carve a weapon, fire it, and walk the shot into a golem.

    Through the real path rather than a hand-built Projectile, so that what
    decides whether a trick rides on the shot is the code that decides it in
    the game and not this helper's opinion.
    """
    weapon = WeaponTool()
    engraving.engrave(weapon.engraved, glyph)
    _, shots = combat.fire_weapon(
        config.FIXED_DT,
        weapon=weapon,
        held=True,
        aim_world=pygame.Vector2(enemies[0].pos),
        player_pos=pygame.Vector2(SHOOTER),
        fire_timer=0.0,
    )
    shots[0].pos.update(enemies[0].pos)
    combat.update_projectiles(
        config.FIXED_DT,
        shots,
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
    # Nothing is left on the ground; the golem is somewhere else instead.
    patches, marks = [], []
    golem = _golem()
    before = pygame.Vector2(golem.pos)
    _fire_into(_supreme(biomes.WIND_PLATEAU), [golem], patches, marks)
    assert not patches and not marks
    assert golem.pos != before


def test_it_is_thrown_away_from_the_one_who_fired():
    # Shoved toward the player it would be a pull, and the plateau's holes are
    # on the far side.
    patches, marks = [], []
    golem = _golem()
    _fire_into(_supreme(biomes.WIND_PLATEAU), [golem], patches, marks)
    assert golem.pos.distance_to(SHOOTER) > CENTRE.distance_to(SHOOTER)


# --- the lower cuts are damage and nothing else --------------------------


def test_a_basic_glyph_leaves_nothing_behind():
    # The ladder has to mean something. If the first cut already threw the
    # trick, the boss would be guarding a bigger number.
    for biome in biomes.RING_BIOMES:
        for tier in (glyph_table.BASIC, glyph_table.GREATER):
            glyph = next(g for g in glyph_table.glyphs_of(biome) if g.tier == tier)
            patches, marks, enemies = [], [], [_golem()]
            _fire_into(glyph, enemies, patches, marks)
            assert not patches and not marks, (biome.key, tier)


def test_a_lower_glyph_still_hurts():
    glyph = next(g for g in glyph_table.glyphs_of(biomes.BOG) if g.tier == glyph_table.BASIC)
    enemies = [_golem()]
    before = enemies[0].hp
    _fire_into(glyph, enemies, [], [])
    assert not enemies or enemies[0].hp < before


# --- what the weapon and the staff put on a shot -------------------------


def test_a_weapon_carved_with_a_supreme_glyph_throws_it():
    weapon = WeaponTool()
    glyph = _supreme(biomes.BURNT_FOREST)
    engraving.engrave(weapon.engraved, glyph)
    _, shots = combat.fire_weapon(
        config.FIXED_DT,
        weapon=weapon,
        held=True,
        aim_world=pygame.Vector2(CENTRE) + pygame.Vector2(100, 0),
        player_pos=pygame.Vector2(CENTRE),
        fire_timer=0.0,
    )
    assert shots and shots[0].gimmick == glyph.gimmick


def test_a_weapon_carved_with_a_lesser_glyph_throws_only_damage():
    weapon = WeaponTool()
    engraving.engrave(
        weapon.engraved,
        next(g for g in glyph_table.glyphs_of(biomes.BURNT_FOREST) if g.tier == glyph_table.BASIC),
    )
    _, shots = combat.fire_weapon(
        config.FIXED_DT,
        weapon=weapon,
        held=True,
        aim_world=pygame.Vector2(CENTRE) + pygame.Vector2(100, 0),
        player_pos=pygame.Vector2(CENTRE),
        fire_timer=0.0,
    )
    assert shots and shots[0].gimmick is None


def test_a_staff_throws_the_trick_of_whatever_it_fires():
    staff = Staff(slots=3)
    glyph = _supreme(biomes.WASTELAND)
    engraving.engrave(staff.engraved, glyph)
    _, shots = combat.fire_staff(
        config.FIXED_DT,
        staff=staff,
        held=True,
        aim_world=pygame.Vector2(CENTRE) + pygame.Vector2(100, 0),
        player_pos=pygame.Vector2(CENTRE),
        fire_timer=0.0,
    )
    assert shots and shots[0].gimmick == glyph.gimmick


def test_a_bare_weapon_throws_no_trick():
    _, shots = combat.fire_weapon(
        config.FIXED_DT,
        weapon=WeaponTool(),
        held=True,
        aim_world=pygame.Vector2(CENTRE) + pygame.Vector2(100, 0),
        player_pos=pygame.Vector2(CENTRE),
        fire_timer=0.0,
    )
    assert shots and shots[0].gimmick is None


def test_the_glyph_a_staff_carries_matches_what_it_fits():
    # Both tools take the supreme cuts; nothing here narrows that.
    for biome in biomes.RING_BIOMES:
        glyph = _supreme(biome)
        assert WEAPON in glyph.fits and STAFF in glyph.fits
