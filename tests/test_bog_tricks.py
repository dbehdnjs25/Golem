"""The bog's three, and the shape they needed.

Poison is the first element whose tricks are about the FLOOR rather than about
the moment. A cone pools at its far end (독1), three lobs come down around you
and pool where they land (독2), and then every pool on the floor goes off at
once (독3) -- so the supreme trick's strength is the history of the fight
rather than a number in the table.

The new shape is the lob: something thrown at a PLACE instead of in a
direction. A ball is a line to step off; a lob is a circle to not be standing
in, and the arc is its own warning.
"""

import random

import pygame

from game import config
from game.entities.hazard import Lob
from game.entities.patch import BURNING, SLUDGE, Patch
from game.entities.player import Player
from game.systems import boss_tricks

HOME = pygame.Vector2(3000, 3000)
RADIUS = config.TEMPLE_RADIUS


def _player(at=None) -> Player:
    return Player(pos=pygame.Vector2(at or HOME))


def _tick(field, player, seconds, patches=None):
    patches = [] if patches is None else patches
    for _ in range(int(seconds / config.FIXED_DT)):
        boss_tricks.update(config.FIXED_DT, field, player, patches, room=HOME, radius=RADIUS)
    return patches


def _cast(key, boss_at=None, player_at=None, might=1.0, patches=None):
    field = boss_tricks.Field()
    player = _player(player_at or (HOME + pygame.Vector2(250, 0)))
    boss_tricks.cast(
        key,
        field,
        pygame.Vector2(boss_at or HOME),
        player.pos,
        might=might,
        rng=random.Random(5),
        patches=patches,
        room=HOME,
        radius=RADIUS,
    )
    return field, player


def _sludge(at, radius=config.PATCH_RADIUS) -> Patch:
    return Patch(pos=pygame.Vector2(at), kind=SLUDGE, radius=radius)


# --- something thrown at a place -----------------------------------------


def test_a_lob_arrives_where_it_was_aimed():
    field = boss_tricks.Field()
    mark = HOME + pygame.Vector2(300, 0)
    field.lobs.append(Lob(start=pygame.Vector2(HOME), to=pygame.Vector2(mark)))
    _tick(field, _player(HOME - pygame.Vector2(900, 0)), config.LOB_SECONDS + 0.1)
    assert not field.lobs  # it landed rather than carrying on


def test_a_lob_is_in_the_air_on_the_way():
    field = boss_tricks.Field()
    lob = Lob(start=pygame.Vector2(HOME), to=HOME + pygame.Vector2(300, 0))
    field.lobs.append(lob)
    _tick(field, _player(HOME - pygame.Vector2(900, 0)), config.LOB_SECONDS / 2)
    assert HOME.x < lob.pos.x < HOME.x + 300
    assert lob.height > 0  # drawn off the ground, which is what reads as a throw


def test_a_lob_hurts_whoever_is_standing_where_it_comes_down():
    field = boss_tricks.Field()
    mark = HOME + pygame.Vector2(300, 0)
    field.lobs.append(Lob(start=pygame.Vector2(HOME), to=pygame.Vector2(mark), damage=12.0))
    player = _player(mark)
    _tick(field, player, config.LOB_SECONDS + 0.1)
    assert player.hp < player.max_hp


def test_a_lob_does_not_hurt_on_the_way_past():
    # The arc is the warning; walking under one has to be free, or the warning
    # would be a lie.
    field = boss_tricks.Field()
    field.lobs.append(
        Lob(start=pygame.Vector2(HOME), to=HOME + pygame.Vector2(600, 0), damage=12.0)
    )
    player = _player(HOME + pygame.Vector2(300, 0))
    _tick(field, player, config.LOB_SECONDS * 0.6)
    assert player.hp == player.max_hp


def test_a_lob_leaves_what_it_was_carrying():
    field = boss_tricks.Field()
    field.lobs.append(
        Lob(start=pygame.Vector2(HOME), to=HOME + pygame.Vector2(200, 0), leaves=SLUDGE)
    )
    patches = _tick(field, _player(HOME), config.LOB_SECONDS + 0.1)
    assert [p.kind for p in patches] == [SLUDGE]


# --- the three -----------------------------------------------------------


def test_the_basic_sprays_a_cone_in_front():
    field, player = _cast("miasma")
    assert len(field.falling) == config.MIASMA_PUFFS
    aways = [HOME.distance_to(spot.pos) for spot in field.falling]
    assert aways == sorted(aways)  # graded along the range, not a heap


def test_the_basic_widens_as_it_goes():
    field, player = _cast("miasma")
    widths = [spot.radius for spot in field.falling]
    assert widths == sorted(widths)
    assert widths[-1] > widths[0]


