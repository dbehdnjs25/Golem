"""The five bosses, and the tricks each of them holds.

Three tables and one entity. ``TRICKS`` is the fifteen attribute gimmicks --
three tiers for each of the five elements -- and ``COMMONS`` is the five blows
that have no element at all. ``BOSS_KINDS`` is five rows saying which of those
each boss carries; the row is an ``EnemyKind``, so combat and drawing need no
special case for a boss.

What a trick DOES is not here. These rows are names and tiers; the behaviour
arrives with the gimmick work, and keeping the two apart is what lets the
design settle without the fight being rewritten each time a trick changes.

A boss has TWO phases and the turn is one way. Half health opens the second,
which adds the other two attribute tricks -- never a common. What grows is the
element, so the second phase reads as the same thing hitting harder rather than
a different creature wearing its skin. Three numbers move with it, and one of
them favours the player: it becomes frailer. Without that a phase two is pure
punishment, and the fight gets longer exactly when it got harder.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from game import config
from game.entities.enemy import TARGET_PLAYER, EnemyKind
from game.world.biomes import BOG, BURNT_FOREST, SNOWFIELD, WASTELAND, WIND_PLATEAU, Biome

# --- the five blows with no element --------------------------------------


@dataclass(frozen=True)
class Common:
    key: str
    name: str
    reach: str  # "close" or "thrown" -- whether the arm leaves the body


CHARGE = Common("charge", "돌진", "close")
SLAM = Common("slam", "내려찍기", "close")
SWEEP = Common("sweep", "휘두르기", "close")
LEAP = Common("leap", "도약", "close")
GRAB = Common("grab", "움켜쥐기", "thrown")

COMMONS: dict[str, Common] = {c.key: c for c in (CHARGE, SLAM, SWEEP, LEAP, GRAB)}


# --- the fifteen attribute tricks ----------------------------------------


@dataclass(frozen=True)
class Trick:
    key: str
    name: str
    biome: Biome
    tier: int  # 1 basic, 2 greater, 3 supreme
    asks: str  # what it asks of the player, in a few words


_ROWS: tuple[Trick, ...] = (
    # 불탄 숲 -- fire falls, then walks at you, then bursts out of the floor
    Trick("ember", "불씨", BURNT_FOREST, 1, "떨어지는 자리를 비켜라"),
    Trick("flame", "화염", BURNT_FOREST, 2, "다가오는 벽을 돌아가라"),
    Trick("ashheart", "잿불심", BURNT_FOREST, 3, "내려칠 때 멀리 있어라"),
    # 설원 -- thrown and splitting, swept and freezing, dropped on a mark
    Trick("frost", "서리", SNOWFIELD, 1, "벽에 붙지 마라"),
    Trick("coldsnap", "한파", SNOWFIELD, 2, "부채꼴 밖으로"),
    Trick("absolute", "절대영도", SNOWFIELD, 3, "예고된 자리에서 비켜라"),
    # 바람 고원 -- a growing whirl, the whole floor flowing, rings in sequence
    Trick("breeze", "산들바람", WIND_PLATEAU, 1, "커지기 전에 피해라"),
    Trick("gale", "돌풍", WIND_PLATEAU, 2, "흐름을 거슬러 서라"),
    Trick("stormcore", "폭풍핵", WIND_PLATEAU, 3, "터지는 순서를 읽어라"),
    # 늪지 -- a cone that pools, three lobs, and the floor erupting
    Trick("miasma", "독기", BOG, 1, "붙어라"),
    Trick("venom", "맹독", BOG, 2, "네가 깐 땅을 피해라"),
    Trick("rotheart", "부패심", BOG, 3, "깔아둔 것이 전부 계산서"),
    # 황무지 -- an orb that sits, rods that chain, a bolt that bounces back
    Trick("static", "정전기", WASTELAND, 1, "구슬에서 떨어져라"),
    Trick("strike", "낙뢰", WASTELAND, 2, "이어진 선을 비켜라"),
    Trick("thunderheart", "뇌신핵", WASTELAND, 3, "치운 자리에서 싸워라"),
)

TRICKS: dict[str, Trick] = {t.key: t for t in _ROWS}


# --- the five bosses ------------------------------------------------------


@dataclass(frozen=True)
class BossKind(EnemyKind):
    """One boss. An ``EnemyKind`` row with a biome and its tricks attached."""

    biome: Biome
    tricks: tuple[str, str, str]  # basic, greater, supreme -- in that order
    commons: tuple[str, str]


def _kind(
    key: str,
    name: str,
    biome: Biome,
    hp: float,
    tricks: tuple[str, str, str],
    commons: tuple[str, str],
) -> BossKind:
    return BossKind(
        key=key,
        name=name,
        target=TARGET_PLAYER,  # it never leaves the temple, so the core is unreachable
        hp=hp,
        speed=config.BOSS_SPEED,
        radius=config.BOSS_RADIUS,
        contact_dps=config.BOSS_CONTACT_DPS,
        color=biome.color,
        biome=biome,
        tricks=tricks,
        commons=commons,
    )


# In ring order, which is difficulty order. No two share a pair of commons:
# phase one is one attribute trick and those two blows, so a shared pair would
# make two of the five fights the same fight until half health.
BOSS_KINDS: tuple[BossKind, ...] = (
    _kind(
        "burnt_lord",
        "잿불의 주인",
        BURNT_FOREST,
        config.BOSS_HP[0],
        ("ember", "flame", "ashheart"),
        ("charge", "sweep"),
    ),
    _kind(
        "frost_lord",
        "서리의 주인",
        SNOWFIELD,
        config.BOSS_HP[1],
        ("frost", "coldsnap", "absolute"),
        ("leap", "grab"),
    ),
    _kind(
        "gale_lord",
        "바람의 주인",
        WIND_PLATEAU,
        config.BOSS_HP[2],
        ("breeze", "gale", "stormcore"),
        ("charge", "grab"),
    ),
    _kind(
        "bog_lord",
        "부패의 주인",
        BOG,
        config.BOSS_HP[3],
        ("miasma", "venom", "rotheart"),
        ("grab", "slam"),
    ),
    _kind(
        "storm_lord",
        "뇌신의 주인",
        WASTELAND,
        config.BOSS_HP[4],
        ("static", "strike", "thunderheart"),
        ("leap", "sweep"),
    ),
)


@dataclass
class Boss:
    pos: pygame.Vector2
    kind: BossKind
    hp: float = field(default=0.0)
    turned: bool = False  # once the second phase opens it stays open

    def __post_init__(self) -> None:
        if not self.hp:
            self.hp = self.kind.hp

    # --- the phase --------------------------------------------------------
    def _latch(self) -> None:
        """Open the second phase once health has been down to the mark.

        Latched rather than read from health each time, so a boss that heals --
        by its own trick, or by something not written yet -- cannot hand the
        player the easier fight twice. Set the moment the blow lands, not the
        next time somebody asks, or a hit and a heal in the same step would
        slip past unnoticed.
        """
        if self.hp <= self.kind.hp * config.BOSS_PHASE_AT:
            self.turned = True

    @property
    def phase(self) -> int:
        """1 or 2. Never 3, and never back to 1."""
        self._latch()
        return 2 if self.turned else 1

    @property
    def tricks_now(self) -> tuple[str, ...]:
        """The attribute tricks it is throwing. One, then all three."""
        return self.kind.tricks if self.phase == 2 else self.kind.tricks[:1]

    @property
    def commons_now(self) -> tuple[str, ...]:
        """The two blows. The same two in both phases -- only the element grows."""
        return self.kind.commons

    # --- what the second phase changes -----------------------------------
    @property
    def taken_multiplier(self) -> float:
        return config.BOSS_PHASE2_FRAILTY if self.phase == 2 else 1.0

    @property
    def contact_dps(self) -> float:
        hit = self.kind.contact_dps
        return hit * config.BOSS_PHASE2_MIGHT if self.phase == 2 else hit

    @property
    def speed(self) -> float:
        quick = self.kind.speed
        return quick * config.BOSS_PHASE2_HASTE if self.phase == 2 else quick

    @property
    def radius(self) -> float:
        return self.kind.radius

    @property
    def color(self) -> tuple[int, int, int]:
        return self.kind.color

    @property
    def is_dead(self) -> bool:
        return self.hp <= 0

    def damage(self, amount: float) -> None:
        self.hp -= amount * self.taken_multiplier
        self._latch()

    def update(
        self,
        dt: float,
        target: pygame.Vector2,
        room: pygame.Vector2,
        room_radius: float,
    ) -> None:
        """Walk at the player, and never past the room's wall.

        Loose on the map it would wander out into the ring, and the temple
        would stop being the place the fight happens.
        """
        toward = target - self.pos
        if toward.length_squared() > 0:
            self.pos += toward.normalize() * self.speed * dt
        offset = self.pos - room
        reach = room_radius - self.radius
        if offset.length() > reach:
            self.pos.update(room + offset.normalize() * reach)
