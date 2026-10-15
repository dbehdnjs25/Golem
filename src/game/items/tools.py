"""Usable tools.

A gathering tool is a family and a grade: the family decides what it can be
swung at, the grade decides whether the node yields and how fast. Both come
from ``items/grades``, so the ladder is described in one place and the tool
just carries a position on it.

``dps`` and ``name`` are derived rather than stored -- a copper pickaxe is not
a separate thing to configure, it is the base rate times copper's speed.

The weapon is still a single flat thing; grading weapons belongs with combat.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game import config
from game.items.engraving import Engraved
from game.items.glyphs import WEAPON
from game.items.grades import AXE, GRADES, HAND, PICKAXE, TOOL_ITEMS, WOOD_G, Grade
from game.items.item_kinds import ItemKind

_FAMILY_NAMES = {PICKAXE: "곡괭이", AXE: "도끼"}


@dataclass(frozen=True)
class MiningTool:
    family: str = PICKAXE
    grade: Grade = WOOD_G
    range: float = config.MINING_RANGE

    @property
    def dps(self) -> float:
        return config.MINING_DPS * self.grade.speed

    @property
    def name(self) -> str:
        return f"{self.grade.name} {_FAMILY_NAMES[self.family]}"


# An empty hand is a tool too -- the worst one. Only litter answers to it, and
# that is what lets a run with nothing in it begin.
BARE_HAND = MiningTool(family=HAND, grade=GRADES[0])


def pickaxe(grade: Grade) -> MiningTool:
    return MiningTool(family=PICKAXE, grade=grade)


def axe(grade: Grade) -> MiningTool:
    return MiningTool(family=AXE, grade=grade)


@dataclass
class WeaponTool:
    """The weapon, plus whatever has been carved into it.

    Not frozen any more: an engraved weapon carries state, and what is cut
    into this particular one is the whole point of the glyph ladder.

    Its slot count is flat because weapon TYPES are still undecided -- the
    spec lists daggers, spears and bows as open questions. The staff is where
    "more slots by upgrading" actually shows.
    """

    damage: float = config.WEAPON_DAMAGE
    fire_rate: float = config.WEAPON_FIRE_RATE  # shots per second
    projectile_speed: float = config.PROJECTILE_SPEED
    projectile_ttl: float = config.PROJECTILE_TTL
    projectile_radius: float = config.PROJECTILE_RADIUS
    name: str = "Pulse Gun"
    engraved: Engraved = field(
        default_factory=lambda: Engraved(kind=WEAPON, slots=config.WEAPON_SLOTS)
    )

    @property
    def total_damage(self) -> float:
        """What a shot actually lands for. Carved power is added, never scaled:
        a multiplier would make the late glyphs silly and the early ones a
        rounding error."""
        return self.damage + self.engraved.power


def tool_for(kind: ItemKind) -> MiningTool | None:
    """The tool a given item IS, or None if it is just cargo.

    This is the bridge between the catalogue and the hand: the hotbar carries
    items, and a tool is what one of them means. Without it a crafted pickaxe
    would sit in a slot as inert cargo.
    """
    entry = TOOL_ITEMS.get(kind)
    if entry is None:
        return None
    family, grade = entry
    return MiningTool(family=family, grade=grade)