def test_the_basic_leaves_the_boss_s_own_feet_clear():
    # The one trick answered by getting CLOSER, which only works if nothing
    # comes out underfoot.
    field, player = _cast("miasma")
    nearest = min(HOME.distance_to(spot.pos) - spot.radius for spot in field.falling)
    assert nearest > 0


def test_standing_close_to_the_basic_is_safe():
    field, player = _cast("miasma", player_at=HOME + pygame.Vector2(60, 0))
    _tick(field, player, 0.2)
    assert player.hp == player.max_hp


def test_backing_away_from_the_basic_is_not():
    field = boss_tricks.Field()
    aim = HOME + pygame.Vector2(config.MIASMA_RANGE * 0.85, 0)
    player = _player(aim)
    boss_tricks.cast("miasma", field, pygame.Vector2(HOME), aim, rng=random.Random(1))
    _tick(field, player, 0.2)
    assert player.hp < player.max_hp


def test_the_basic_pools_only_at_the_far_end():
    field, player = _cast("miasma")
    leaving = [spot for spot in field.falling if spot.leaves == SLUDGE]
    staying = [spot for spot in field.falling if spot.leaves is None]
    assert leaving and staying
    assert min(HOME.distance_to(s.pos) for s in leaving) > max(
        HOME.distance_to(s.pos) for s in staying
    )


def test_the_greater_throws_three():
    field, player = _cast("venom")
    assert len(field.lobs) == config.VENOM_LOBS


def test_one_of_the_three_comes_down_on_the_spot():
    # Standing still must never be the free answer.
    field, player = _cast("venom")
    assert any(lob.to.distance_to(player.pos) < 1 for lob in field.lobs)


def test_the_greater_leaves_a_pool_under_each():
    field, player = _cast("venom", player_at=HOME)
    patches = _tick(field, player, config.LOB_SECONDS + 0.2)
    assert len([p for p in patches if p.kind is SLUDGE]) == config.VENOM_LOBS


def test_the_supreme_sends_off_every_pool_on_the_floor():
    ground = [_sludge(HOME + pygame.Vector2(x, 0)) for x in (0, 200, 400)]
    field, player = _cast("rotheart", player_at=HOME + pygame.Vector2(900, 0), patches=ground)
    # One per pool, and one more underfoot so a clean floor still asks
    # something of the player.
    assert len(field.falling) == len(ground) + 1


def test_the_supreme_only_counts_poison():
    ground = [_sludge(HOME), Patch(pos=pygame.Vector2(HOME), kind=BURNING)]
    field, player = _cast("rotheart", patches=ground)
    assert len(field.falling) == 2  # the one pool, and the one underfoot


def test_the_supreme_bursts_where_the_pools_are():
    ground = [_sludge(HOME + pygame.Vector2(400, 0))]
    field, player = _cast("rotheart", player_at=HOME, patches=ground)
    assert any(spot.pos.distance_to(ground[0].pos) < 1 for spot in field.falling)


def test_standing_in_a_pool_when_the_supreme_lands_hurts():
    ground = [_sludge(HOME)]
    field = boss_tricks.Field()
    player = _player(HOME)
    boss_tricks.cast("rotheart", field, HOME + pygame.Vector2(600, 0), player.pos, patches=ground)
    _tick(field, player, config.ROTHEART_WARNING + 0.1, patches=ground)
    assert player.hp < player.max_hp


def test_a_clean_floor_makes_the_supreme_nearly_nothing():
    dirty = _cast(
        "rotheart",
        player_at=HOME,
        patches=[_sludge(HOME + pygame.Vector2(x, 0)) for x in (0, 90, 180, 270)],
    )
    clean = _cast("rotheart", player_at=HOME, patches=[])
    assert len(dirty[0].falling) > len(clean[0].falling)


def test_the_supreme_still_announces_itself():
    field, player = _cast("rotheart", patches=[_sludge(HOME)])
    assert all(spot.left > 0 for spot in field.falling)


def test_every_bog_trick_is_built():
    from game.entities.boss import BOSS_KINDS

    bog = next(k for k in BOSS_KINDS if k.biome.key == "bog")
    for key in bog.tricks:
        field, player = _cast(key, patches=[_sludge(HOME)])
        assert field.falling or field.lobs, key


def test_the_second_phase_makes_all_three_hit_harder():
    def hurt(key, might):
        ground = [_sludge(HOME)]
        where = HOME + pygame.Vector2(config.MIASMA_RANGE * 0.8, 0) if key == "miasma" else HOME
        field = boss_tricks.Field()
        player = _player(where)
        boss_tricks.cast(
            key,
            field,
            pygame.Vector2(HOME),
            player.pos,
            might=might,
            rng=random.Random(5),
            patches=ground,
            room=HOME,
            radius=RADIUS,
        )
        _tick(field, player, 2.0, patches=ground)
        return player.max_hp - player.hp

    for key in ("miasma", "venom", "rotheart"):
        assert hurt(key, 1.6) > hurt(key, 1.0), key
