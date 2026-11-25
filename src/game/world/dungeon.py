"""The inside of a temple: rooms, the doors between them, and what is in them.

A temple used to be one circle with an altar in it. It is a building now --
thirteen rooms at least, each one a rectangle the size of a screen, joined
into a TREE: branches, and never a way round. That last part is the whole
reason for the shape. With a loop in it a player could walk past a room full
of golems and come at the far side from behind, and "the doors do not open
until the room is clear" would be a suggestion.

Every room is entered from its south side -- the door you came in by -- and
may open north, east or west onto rooms further in. So the tree grows away
from the entrance and the player always knows which way is back.

Pure: generation is seeded arithmetic over a temple's own salt, and the state
is four flags and a count. Nothing here touches a surface, and "is the boss
reachable in fewer than five rooms" is a question a test asks in one line.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from game import config

# Where a door is in the wall of a room. SOUTH is always the way back.
NORTH = "north"
EAST = "east"
WEST = "west"
SOUTH = "south"
ONWARD: tuple[str, ...] = (NORTH, EAST, WEST)

# What a room is for.
START = "start"
PLAIN = "plain"
CHEST = "chest"
BOSS = "boss"


@dataclass
class Room:
    """One rectangle, and everything that is true about it."""

    index: int
    kind: str
    depth: int  # rooms from the entrance; the start room is 0
    back: int | None = None  # the room its south door leads to
    doors: dict[str, int] = field(default_factory=dict)  # onward direction -> room
    golems: int = 0  # how many were placed here when the temple was drawn
    standing: int = 0  # how many are still up
    chest_opened: bool = False
    has_key: bool = False  # whether this room's chest holds the boss door's key
    boss_woken: bool = False

    @property
    def cleared(self) -> bool:
        """Whether anything is still guarding this room."""
        return self.standing <= 0

    @property
    def has_chest(self) -> bool:
        return self.kind is CHEST

    @property
    def is_dead_end(self) -> bool:
        return not self.doors


@dataclass
class Dungeon:
    """A whole temple interior, and where the player is in it."""

    rooms: list[Room]
    at: int = 0  # which room the player is standing in
    key_found: bool = False  # the boss door's key, once a chest has given it up
    key_spent: bool = False  # and once it has been turned

    @property
    def room(self) -> Room:
        return self.rooms[self.at]

    @property
    def boss_room(self) -> Room:
        return next(room for room in self.rooms if room.kind is BOSS)

    @property
    def depth_of_boss(self) -> int:
        return self.boss_room.depth

    # --- doors ------------------------------------------------------------
    def locked(self, way: str) -> str | None:
        """Why this door will not open, or None if it will.

        Two locks, and they read differently on purpose. A room with something
        still standing in it holds every door, including the one back -- that
        is what makes a room a fight rather than a corridor. The boss door
        holds alone, and only until the key is found.
        """
        here = self.room
        if not here.cleared:
            return "골렘이 아직 서 있다"
        target = self.through(way)
        if target is None:
            return None  # no door there at all; the caller simply does not move
        if self.rooms[target].kind is BOSS and not (self.key_found or self.key_spent):
            return "잠겨 있다 · 열쇠가 필요하다"
        return None

    def through(self, way: str) -> int | None:
        """Which room that door leads to, or None if the wall is blank."""
        here = self.room
        if way is SOUTH:
            return here.back
        return here.doors.get(way)

    def walk(self, way: str) -> bool:
        """Go through a door. False if there is none, or it will not open."""
        target = self.through(way)
        if target is None or self.locked(way) is not None:
            return False
        if self.rooms[target].kind is BOSS and self.key_found and not self.key_spent:
            # Turned once and gone. Carrying a spent key around would make the
            # second temple's door a formality.
            self.key_found = False
            self.key_spent = True
        self.at = target
        return True

    @staticmethod
    def opposite(way: str) -> str:
        """The wall a door comes out of on the other side."""
        return {NORTH: SOUTH, SOUTH: NORTH, EAST: WEST, WEST: EAST}[way]

    # --- what the rooms hold ----------------------------------------------
    def open_chest(self) -> bool:
        """Take what this room's chest holds. False if there is nothing to take."""
        here = self.room
        if not here.has_chest or here.chest_opened or not here.cleared:
            return False
        here.chest_opened = True
        if here.has_key:
            self.key_found = True
        return True

    def kill_one(self) -> None:
        """Something in this room went down."""
        here = self.room
        here.standing = max(0, here.standing - 1)

    @property
    def cleared_rooms(self) -> int:
        return sum(1 for room in self.rooms if room.cleared)


