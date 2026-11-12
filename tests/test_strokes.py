"""Glyphs as shapes drawn with the arrow keys.

The shape IS the spell. Nothing is carved and nothing is selected: the player
draws ㄱ and fire comes out, because they know that ㄱ means fire. What grows
over a run is the number of shapes they have found and whether their hand
remembers them.

Two rules give the table its order, and both are for the player's memory rather
than the code's convenience: the FIRST stroke says which element it is, and the
LENGTH says which rung. A supreme glyph taking four strokes is the fight asking
for something, not a number being larger.
"""

import pygame

from game.items import glyphs as glyph_table
from game.items import strokes
from game.systems.drawing import Drawing
from game.world import biomes

D, U, L, R = strokes.DOWN, strokes.UP, strokes.LEFT, strokes.RIGHT


# --- the table ------------------------------------------------------------


def test_every_glyph_has_a_shape():
    for glyph in glyph_table.GLYPHS:
        assert glyph.key in strokes.SHAPES, glyph.key


def test_no_two_glyphs_share_a_shape():
    drawn = list(strokes.SHAPES.values())
    assert len(set(drawn)) == len(drawn)


def test_the_length_of_a_shape_is_its_rung():
    # Three strokes for a basic, four for a greater, five for a supreme.
    # The ladder is in the hand rather than in a number.
    wanted = {glyph_table.BASIC: 3, glyph_table.GREATER: 4, glyph_table.SUPREME: 5}
    for glyph in glyph_table.GLYPHS:
        assert len(strokes.SHAPES[glyph.key]) == wanted[glyph.tier], glyph.key


def test_no_shape_merely_alternates():
    # Two directions traded back and forth is a shape the hand picks up
    # without the player ever having looked at it.
    for key, shape in strokes.SHAPES.items():
        assert len(set(shape)) > 2, key


def test_an_element_always_starts_the_same_way():
    # So that learning one rung teaches the beginning of the next two.
    for biome in biomes.RING_BIOMES:
        opens = {strokes.SHAPES[g.key][0] for g in glyph_table.glyphs_of(biome)}
        assert len(opens) == 1, biome.key


def test_no_shape_doubles_back_on_itself():
    # Two of the same in a row is a longer line, not a corner, and the player
    # cannot see the difference.
    for key, shape in strokes.SHAPES.items():
        assert all(a != b for a, b in zip(shape, shape[1:], strict=False)), key


def test_a_shape_is_only_the_four_directions():
    for shape in strokes.SHAPES.values():
        assert set(shape) <= {U, D, L, R}


# --- reading one back -----------------------------------------------------


def test_a_drawn_shape_finds_its_glyph():
    for glyph in glyph_table.GLYPHS:
        assert strokes.glyph_for(strokes.SHAPES[glyph.key]) is glyph


def test_a_shape_nobody_wrote_finds_nothing():
    assert strokes.glyph_for((U, U, U, U)) is None
    assert strokes.glyph_for(()) is None


# --- drawing one ----------------------------------------------------------


def _draw(drawing: Drawing, *marks: str) -> None:
    for mark in marks:
        drawing.stroke(mark)


def test_strokes_pile_up_as_they_are_pressed():
    drawing = Drawing()
    _draw(drawing, R, D)
    assert drawing.drawn == (R, D)


def test_the_same_direction_twice_is_one_stroke():
    # Holding a key or tapping it twice is a longer line, not a second corner.
    drawing = Drawing()
    _draw(drawing, R, R, R, D)
    assert drawing.drawn == (R, D)


def test_a_pause_finishes_what_was_drawn():
    drawing = Drawing()
    _draw(drawing, *strokes.SHAPES["burnt_forest_basic"])
    assert drawing.update(strokes.SETTLE * 0.5) is None  # still going
    assert drawing.update(strokes.SETTLE) is not None


def test_what_a_pause_hands_back_is_the_glyph():
    ember = next(g for g in glyph_table.glyphs_of(biomes.BURNT_FOREST) if g.tier == "basic")
    drawing = Drawing()
    _draw(drawing, *strokes.SHAPES[ember.key])
    assert drawing.update(strokes.SETTLE) is ember


def test_the_slate_is_wiped_after_it_settles():
    drawing = Drawing()
    _draw(drawing, R, D)
    drawing.update(strokes.SETTLE)
    assert drawing.drawn == ()


def test_a_shape_nobody_knows_settles_into_nothing():
    drawing = Drawing()
    _draw(drawing, U, D)  # doubles back; no such shape
    assert drawing.update(strokes.SETTLE) is None
    assert drawing.drawn == ()


def test_a_long_shape_survives_being_drawn_slowly():
    # Resolving the instant a prefix matched would make the four-stroke shapes
    # unreachable: every one of them opens with a shape that already means
    # something.
    ash = next(g for g in glyph_table.glyphs_of(biomes.BURNT_FOREST) if g.tier == "supreme")
    drawing = Drawing()
    for mark in strokes.SHAPES[ash.key]:
        drawing.stroke(mark)
        assert drawing.update(strokes.SETTLE * 0.6) is None
    assert drawing.update(strokes.SETTLE) is ash


def test_drawing_nothing_settles_nothing():
    drawing = Drawing()
    assert drawing.update(strokes.SETTLE * 10) is None


def test_a_shape_can_be_given_up_on():
    drawing = Drawing()
    _draw(drawing, R, D)
    drawing.clear()
    assert drawing.drawn == ()


# --- the opening of a shape is the start of the longer ones --------------


def test_every_rung_opens_the_next_one():
    for biome in biomes.RING_BIOMES:
        rungs = sorted(glyph_table.glyphs_of(biome), key=lambda g: len(strokes.SHAPES[g.key]))
        for short, long in zip(rungs, rungs[1:], strict=False):
            opening = strokes.SHAPES[long.key][: len(strokes.SHAPES[short.key])]
            assert opening == strokes.SHAPES[short.key], (short.key, long.key)


def test_arrow_keys_are_what_the_four_directions_mean():
    assert strokes.of_key(pygame.K_UP) == U
    assert strokes.of_key(pygame.K_DOWN) == D
    assert strokes.of_key(pygame.K_LEFT) == L
    assert strokes.of_key(pygame.K_RIGHT) == R
    assert strokes.of_key(pygame.K_a) is None
