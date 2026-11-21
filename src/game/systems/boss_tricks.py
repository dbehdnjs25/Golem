"""The attribute tricks: casting them, and running what they put on the floor.

``cast`` turns a trick's name into hazards. ``update`` moves them and works out
who is standing in the way. The names come from ``entities/boss.TRICKS``, which
is where the design lives. All fifteen are built; reaching for a name that is
not one is quiet rather than a crash, because the design table is edited far
more often than this is, and a boss must not take the game down over it.

The one rule that shapes all of it: every trick announces itself. The circle
before the blow, the wall slower than a walk, the ring you can be inside of.
None of them is damage for being in the room, which the contact damage already
is, and none of them kills outright.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from game import config
from game.entities.hazard import Ball, Beam, Falling, Lob, Pillar, Ring, Rod, Wall, Zone
from game.entities.patch import BOSS, BURNING, FROST, SLUDGE, Patch
from game.entities.player import Player
from game.systems import status


@dataclass
class Casting:
    """A trick that lays itself down a beat at a time.

    Kept here rather than on the boss because what matters to each beat is
    where the player is NOW -- the whole point of a channel is that it
    follows -- and this is the thing that gets told that every frame.
    """

    beat: str  # which maker to call each time
    left: int
    every: float
    might: float = 1.0
    timer: float = 0.0


class Field:
    """Everything a boss has put on the floor. One per fight."""

    def __init__(self) -> None:
        self.falling: list[Falling] = []
        self.walls: list[Wall] = []
        self.rings: list[Ring] = []
        self.balls: list[Ball] = []
        self.pillars: list[Pillar] = []
        self.zones: list[Zone] = []
        self.lobs: list[Lob] = []
        self.rods: list[Rod] = []
        self.beams: list[Beam] = []
        self.casting: list[Casting] = []
        # Where the fight is happening. On the field rather than handed to
        # every call, because by the plateau and the desert it is not one
        # trick that wants it: a ball breaks on the wall, wind fills the
        # whole floor, and a rod is thrown AT the edge.
        self.room: pygame.Vector2 | None = None
        self.radius: float = config.TEMPLE_RADIUS

    def clear(self) -> None:
        self.falling.clear()
        self.walls.clear()
        self.rings.clear()
        self.balls.clear()
        self.pillars.clear()
        self.zones.clear()
        self.lobs.clear()
        self.rods.clear()
        self.beams.clear()
        self.casting.clear()

    @property
    def busy(self) -> bool:
        return bool(
            self.falling
            or self.walls
            or self.rings
            or self.balls
            or self.pillars
            or self.zones
            or self.lobs
            or self.rods
            or self.beams
            or self.casting
        )


def _hurt(player: Player, amount: float) -> None:
    if amount and not player.invulnerable and player.hp > 0:
        player.hp -= amount


def _leave(
    kind: str | None,
    at: pygame.Vector2,
    patches: list[Patch],
    radius: float = config.PATCH_RADIUS,
) -> None:
    """Put ground down, the size of whatever put it there.

    The size matters more than it sounds. Taking the global patch radius
    meant a trick could leave fire wider than the circle it announced, and
    then stepping correctly out of the warning still burned you.
    """
    if kind is not None:
        patches.append(Patch(pos=pygame.Vector2(at), kind=kind, radius=radius, laid_by=BOSS))


# --- running what is on the floor -----------------------------------------


def update(
    dt: float,
    field: Field,
    player: Player,
    patches: list[Patch],
    room: pygame.Vector2 | None = None,
    radius: float = config.TEMPLE_RADIUS,
) -> None:
    """Advance every hazard and settle what it does.

    The room is wanted because a thrown ball breaks on its wall and wind
    fills a floor. Given here it is remembered on the field, so a trick cast
    later in the same step knows the shape of the place it is thrown into.
    Left out, a ball simply flies until its own clock runs down, which is what
    happens anywhere there is no room to speak of.
    """
    if room is not None:
        field.room = pygame.Vector2(room)
        field.radius = radius
    _update_casting(dt, field, player)
    _update_falling(dt, field, player, patches)
    _update_walls(dt, field, player)
    _update_rings(dt, field, player, patches)
    _update_balls(dt, field, player, field.room, field.radius)
    _update_pillars(dt, field, player)
    _update_zones(dt, field, player)
    _update_lobs(dt, field, player, patches)
    _update_rods(dt, field)
    _update_beams(dt, field, player)


def _update_casting(dt: float, field: Field, player: Player) -> None:
    """Lay down the next beat of anything still casting."""
    for cast_in_progress in list(field.casting):
        cast_in_progress.timer -= dt
        if cast_in_progress.timer > 0:
            continue
        _BEATS[cast_in_progress.beat](field, player.pos, cast_in_progress.might)
        cast_in_progress.left -= 1
        cast_in_progress.timer = cast_in_progress.every
        if cast_in_progress.left <= 0:
            field.casting.remove(cast_in_progress)


def _update_falling(dt: float, field: Field, player: Player, patches: list[Patch]) -> None:
    landed: list[Falling] = []
    for spot in field.falling:
        spot.left -= dt
        if spot.left <= 0:
            landed.append(spot)
    for spot in landed:
        if spot.pos.distance_to(player.pos) <= spot.radius + player.radius:
            _hurt(player, spot.damage)
        _leave(spot.leaves, spot.pos, patches, spot.radius)
        if spot.stands:
            # A column, not just a blow. It is the only thing in the game that
            # is in the way, which is the whole of what the trick asks.
            field.pillars.append(Pillar(pos=pygame.Vector2(spot.pos)))
        field.falling.remove(spot)


def _update_walls(dt: float, field: Field, player: Player) -> None:
    for wall in list(field.walls):
        wall.pos += wall.vel * dt
        wall.ttl -= dt
        if not wall.spent and _within_wall(player.pos, wall, player.radius):
            _hurt(player, wall.damage)
            wall.spent = True  # once, not sixty times a second
        if wall.ttl <= 0:
            field.walls.remove(wall)


def _within_wall(point: pygame.Vector2, wall: Wall, pad: float) -> bool:
    """A front is a rectangle: wide across its travel, thin along it."""
    facing = wall.vel.normalize() if wall.vel.length_squared() else pygame.Vector2(1, 0)
    offset = point - wall.pos
    along = abs(offset.dot(facing))
    across = abs(offset.dot(pygame.Vector2(-facing.y, facing.x)))
    return along <= wall.reach + pad and across <= wall.width / 2 + pad


def _update_rings(dt: float, field: Field, player: Player, patches: list[Patch]) -> None:
    for ring in list(field.rings):
        before = ring.radius
        ring.radius += ring.speed * dt
        gap = ring.pos.distance_to(player.pos)
        if not ring.caught and before - player.radius <= gap <= ring.radius + player.radius:
            _hurt(player, ring.damage)
            ring.caught = True
        if ring.leaves is not None:
            _scatter_behind(ring, before, patches)
        if ring.radius >= ring.reach:
            field.rings.remove(ring)


def _scatter_behind(ring: Ring, before: float, patches: list[Patch]) -> None:
    """Drop what the ring leaves, spaced out along the way rather than every
    frame -- otherwise one ring would carpet the room."""
    step = ring.reach / max(1, config.ASHHEART_EMBERS)
    if math.floor(ring.radius / step) == math.floor(before / step):
        return
    angle = (len(ring.dropped) * 137.5) % 360  # spread apart, not in a line
    at = ring.pos + pygame.Vector2(1, 0).rotate(angle) * ring.radius
    ring.dropped.append(at)
    _leave(ring.leaves, at, patches, config.RING_EMBER_RADIUS)


def _update_balls(
    dt: float,
    field: Field,
    player: Player,
    room: pygame.Vector2 | None,
    radius: float,
) -> None:
    """Fly, hit once, and break apart on the wall."""
    for ball in list(field.balls):
        ball.pos += ball.vel * dt
        ball.ttl -= dt
        if not ball.spent and ball.pos.distance_to(player.pos) <= ball.radius + player.radius:
            _hurt(player, ball.damage)
            ball.spent = True
        at_wall = room is not None and room.distance_to(ball.pos) >= radius - ball.radius
        if at_wall and ball.splits:
            _shatter(field, ball)
            field.balls.remove(ball)
            continue
        if ball.ttl <= 0 or (at_wall and not ball.splits):
            field.balls.remove(ball)


def _shatter(field: Field, ball: Ball) -> None:
    """Break one ball into shards, fanned evenly.

    Evenly rather than at random: the player is meant to read where the pieces
    are going from where it struck, and a scatter cannot be read.
    """
    speed = ball.vel.length() or config.FROST_SPEED
    for n in range(ball.splits):
        way = pygame.Vector2(1, 0).rotate(360 * n / ball.splits)
        field.balls.append(
            Ball(
                pos=pygame.Vector2(ball.pos),
                vel=way * speed * 0.8,
                damage=ball.damage,
                splits=0,  # a shard does not break again
            )
        )


def _update_pillars(dt: float, field: Field, player: Player) -> None:
    """Melt them down, clear the broken ones, and keep bodies out of them."""
    for pillar in list(field.pillars):
        pillar.left -= dt
        if pillar.left <= 0 or pillar.is_broken:
            field.pillars.remove(pillar)
            continue
        gap = pillar.pos.distance_to(player.pos)
        reach = pillar.radius + player.radius
        if gap < reach:
            # Pushed out rather than stopped at the edge: a player who was
            # already inside when it landed has to end up somewhere.
            offset = player.pos - pillar.pos
            if offset.length_squared() == 0:
                offset = pygame.Vector2(1, 0)
            player.pos.update(pillar.pos + offset.normalize() * reach)


def _update_zones(dt: float, field: Field, player: Player) -> None:
    """Fly, settle, open out, and bill per second for standing in it."""
    for zone in list(field.zones):
        if zone.settle > 0:
            # Only the flight it has left, so a step longer than the flight
            # does not carry it past where it was meant to stop.
            flew = min(dt, zone.settle)
            zone.settle -= flew
            zone.pos += zone.vel * flew
            if zone.settle <= 0:
                zone.vel.update(0, 0)
        zone.radius += zone.grow * dt
        zone.ttl -= dt
        if zone.pos.distance_to(player.pos) <= zone.radius + player.radius:
            # Per second, not per entry. A brush past should be cheap and
            # standing in it should not, and that is the whole difference
            # between a place and a blow.
            _hurt(player, zone.dps * dt)
            if zone.shock:
                status.charge(player, zone.shock)
            _shove(dt, zone, player, field)
        if zone.ttl <= 0:
            field.zones.remove(zone)


def _shove(dt: float, zone: Zone, player: Player, field: Field) -> None:
    """Drag a body toward the middle of a whirl, or push it downwind.

    Both are kept under the player own speed. Wind that cannot be walked
    against is not a current, it is a cage -- and the trick asks the player to
    lean into it, which is only a choice while leaning works.
    """
    push = pygame.Vector2(zone.drift)
    if zone.pull:
        toward = zone.pos - player.pos
        if toward.length_squared() > 0:
            push += toward.normalize() * zone.pull
    if push.length_squared() == 0:
        return
    moved = player.pos + push * dt
    if field.room is not None:
        edge = field.radius - player.radius
        offset = moved - field.room
        if offset.length_squared() > edge * edge:
            # Pinned against the wall, not pushed through it.
            moved = field.room + offset.normalize() * edge
    player.pos.update(moved)


def _update_lobs(dt: float, field: Field, player: Player, patches: list[Patch]) -> None:
    """Carry it along its arc, and settle what is standing where it comes down."""
    for lob in list(field.lobs):
        lob.gone += dt
        lob.pos.update(lob.start.lerp(lob.to, lob.share))
        if not lob.landed:
            continue
        if lob.pos.distance_to(player.pos) <= lob.radius + player.radius:
            _hurt(player, lob.damage)
        _leave(lob.leaves, lob.pos, patches, lob.radius)
        field.lobs.remove(lob)


def _update_rods(dt: float, field: Field) -> None:
    """Rust them out, clear the broken, and let the live ones throw a line."""
    for rod in list(field.rods):
        rod.left -= dt
        if rod.left <= 0 or rod.is_broken:
            field.rods.remove(rod)
    for rod in field.rods:
        if not rod.fires:
            continue
        rod.spark -= dt
        if rod.spark > 0:
            continue
        rod.spark = config.ROD_SPARK
        partner = _across_from(rod, field)
        if partner is not None:
            field.beams.append(
                Beam(
                    a=pygame.Vector2(rod.pos),
                    b=pygame.Vector2(partner.pos),
                    damage=config.STRIKE_DAMAGE * rod.might,
                )
            )


def _across_from(rod: Rod, field: Field) -> Rod | None:
    """The rod furthest round the room from this one, or none standing far enough.

    Not the one next door, on purpose. A line between two rods standing side
    by side crosses nothing and asks nothing; a line to the far side of the
    room cuts the floor in half, which is the trick.
    """
    middle = field.room if field.room is not None else rod.pos
    mine = rod.pos - middle
    best: Rod | None = None
    widest = -1.0
    for other in field.rods:
        if other is rod:
            continue
        theirs = other.pos - middle
        if mine.length_squared() and theirs.length_squared():
            apart = abs(mine.angle_to(theirs))
            apart = min(apart, 360 - apart)
        else:
            apart = 180.0
        if apart < config.STRIKE_APART or apart <= widest:
            continue
        best, widest = other, apart
    return best


def _update_beams(dt: float, field: Field, player: Player) -> None:
    """Hold the thread, fire once, then fade."""
    for beam in list(field.beams):
        if beam.left > 0:
            beam.left -= dt
            continue
        if not beam.spent:
            if _on_beam(player.pos, beam, player.radius):
                _hurt(player, beam.damage)
            beam.spent = True
        beam.ttl -= dt
        if beam.ttl <= 0:
            field.beams.remove(beam)


def _on_beam(point: pygame.Vector2, beam: Beam, pad: float) -> bool:
    """Whether a body is on the line, treating it as a thick segment."""
    span = beam.b - beam.a
    length = span.length()
    if length == 0:
        return point.distance_to(beam.a) <= beam.width / 2 + pad
    along = max(0.0, min(1.0, (point - beam.a).dot(span) / (length * length)))
    nearest = beam.a + span * along
    return point.distance_to(nearest) <= beam.width / 2 + pad


# --- casting ---------------------------------------------------------------


def cast(
    key: str,
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float = 1.0,
    rng: random.Random | None = None,
    patches: list[Patch] | None = None,
    room: pygame.Vector2 | None = None,
    radius: float | None = None,
) -> float:
    """Throw the trick ``key``, and say how long the boss is busy with it.

    Zero for the instant ones. The number has to come from the trick rather
    than be guessed where it is called: only the trick knows whether it is a
    throw or a channel.

    The patch list is handed over because one trick spends what is already on
    the floor rather than putting something new on it, and the room because
    two of them are thrown at the edge rather than at anybody. Both are
    remembered on the field, so a fight only has to say where it is once.
    """
    if room is not None:
        field.room = pygame.Vector2(room)
    if radius is not None:
        field.radius = radius
    maker = _CASTS.get(key)
    if maker is None:
        return 0.0
    return maker(
        field,
        pygame.Vector2(boss_pos),
        pygame.Vector2(target),
        might,
        rng or random.Random(),
        patches if patches is not None else [],
    )


def _ember_beat(field: Field, at: pygame.Vector2, might: float) -> None:
    """One circle, around wherever the player is standing right now.

    Sometimes directly on them, and that is deliberate: the warning is long
    enough to walk out of, so a circle underfoot is a reason to move rather
    than a hit. Kept always to one side, standing perfectly still would be the
    safest thing to do, which is the opposite of what this asks.
    """
    angle = _SPIN.uniform(0, 360)
    reach = _SPIN.uniform(0, config.EMBER_SPREAD)
    field.falling.append(
        Falling(
            pos=at + pygame.Vector2(1, 0).rotate(angle) * reach,
            damage=config.EMBER_DAMAGE * might,
            leaves=BURNING,
        )
    )


def _ember(
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float,
    rng: random.Random,
    patches: list[Patch],
) -> float:
    """Shot into the sky, coming down one at a time around whoever moved.

    The boss holds still for the whole of it -- a channel it could walk out of
    would be a free hit rather than a commitment -- and each circle appears
    beside the player as its turn comes, so standing still collects all five.
    Walking away IS the answer to this one.
    """
    _ember_beat(field, target, might)  # the first lands with the cast
    field.casting.append(
        Casting(
            beat="ember",
            left=config.EMBER_DROPS - 1,
            every=config.EMBER_INTERVAL,
            might=might,
            timer=config.EMBER_INTERVAL,
        )
    )
    return config.EMBER_INTERVAL * (config.EMBER_DROPS - 1)


def _flame(
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float,
    rng: random.Random,
    patches: list[Patch],
) -> float:
    """One front, walking at where you were. Slower than you are."""
    toward = target - boss_pos
    facing = toward.normalize() if toward.length_squared() else pygame.Vector2(1, 0)
    field.walls.append(
        Wall(
            pos=pygame.Vector2(boss_pos),
            vel=facing * config.FLAME_SPEED,
            damage=config.FLAME_DAMAGE * might,
        )
    )
    return 0.0  # thrown and forgotten; the wall lives on its own


def _ashheart(
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float,
    rng: random.Random,
    patches: list[Patch],
) -> float:
    """The floor struck, and fire opening out of it in every direction."""
    field.rings.append(
        Ring(
            pos=pygame.Vector2(boss_pos),
            damage=config.ASHHEART_DAMAGE * might,
            leaves=BURNING,
        )
    )
    return 0.0  # one strike; the ring opens out by itself


def _frost(
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float,
    rng: random.Random,
    patches: list[Patch],
) -> float:
    """One ball, thrown at where you were. It breaks on whatever it meets."""
    toward = target - boss_pos
    facing = toward.normalize() if toward.length_squared() else pygame.Vector2(1, 0)
    field.balls.append(
        Ball(
            pos=pygame.Vector2(boss_pos),
            vel=facing * config.FROST_SPEED,
            damage=config.FROST_DAMAGE * might,
            splits=config.FROST_SPLITS,
        )
    )
    return 0.0


def _coldsnap(
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float,
    rng: random.Random,
    patches: list[Patch],
) -> float:
    """A fan of frost, and the floor left slick where it passed.

    Resolved at once rather than swept across frames: it is an arm's length,
    and a wedge that takes a second to travel is a wall, not a swing. What
    lasts is the ground.
    """
    toward = target - boss_pos
    facing = toward.normalize() if toward.length_squared() else pygame.Vector2(1, 0)
    half = config.COLDSNAP_ARC / 2
    for n in range(config.COLDSNAP_SHEETS):
        share = n / max(1, config.COLDSNAP_SHEETS - 1)
        way = facing.rotate(-half + config.COLDSNAP_ARC * share)
        field.falling.append(
            Falling(
                pos=boss_pos + way * config.COLDSNAP_RANGE * 0.55,
                damage=config.COLDSNAP_DAMAGE * might,
                radius=config.COLDSNAP_RANGE * 0.45,
                left=0.0,  # the swing is already happening; nothing to warn of
                leaves=FROST,
            )
        )
    return 0.0


def _absolute(
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float,
    rng: random.Random,
    patches: list[Patch],
) -> float:
    """Columns announced around you, which then stand where they fell."""
    for n in range(config.ABSOLUTE_PILLARS):
        angle = rng.uniform(0, 360) + 360 * n / config.ABSOLUTE_PILLARS
        reach = rng.uniform(config.ABSOLUTE_SPREAD * 0.3, config.ABSOLUTE_SPREAD)
        field.falling.append(
            Falling(
                pos=target + pygame.Vector2(1, 0).rotate(angle) * reach,
                damage=config.ABSOLUTE_DAMAGE * might,
                radius=config.PILLAR_RADIUS,
                stands=True,
            )
        )
    return 0.0


# --- the wind plateau's three ---------------------------------------------


def _breeze(
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float,
    rng: random.Random,
    patches: list[Patch],
) -> float:
    """A whirl where you were, small at first, and then not.

    The only trick that is safe to ignore for a moment and wrong to ignore
    for two. It pulls rather than hits, which is why it is the basic one:
    on its own it is a nuisance, and under anything else it is what puts you
    where the other thing lands.
    """
    field.zones.append(
        Zone(
            pos=pygame.Vector2(target),
            radius=config.BREEZE_RADIUS,
            dps=config.BREEZE_DPS * might,
            grow=config.BREEZE_GROW,
            pull=config.BREEZE_PULL,
            ttl=config.BREEZE_SECONDS,
        )
    )
    return 0.0


def _gale(
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float,
    rng: random.Random,
    patches: list[Patch],
) -> float:
    """The whole floor flowing, away from the boss.

    Not aimed at anybody -- there is nowhere in the room it is not. What it
    takes away is the free step, and it does not hold the boss still: the
    point of the current is what the boss does to you while you are leaning
    into it.
    """
    toward = target - boss_pos
    facing = toward.normalize() if toward.length_squared() else pygame.Vector2(1, 0)
    field.zones.append(
        Zone(
            pos=pygame.Vector2(field.room if field.room is not None else boss_pos),
            radius=field.radius,
            dps=config.GALE_DPS * might,
            drift=facing * config.GALE_DRIFT,
            ttl=config.GALE_SECONDS,
        )
    )
    return 0.0


def _stormcore(
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float,
    rng: random.Random,
    patches: list[Patch],
) -> float:
    """Circles around the boss, bursting one after another the whole way round.

    Every one of them is announced at the same moment and they go off in
    order, so the floor is not a puzzle of where but of when. Reading the
    rotation gives you a gap that is always there; standing still does not.
    """
    start = rng.uniform(0, 360)
    turn = 1 if rng.random() < 0.5 else -1  # it does not always go the same way
    for n in range(config.STORMCORE_BURSTS):
        angle = start + turn * 360 * n / config.STORMCORE_BURSTS
        field.falling.append(
            Falling(
                pos=boss_pos + pygame.Vector2(1, 0).rotate(angle) * config.STORMCORE_SPREAD,
                damage=config.STORMCORE_DAMAGE * might,
                left=config.FALL_WARNING + n * config.STORMCORE_STEP,
            )
        )
    return (config.STORMCORE_BURSTS - 1) * config.STORMCORE_STEP


# --- the bog's three ------------------------------------------------------


def _miasma(
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float,
    rng: random.Random,
    patches: list[Patch],
) -> float:
    """A cone of breath, widening as it goes, pooling at the far end.

    The one trick in the game that is answered by getting CLOSER. Nothing
    comes out underfoot, so the mistake is backing away -- which is what
    every other trick has been teaching, and the point of this one.
    """
    toward = target - boss_pos
    facing = toward.normalize() if toward.length_squared() else pygame.Vector2(1, 0)
    half = math.tan(math.radians(config.MIASMA_ARC / 2))
    for n in range(config.MIASMA_PUFFS):
        share = config.MIASMA_NEAR + (1 - config.MIASMA_NEAR) * (n + 1) / config.MIASMA_PUFFS
        reach = config.MIASMA_RANGE * share
        wide = reach * half * 0.55
        field.falling.append(
            Falling(
                pos=boss_pos + facing * reach,
                damage=config.MIASMA_DAMAGE * might,
                radius=wide,
                left=0.0,  # the breath is already out; the wind-up was the warning
                # Only the far half pools. Sludge all the way back to the
                # boss's feet would undo the whole shape of it.
                leaves=SLUDGE if n >= config.MIASMA_PUFFS // 2 else None,
            )
        )
    return 0.0


def _venom(
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float,
    rng: random.Random,
    patches: list[Patch],
) -> float:
    """Three lobbed over, coming down around you, each leaving a pool.

    Thrown at places rather than in directions: the arcs are the warning,
    and all three are in the air at once, so the answer is picking where to
    be rather than stepping off a line. What is left behind is the bill the
    supreme trick collects.
    """
    start = rng.uniform(0, 360)
    for n in range(config.VENOM_LOBS):
        angle = start + 360 * n / config.VENOM_LOBS
        # One of the three comes down on the spot itself, so standing where
        # you are is never the free answer.
        reach = 0.0 if n == 0 else config.VENOM_SPREAD
        field.lobs.append(
            Lob(
                start=pygame.Vector2(boss_pos),
                to=target + pygame.Vector2(1, 0).rotate(angle) * reach,
                damage=config.VENOM_DAMAGE * might,
                leaves=SLUDGE,
            )
        )
    return 0.0


def _rotheart(
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float,
    rng: random.Random,
    patches: list[Patch],
) -> float:
    """Every pool already on the floor goes off at once, and one more besides.

    The only trick whose strength is the history of the fight: a player who
    has been dancing through the sludge all fight has built this one. The
    extra circle underfoot is so that a clean floor still asks something --
    otherwise the supreme trick could be nothing at all.
    """
    for pool in patches:
        if pool.kind != SLUDGE:
            continue
        field.falling.append(
            Falling(
                pos=pygame.Vector2(pool.pos),
                damage=config.ROTHEART_DAMAGE * might,
                radius=pool.radius,
                left=config.ROTHEART_WARNING,
            )
        )
    field.falling.append(
        Falling(
            pos=pygame.Vector2(target),
            damage=config.ROTHEART_DAMAGE * might,
            left=config.ROTHEART_WARNING,
        )
    )
    return config.ROTHEART_WARNING


# --- the desert's three ---------------------------------------------------


def _static(
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float,
    rng: random.Random,
    patches: list[Patch],
) -> float:
    """An orb thrown out, which stops and sits there humming.

    It does not chase and it does not expire quickly: it takes a piece of the
    floor away for six seconds. Standing beside it costs health per second and
    the charge, and the charge takes the dodge -- which is far worse than the
    damage, and the reason the answer is simply distance.
    """
    toward = target - boss_pos
    facing = toward.normalize() if toward.length_squared() else pygame.Vector2(1, 0)
    field.zones.append(
        Zone(
            pos=pygame.Vector2(boss_pos),
            radius=config.STATIC_RADIUS,
            vel=facing * config.STATIC_SPEED,
            settle=config.STATIC_SETTLE,
            dps=config.STATIC_DPS * might,
            ttl=config.STATIC_SECONDS,
            shock=config.STATIC_SHOCK,
        )
    )
    return 0.0


def _strike(
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float,
    rng: random.Random,
    patches: list[Patch],
) -> float:
    """Rods flung out to the edge, and one among them that throws lines.

    They stay. Every cast adds four more to whatever is already standing, and
    the one that fires joins itself to the far side of the room every five
    seconds -- so the floor slowly fills with lines rather than with a single
    blow to dodge. All of them can be broken, and the player who never breaks
    one has built the supreme trick's weapon for it.
    """
    middle = field.room if field.room is not None else boss_pos
    reach = field.radius * config.STRIKE_REACH
    for n in range(config.STRIKE_RODS + 1):
        angle = rng.uniform(0, 360)
        field.rods.append(
            Rod(
                pos=middle + pygame.Vector2(1, 0).rotate(angle) * reach,
                might=might,
                # The last one is the starter: exactly one per cast throws
                # lines, so the lines grow with the fight and not with luck.
                fires=n == config.STRIKE_RODS,
            )
        )
    return 0.0


def _thunderheart(
    field: Field,
    boss_pos: pygame.Vector2,
    target: pygame.Vector2,
    might: float,
    rng: random.Random,
    patches: list[Patch],
) -> float:
    """One line threaded through every rod on the floor, and then through you.

    Nothing new is put down: it spends what is standing. A room that has been
    kept clear gives a single line from the boss to wherever you are, which is
    one step to the side. A room left full is cut into pieces at once, and
    there is no stepping out of all of them.
    """
    middle = field.room if field.room is not None else boss_pos
    standing = sorted(
        field.rods,
        key=lambda rod: (
            pygame.Vector2(1, 0).angle_to(rod.pos - middle)
            if (rod.pos - middle).length_squared()
            else 0.0
        ),
    )
    chain = [pygame.Vector2(boss_pos), *(pygame.Vector2(rod.pos) for rod in standing)]
    chain.append(pygame.Vector2(target))
    for here, there in zip(chain, chain[1:], strict=False):
        field.beams.append(Beam(a=here, b=there, damage=config.THUNDERHEART_DAMAGE * might))
    return config.BEAM_WARNING


# One generator for every beat of every channel. The casts take an injected
# one, but a beat happens frames later with nobody holding the dice.
_SPIN = random.Random()

_BEATS = {
    "ember": _ember_beat,
}

# Every trick in the design table is built. A key that is not in here at all
# makes ``cast`` do nothing and hold nobody, so a boss given a name the design
# has and this does not simply skips that beat.
_CASTS = {
    "ember": _ember,
    "flame": _flame,
    "ashheart": _ashheart,
    "frost": _frost,
    "coldsnap": _coldsnap,
    "absolute": _absolute,
    "breeze": _breeze,
    "gale": _gale,
    "stormcore": _stormcore,
    "miasma": _miasma,
    "venom": _venom,
    "rotheart": _rotheart,
    "static": _static,
    "strike": _strike,
    "thunderheart": _thunderheart,
}
