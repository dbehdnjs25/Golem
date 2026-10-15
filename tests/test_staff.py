import pytest

from game import config
from game.items import engraving, glyphs
from game.items.glyphs import STAFF
from game.items.staff import GREATER_STAFF_SLOTS, Staff
from game.systems.grimoire import Grimoire

EMBER = glyphs.VOLCANO_GLYPHS[0]  # basic: cheap to throw
BLAZE = glyphs.VOLCANO_GLYPHS[1]  # greater
HEART = glyphs.VOLCANO_GLYPHS[2]  # supreme: the dear one
FROST = glyphs.SNOWFIELD_GLYPHS[0]


def _loaded(*carved, slots: int = 3) -> Staff:
    staff = Staff(slots=slots)
    book = Grimoire()
    for glyph in carved:
        book.learn(glyph)
        engraving.engrave(staff.engraved, glyph, book)
    return staff


def test_a_bare_staff_throws_nothing():
    # Not a club. The spec says a staff has no attack of its own and the
    # carving IS the magic, so an empty one has to be useless rather than weak.
    staff = Staff()
    assert staff.ready is None
    assert staff.fire() is None


def test_a_carved_staff_throws_what_is_on_it():
    staff = _loaded(EMBER)
    thrown = staff.fire()
    assert thrown is EMBER


def test_with_two_carved_it_throws_the_chosen_one():
    staff = _loaded(EMBER, FROST)
    staff.choose(1)
    assert staff.fire() is FROST


def test_choosing_past_the_end_is_refused_rather_than_wrapping():
    # Wrapping would silently throw the wrong magic, which in a fight is worse
    # than nothing happening.
    staff = _loaded(EMBER)
    with pytest.raises(IndexError):
        staff.choose(1)


def test_throwing_builds_strain():
    staff = _loaded(EMBER)
    assert staff.strain == 0
    staff.fire()
    assert staff.strain == EMBER.strain


def test_the_dear_cuts_empty_it_fastest():
    # Power and strain climb together, which is what keeps the supreme glyph
    # from being simply the right answer.
    cheap, dear = _loaded(EMBER), _loaded(HEART)
    cheap_shots = _shots_until_overload(cheap)
    dear_shots = _shots_until_overload(dear)
    assert dear_shots < cheap_shots


def _shots_until_overload(staff: Staff) -> int:
    n = 0
    while not staff.overloaded and n < 200:
        if staff.fire() is None:
            break
        n += 1
    return n


def test_an_overloaded_staff_throws_nothing():
    staff = _loaded(HEART)
    while not staff.overloaded:
        staff.fire()
    assert staff.fire() is None


def test_an_overloaded_staff_comes_back_after_its_lockout():
    staff = _loaded(HEART)
    while not staff.overloaded:
        staff.fire()
    staff.update(config.STAFF_LOCKOUT + 0.1)
    assert not staff.overloaded
    assert staff.fire() is HEART


def test_strain_cools_while_it_is_not_being_thrown():
    staff = _loaded(EMBER)
    staff.fire()
    hot = staff.strain
    staff.update(1.0)
    assert staff.strain < hot


def test_strain_never_cools_below_nothing():
    staff = _loaded(EMBER)
    staff.update(60.0)
    assert staff.strain == 0


def test_a_cheap_glyph_can_be_thrown_indefinitely():
    # Something has to be sustainable or the staff is a novelty. The basic cut
    # is that something: weak, but it never puts the staff out of action.
    staff = _loaded(EMBER)
    for _ in range(400):
        staff.fire()
        staff.update(1.0 / config.STAFF_FIRE_RATE)
    assert not staff.overloaded


def test_a_better_staff_has_more_room_on_it():
    # The spec's "slots are raised by upgrading". They come from biome
    # material, never from the ore grade, so the two ladders stay apart.
    assert Staff().slots < GREATER_STAFF_SLOTS


def test_only_staff_glyphs_go_on_a_staff():
    staff = Staff()
    assert staff.engraved.kind == STAFF
    book = Grimoire()
    book.learn(glyphs.LESSER_SWIFT)
    assert engraving.can_engrave(staff.engraved, glyphs.LESSER_SWIFT, book) is not None
