"""The desert's three, and the two shapes they needed.

Lightning is the only element whose tricks the player BUILDS. An orb takes a
piece of the floor away and holds the charge (번개1); rods are flung to the
edge and stay, one of them joining itself to the far side of the room every
five seconds (번개2); and then one line is threaded through every rod still
standing (번개3). A room kept clear makes the supreme trick a single line to
step off. A room left full is cut into pieces at once.

Two shapes come with it. A ROD, which unlike a pillar is not in the way -- you
walk past it and it kills you from somewhere else -- and a BEAM, the first
hazard that is a line between two places rather than a circle.

And one status: the charge. It takes the dodge away and nothing else, which is
worse than the damage and the reason the answer to an orb is distance.
"""

import random

import pygame

from game import config
from game.entities.hazard import Beam, Rod
from game.entities.player import Player
from game.systems import boss_tricks
from game.world.map import WorldMap

HOME = pygame.Vector2(3000, 3000)
RADIUS = config.TEMPLE_RADIUS


def _player(at=None) -> Player:
    return Player(pos=pygame.Vector2(at or HOME))


def _tick(field, player, seconds, patches=None):
    patches = [] if patches is None else patches
    for _ in range(int(seconds / config.FIXED_DT)):
        boss_tricks.update(config.FIXED_DT, field, player, patches, room=HOME, radius=RADIUS)
    return patches


def _cast(key, boss_at=None, player_at=None, might=1.0):
    field = boss_tricks.Field()
    player = _player(player_at or (HOME + pygame.Vector2(250, 0)))
    boss_tricks.cast(
        key,
        field,
        pygame.Vector2(boss_at or HOME),
        player.pos,
        might=might,
        rng=random.Random(5),
        room=HOME,
        radius=RADIUS,
    )
    return field, player


# --- the charge ----------------------------------------------------------


def test_the_charge_takes_the_dodge_away():
    player = _player()
    player.shock_timer = 1.0
    world = WorldMap()
    player.update(config.FIXED_DT, pygame.Vector2(1, 0), world, dodge_pressed=True)
    assert player.iframe_timer == 0.0  # no i-frames means no dodge happened


def test_the_charge_does_not_charge_you_for_the_dodge_it_refused():
    player = _player()
    player.shock_timer = 1.0
    world = WorldMap()
    player.update(config.FIXED_DT, pygame.Vector2(1, 0), world, dodge_pressed=True)
    assert player.stamina == player.max_stamina


def test_the_charge_wears_off():
    player = _player()
    player.shock_timer = 0.5
    world = WorldMap()
    for _ in range(int(1.0 / config.FIXED_DT)):
        player.update(config.FIXED_DT, pygame.Vector2(0, 0), world)
    assert not player.shocked


def test_the_charge_refreshes_rather_than_stacking():
    from game.systems import status

    player = _player()
    status.charge(player, 2.0)
    status.charge(player, 2.0)
    assert player.shock_timer == 2.0
    status.charge(player, 1.0)
    assert player.shock_timer == 2.0  # a shorter one does not cut a longer short


# --- a rod, and a line between two places --------------------------------


def test_a_rod_is_not_in_the_way():
    # The whole difference from a pillar. You walk past it, and then it kills
    # you from somewhere else.
    field = boss_tricks.Field()
    field.rods.append(Rod(pos=pygame.Vector2(HOME)))
    player = _player(HOME)
    _tick(field, player, 0.2)
    assert player.pos == HOME


def test_a_rod_can_be_broken():
    field = boss_tricks.Field()
    rod = Rod(pos=pygame.Vector2(HOME))
    field.rods.append(rod)
    rod.damage(config.ROD_HP)
    _tick(field, _player(HOME), 0.1)
    assert not field.rods


def test_a_rod_rusts_out_if_ignored():
    field = boss_tricks.Field()
    field.rods.append(Rod(pos=pygame.Vector2(HOME)))
    _tick(field, _player(HOME), config.ROD_SECONDS + 0.5)
    assert not field.rods


def test_a_rod_that_fires_throws_a_line_at_the_far_side():
    field = boss_tricks.Field()
    field.room = pygame.Vector2(HOME)
    field.rods.append(Rod(pos=HOME + pygame.Vector2(300, 0), fires=True, spark=0.1))
    field.rods.append(Rod(pos=HOME - pygame.Vector2(300, 0)))
    _tick(field, _player(HOME + pygame.Vector2(0, 900)), 0.2)
    assert len(field.beams) == 1


def test_a_rod_does_not_join_the_one_next_door():
    # A line between two rods standing side by side crosses nothing.
    field = boss_tricks.Field()
    field.room = pygame.Vector2(HOME)
    field.rods.append(Rod(pos=HOME + pygame.Vector2(300, 0), fires=True, spark=0.1))
    field.rods.append(Rod(pos=HOME + pygame.Vector2(300, 20)))
    _tick(field, _player(HOME), 0.2)
    assert not field.beams


