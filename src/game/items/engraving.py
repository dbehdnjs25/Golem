"""Carving a glyph onto a thing, and the chisel that pays for it.

Knowing a glyph is free and forever. Carving one costs a chisel, and a chisel
is good for three cuts. That is the whole tension of this step: because the
tool runs out, "is this the right drawing for this weapon" is a question every
time rather than a formality.

``can_engrave`` answers with a REASON rather than a bool. There are four ways
to be refused and the player needs to be told which -- a greyed-out row with no
explanation is the worst version of this screen.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game import config
from game.items.glyphs import Glyph
from game.systems.grimoire import Grimoire


@dataclass
class Engraved:
    """What is carved on one piece of equipment.

    ``slots`` is the piece's own, not the player's: a better staff is a staff
    with more room on it. Slots come from biome material, never from the ore
    grade, so the two ladders stay apart.
    """

    kind: str  # WEAPON or STAFF, from items/glyphs
    slots: int = 1
    glyphs: list[Glyph] = field(default_factory=list)

    @property
    def free(self) -> int:
        return self.slots - len(self.glyphs)

    @property
    def power(self) -> float:
        return sum(g.power for g in self.glyphs)

    def holds(self, glyph: Glyph) -> bool:
        return any(g.key == glyph.key for g in self.glyphs)


def can_engrave(piece: Engraved, glyph: Glyph, grimoire: Grimoire) -> str | None:
    """Why this cut cannot be made, or None if it can.

    Checked in the order the player would ask: do I know it, does it belong on
    this, have I already done it, is there room.
    """
    if not grimoire.knows(glyph):
        return f"{glyph.name}: 아직 모르는 그림"
    if piece.kind not in glyph.fits:
        return f"{glyph.name}: 여기엔 새길 수 없음"
    if piece.holds(glyph):
        return f"{glyph.name}: 이미 새겨져 있음"
    if piece.free <= 0:
        return "빈 칸이 없음"
    return None


def engrave(piece: Engraved, glyph: Glyph, grimoire: Grimoire | None = None) -> None:
    """Cut it in. Raises if it was not allowed.

    The check is repeated here rather than trusted to the caller: ``can_engrave``
    is advice a screen asks for, and a piece quietly overfilled by a careless
    caller would be a bug nobody sees until the damage numbers are wrong.
    """
    if piece.kind not in glyph.fits:
        raise ValueError(f"{glyph.key} does not fit a {piece.kind}")
    if piece.holds(glyph):
        raise ValueError(f"{glyph.key} is already on this piece")
    if piece.free <= 0:
        raise ValueError("no free slot")
    if grimoire is not None and not grimoire.knows(glyph):
        raise ValueError(f"{glyph.key} has not been learned")
    piece.glyphs.append(glyph)


@dataclass
class Chisel:
    """Three cuts and it is gone. The only price carving has."""

    uses_left: int = config.CHISEL_USES

    @property
    def spent(self) -> bool:
        return self.uses_left <= 0

    def use(self) -> None:
        if self.spent:
            raise ValueError("this chisel is worn out")
        self.uses_left -= 1
