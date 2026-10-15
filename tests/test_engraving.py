import pytest

from game import config
from game.items import engraving, glyphs
from game.items.engraving import Engraved
from game.items.glyphs import LESSER_SWIFT, STAFF, WEAPON
from game.systems.grimoire import Grimoire
from game.world import biomes

FIRE = glyphs.BURNT_GLYPHS[0]
BLAZE = glyphs.BURNT_GLYPHS[1]
FROST = glyphs.SNOWFIELD_GLYPHS[0]


def _knowing(*learned) -> Grimoire:
    book = Grimoire()
    for glyph in learned:
        book.learn(glyph)
    return book


# --- the grimoire ---------------------------------------------------------


def test_learning_is_permanent_and_free():
    book = Grimoire()
    assert not book.knows(FIRE)
    assert book.learn(FIRE) is True
    assert book.knows(FIRE)


def test_learning_the_same_glyph_twice_says_so():
    # Structures hand out what they hold; two ruins holding the same drawing
    # must not read as two finds.
    book = _knowing(FIRE)
    assert book.learn(FIRE) is False


def test_the_book_lists_in_catalogue_order():
    book = _knowing(FROST, FIRE)
    assert list(book.known()) == [g for g in glyphs.GLYPHS if g in (FIRE, FROST)]


def test_the_book_can_be_asked_per_biome():
    book = _knowing(FIRE, FROST)
    assert book.known(biomes.BURNT_FOREST) == (FIRE,)
    assert book.known(biomes.SNOWFIELD) == (FROST,)
    assert book.known(biomes.BOG) == ()


# --- what is carved on a thing --------------------------------------------


def test_a_fresh_piece_is_blank():
    piece = Engraved(kind=WEAPON, slots=2)
    assert piece.glyphs == []
    assert piece.free == 2
    assert piece.power == 0


def test_carving_fills_a_slot_and_adds_its_power():
    piece = Engraved(kind=WEAPON, slots=2)
    engraving.engrave(piece, FIRE)
    assert piece.glyphs == [FIRE]
    assert piece.free == 1
    assert piece.power == FIRE.power


def test_power_is_the_sum_of_what_is_on_it():
    piece = Engraved(kind=WEAPON, slots=3)
    engraving.engrave(piece, FIRE)
    engraving.engrave(piece, LESSER_SWIFT)
    assert piece.power == FIRE.power + LESSER_SWIFT.power


# --- the four ways it can be refused --------------------------------------


def test_a_glyph_you_have_not_learned_cannot_be_carved():
    why = engraving.can_engrave(Engraved(kind=WEAPON, slots=2), FIRE, Grimoire())
    assert why is not None and "모르" in why


def test_a_full_piece_refuses():
    piece = Engraved(kind=WEAPON, slots=1)
    engraving.engrave(piece, FIRE)
    why = engraving.can_engrave(piece, FROST, _knowing(FIRE, FROST))
    assert why is not None and "칸" in why


def test_a_glyph_that_does_not_fit_the_piece_refuses():
    # Swift is a weapon's business. A staff is only what is carved on it, and
    # "faster" is not something it can throw.
    why = engraving.can_engrave(Engraved(kind=STAFF, slots=2), LESSER_SWIFT, _knowing(LESSER_SWIFT))
    assert why is not None and "새길 수 없" in why


def test_the_same_glyph_twice_on_one_piece_refuses():
    piece = Engraved(kind=WEAPON, slots=3)
    engraving.engrave(piece, FIRE)
    why = engraving.can_engrave(piece, FIRE, _knowing(FIRE))
    assert why is not None and "이미" in why


def test_a_legal_carving_gives_no_reason():
    assert engraving.can_engrave(Engraved(kind=WEAPON, slots=1), FIRE, _knowing(FIRE)) is None


def test_engraving_refuses_the_illegal_rather_than_doing_it_anyway():
    # can_engrave is advice; engrave has to enforce, or a bad caller silently
    # overfills a piece.
    piece = Engraved(kind=WEAPON, slots=1)
    engraving.engrave(piece, FIRE)
    with pytest.raises(ValueError):
        engraving.engrave(piece, FROST)


# --- the chisel -----------------------------------------------------------


def test_a_chisel_wears_out_after_three():
    chisel = engraving.Chisel()
    assert chisel.uses_left == config.CHISEL_USES
    for _ in range(config.CHISEL_USES):
        assert not chisel.spent
        chisel.use()
    assert chisel.spent


def test_a_spent_chisel_refuses_to_be_used_again():
    chisel = engraving.Chisel(uses_left=0)
    with pytest.raises(ValueError):
        chisel.use()


def test_the_chisel_is_the_whole_cost_of_carving():
    # Learning is free and forever; this is where the decision lives. Three
    # uses is what makes "is this the right glyph for this weapon" a question
    # rather than a formality.
    assert config.CHISEL_USES == 3