def test_a_rod_that_does_not_fire_stays_quiet():
    field = boss_tricks.Field()
    field.room = pygame.Vector2(HOME)
    field.rods.append(Rod(pos=HOME + pygame.Vector2(300, 0), spark=0.1))
    field.rods.append(Rod(pos=HOME - pygame.Vector2(300, 0), spark=0.1))
    _tick(field, _player(HOME), 0.5)
    assert not field.beams


def test_a_rod_keeps_firing_on_its_own_clock():
    # Counted as they are thrown rather than counted at the end: a line is
    # gone within a second of firing, so a later look would find one at most.
    field = boss_tricks.Field()
    field.room = pygame.Vector2(HOME)
    field.rods.append(Rod(pos=HOME + pygame.Vector2(300, 0), fires=True, spark=0.1))
    field.rods.append(Rod(pos=HOME - pygame.Vector2(300, 0)))
    away = _player(HOME + pygame.Vector2(0, 900))
    thrown = 0
    for _ in range(int((config.ROD_SPARK * 2 + 0.3) / config.FIXED_DT)):
        before = len(field.beams)
        boss_tricks.update(config.FIXED_DT, field, away, [], room=HOME, radius=RADIUS)
        thrown += max(0, len(field.beams) - before)
    assert thrown >= 2


def test_a_beam_warns_before_it_fires():
    field = boss_tricks.Field()
    field.beams.append(Beam(a=pygame.Vector2(HOME), b=HOME + pygame.Vector2(600, 0), damage=20.0))
    player = _player(HOME + pygame.Vector2(300, 0))
    _tick(field, player, config.BEAM_WARNING * 0.5)
    assert player.hp == player.max_hp  # still a thread


def test_a_beam_hurts_whoever_is_on_the_line():
    field = boss_tricks.Field()
    field.beams.append(Beam(a=pygame.Vector2(HOME), b=HOME + pygame.Vector2(600, 0), damage=20.0))
    player = _player(HOME + pygame.Vector2(300, 0))
    _tick(field, player, config.BEAM_WARNING + 0.05)
    assert player.hp < player.max_hp


def test_a_beam_misses_whoever_stepped_off_it():
    field = boss_tricks.Field()
    field.beams.append(Beam(a=pygame.Vector2(HOME), b=HOME + pygame.Vector2(600, 0), damage=20.0))
    player = _player(HOME + pygame.Vector2(300, 200))
    _tick(field, player, config.BEAM_WARNING + 0.05)
    assert player.hp == player.max_hp


def test_a_beam_hits_once_and_goes():
    field = boss_tricks.Field()
    field.beams.append(Beam(a=pygame.Vector2(HOME), b=HOME + pygame.Vector2(600, 0), damage=20.0))
    player = _player(HOME + pygame.Vector2(300, 0))
    _tick(field, player, config.BEAM_WARNING + 0.05)
    once = player.max_hp - player.hp
    _tick(field, player, 1.0)
    assert player.max_hp - player.hp == once
    assert not field.beams


def test_a_beam_does_not_reach_past_its_ends():
    field = boss_tricks.Field()
    field.beams.append(Beam(a=pygame.Vector2(HOME), b=HOME + pygame.Vector2(300, 0), damage=20.0))
    player = _player(HOME + pygame.Vector2(700, 0))  # along the line, but past it
    _tick(field, player, config.BEAM_WARNING + 0.05)
    assert player.hp == player.max_hp


# --- the three -----------------------------------------------------------


def test_the_basic_throws_an_orb_that_stops():
    field, player = _cast("static")
    assert len(field.zones) == 1
    orb = field.zones[0]
    assert orb.vel.length() > 0
    _tick(field, _player(HOME + pygame.Vector2(2000, 0)), config.STATIC_SETTLE + 0.2)
    assert orb.vel.length() == 0


def test_the_basic_takes_a_piece_of_the_floor_for_a_while():
    field, player = _cast("static")
    assert field.zones[0].ttl >= 5.0


def test_standing_beside_the_orb_costs_you():
    field, player = _cast("static", player_at=HOME)
    _tick(field, player, 1.0)
    assert player.hp < player.max_hp


def test_the_orb_holds_the_charge_on_you():
    field, player = _cast("static", player_at=HOME)
    _tick(field, player, 0.2)
    assert player.shocked


def test_keeping_away_from_the_orb_is_the_whole_answer():
    field, player = _cast("static", player_at=HOME + pygame.Vector2(1500, 0))
    _tick(field, player, 0.5)
    assert player.hp == player.max_hp
    assert not player.shocked


def test_the_greater_flings_rods_to_the_edge():
    field, player = _cast("strike")
    assert len(field.rods) == config.STRIKE_RODS + 1
    for rod in field.rods:
        assert HOME.distance_to(rod.pos) > RADIUS * 0.5


def test_the_greater_plants_exactly_one_that_fires():
    field, player = _cast("strike")
    assert len([rod for rod in field.rods if rod.fires]) == 1


def test_the_greater_adds_to_what_is_already_standing():
    # They stay. The floor filling up is the trick, not a single blow.
    field, player = _cast("strike")
    boss_tricks.cast(
        "strike", field, pygame.Vector2(HOME), player.pos, rng=random.Random(9), room=HOME
    )
    assert len(field.rods) == (config.STRIKE_RODS + 1) * 2