# --- drawing one ----------------------------------------------------------


def build(salt: int, rng: random.Random | None = None) -> Dungeon:
    """Lay out one temple's inside, the same way every time for the same salt.

    Grown rather than planned: a spine is walked out from the entrance until
    the boss is far enough in, and then branches are hung off it until there
    are enough rooms. Growing it means the shape is never the same twice and
    never has to be described anywhere; the two things that MUST hold -- the
    boss is deep, and every dead end is worth walking to -- are checked at the
    end rather than hoped for.
    """
    dice = rng or random.Random(salt * config.TEMPLE_SEED_STRIDE + 7)
    rooms = [Room(index=0, kind=START, depth=0)]

    # The spine: a wandering path from the entrance to the boss. Its length is
    # what makes the boss far away, and it wanders because a door that is
    # always north would make every temple the same corridor.
    spine = [0]
    length = dice.randint(config.DUNGEON_BOSS_DEPTH, config.DUNGEON_BOSS_DEPTH + 2)
    for _ in range(length):
        spine.append(_grow(rooms, spine[-1], PLAIN, dice))
    boss = _grow(rooms, spine[-1], BOSS, dice)
    rooms[boss].kind = BOSS

    # Branches, hung off anything with a wall to spare, until the place is big
    # enough. Each one ends in a chest: a dead end nobody has a reason to walk
    # to is just a longer way of being lost.
    while len(rooms) < config.DUNGEON_ROOMS:
        host = _somewhere_with_room(rooms, dice)
        if host is None:
            break
        here = _grow(rooms, host, PLAIN, dice)
        for _ in range(dice.randint(0, config.DUNGEON_BRANCH_EXTRA)):
            if len(rooms) >= config.DUNGEON_ROOMS:
                break
            here = _grow(rooms, here, PLAIN, dice)
        rooms[here].kind = CHEST

    _stock(rooms, dice)
    return Dungeon(rooms=rooms)


def _grow(rooms: list[Room], host: int, kind: str, dice: random.Random) -> int:
    """Put a new room through one of the host's free walls, and return it."""
    free = [way for way in ONWARD if way not in rooms[host].doors]
    way = dice.choice(free)
    made = Room(index=len(rooms), kind=kind, depth=rooms[host].depth + 1, back=host)
    rooms[host].doors[way] = made.index
    rooms.append(made)
    return made.index


def _somewhere_with_room(rooms: list[Room], dice: random.Random) -> int | None:
    """A room with a wall to spare, preferring the ones further in.

    The boss's room is never built onto: it is the end of the place, and a
    door out of it would let a player walk past the fight.
    """
    spare = [
        room.index
        for room in rooms
        if room.kind is not BOSS and len(room.doors) < len(ONWARD) and room.kind is not CHEST
    ]
    if not spare:
        return None
    return dice.choice(spare)


def _stock(rooms: list[Room], dice: random.Random) -> None:
    """Put the golems and the key where they go.

    The start room is left empty. Walking in to find something already swinging
    gives the player no moment to read the room, and the one thing a doorway
    should always be is safe.
    """
    for room in rooms:
        if room.kind is START or room.kind is BOSS:
            room.golems = 0
        elif room.kind is CHEST:
            # Never fewer than three. A chest is the reason to walk down a
            # dead end, so it has to cost more than the room before it.
            room.golems = dice.randint(config.DUNGEON_CHEST_GUARDS, config.DUNGEON_GUARDS_MAX)
        else:
            room.golems = dice.randint(config.DUNGEON_GUARDS_MIN, config.DUNGEON_GUARDS_MAX)
        room.standing = room.golems

    chests = [room for room in rooms if room.kind is CHEST]
    if chests:
        dice.choice(chests).has_key = True