def test_the_greater_s_rods_can_all_be_cleared():
    field, player = _cast("strike")
    for rod in list(field.rods):
        rod.damage(config.ROD_HP)
    _tick(field, player, 0.1)
    assert not field.rods


def test_the_supreme_threads_a_line_through_everything_standing():
    field, player = _cast("strike")
    rods = len(field.rods)
    field.beams.clear()
    boss_tricks.cast(
        "thunderheart", field, pygame.Vector2(HOME), player.pos, rng=random.Random(3), room=HOME
    )
    # Boss, every rod, and then the player: one line between each pair.
    assert len(field.beams) == rods + 1


def test_the_supreme_on_a_clean_floor_is_one_line():
    field, player = _cast("thunderheart", player_at=HOME + pygame.Vector2(300, 0))
    assert len(field.beams) == 1


def test_the_supreme_puts_nothing_new_on_the_floor():
    # It spends what is standing. Nothing else.
    field, player = _cast("thunderheart")
    assert not field.rods
    assert not field.falling
    assert not field.zones


def test_the_supreme_still_warns():
    field, player = _cast("thunderheart")
    assert all(beam.left > 0 for beam in field.beams)


def test_clearing_the_rods_is_worth_doing():
    # Standing halfway between two rods is a safe spot on an empty floor and a
    # line on a full one. That is the whole of what the desert asks.
    here = HOME + pygame.Vector2(1, 0).rotate(30) * 380

    def hurt(rods):
        field = boss_tricks.Field()
        field.room = pygame.Vector2(HOME)
        player = _player(here)
        for n in range(rods):
            field.rods.append(Rod(pos=HOME + pygame.Vector2(1, 0).rotate(60 * n) * 440))
        boss_tricks.cast("thunderheart", field, HOME + pygame.Vector2(0, 900), pygame.Vector2(HOME))
        _tick(field, player, config.BEAM_WARNING + 0.1)
        return player.max_hp - player.hp

    assert hurt(6) > 0
    assert hurt(0) == 0


def test_every_desert_trick_is_built():
    from game.entities.boss import BOSS_KINDS

    storm = next(k for k in BOSS_KINDS if k.biome.key == "wasteland")
    for key in storm.tricks:
        field, player = _cast(key)
        assert field.zones or field.rods or field.beams, key


def test_the_second_phase_makes_all_three_hit_harder():
    def hurt(key, might):
        field, player = _cast(key, player_at=HOME, might=might)
        _tick(field, player, 1.2)
        return player.max_hp - player.hp

    # The orb and the threaded line both land on whoever is standing there.
    for key in ("static", "thunderheart"):
        assert hurt(key, 1.6) > hurt(key, 1.0), key

    # Rods are the exception: their damage arrives five seconds later, through
    # a line thrown at the far side of the room rather than at anybody. So
    # what carries the phase is the rod the cast plants.
    hard = _cast("strike", might=1.6)[0].rods
    soft = _cast("strike", might=1.0)[0].rods
    assert max(rod.might for rod in hard) > max(rod.might for rod in soft)


# --- clearing them has to actually be possible ---------------------------


def test_a_shot_can_be_spent_on_a_rod():
    # Two of the fifteen are answered by clearing the floor, which is only an
    # answer if a shot lands on one.
    from game.entities.projectile import Projectile
    from game.systems import combat
    from game.world.map import WorldMap

    world = WorldMap()
    here = pygame.Vector2(world.center)
    rod = Rod(pos=pygame.Vector2(here))
    shots = [Projectile(pos=pygame.Vector2(here), vel=pygame.Vector2(0, 0), damage=10.0)]
    combat.update_projectiles(config.FIXED_DT, shots, [], world, standing=[rod])
    assert rod.hp < config.ROD_HP
    assert not shots  # and the shot was spent on it


def test_a_rod_does_not_eat_a_shot_meant_for_something_alive():
    from game.entities.enemy import GOLEM_KINDS, Golem
    from game.entities.projectile import Projectile
    from game.systems import combat
    from game.world.map import WorldMap

    world = WorldMap()
    here = pygame.Vector2(world.center)
    rod = Rod(pos=pygame.Vector2(here))
    golem = Golem(pos=pygame.Vector2(here), kind=GOLEM_KINDS[0])
    shots = [Projectile(pos=pygame.Vector2(here), vel=pygame.Vector2(0, 0), damage=10.0)]
    combat.update_projectiles(config.FIXED_DT, shots, [golem], world, standing=[rod])
    assert rod.hp == config.ROD_HP  # the golem took it


def test_a_column_can_be_broken_by_a_shot_too():
    from game.entities.hazard import Pillar
    from game.entities.projectile import Projectile
    from game.systems import combat
    from game.world.map import WorldMap

    world = WorldMap()
    here = pygame.Vector2(world.center)
    pillar = Pillar(pos=pygame.Vector2(here))
    shots = [Projectile(pos=pygame.Vector2(here), vel=pygame.Vector2(0, 0), damage=10.0)]
    combat.update_projectiles(config.FIXED_DT, shots, [], world, standing=[pillar])
    assert pillar.hp < config.PILLAR_HP
