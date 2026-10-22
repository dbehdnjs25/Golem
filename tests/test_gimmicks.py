import pygame
import pytest

from game import config
from game.entities.patch import BURNING, FROST, SLUDGE, Patch
from game.entities.player import Player
from game.systems import gimmicks
from game.world.map import WorldMap

WORLD = WorldMap()
HOME = WORLD.center


def _player(at: pygame.Vector2 | None = None) -> Player:
    return Player(pos=pygame.Vector2(at if at is not None else HOME))


# --- what the five are ----------------------------------------------------


def test_there_is_one_gimmick_per_ring_biome():
    from game.world import biomes

    assert len(gimmicks.GIMMICKS) == len(biomes.RING_BIOMES)
    for biome in biomes.RING_BIOMES:
        assert gimmicks.of(biome) is not None


def test_no_two_do_the_same_thing():
    # The spec's whole reason for five elements. Colour-swapped damage would
    # make four of them spare.
    assert len({g.effect for g in gimmicks.GIMMICKS}) == len(gimmicks.GIMMICKS)


def test_a_biome_that_has_none_says_so():
    from game.world import biomes

    assert gimmicks.of(biomes.GRASSLAND) is None


# --- fire: the ground it crosses keeps burning -----------------------------


def test_scorching_leaves_something_behind():
    patches: list[Patch] = []
    gimmicks.scorch(HOME, patches)
    assert [p.kind for p in patches] == [BURNING]


def test_standing_on_scorched_ground_sets_you_alight():
    patches: list[Patch] = []
    gimmicks.scorch(HOME, patches)
    player = _player()
    gimmicks.touch(0.1, player, patches, moving=False)
    assert player.burning


def test_scorched_ground_goes_out_on_its_own():
    # A trail that never cooled would wall the arena off by the end of a fight.
    patches: list[Patch] = []
    gimmicks.scorch(HOME, patches)
    gimmicks.update_patches(config.PATCH_SECONDS + 1.0, patches)
    assert patches == []


# --- ice: it freezes the ground under you ----------------------------------


def test_freezing_puts_ice_where_you_are_standing():
    patches: list[Patch] = []
    gimmicks.freeze(HOME, patches)
    assert [p.kind for p in patches] == [FROST]


def test_frozen_ground_is_slippery():
    patches: list[Patch] = []
    gimmicks.freeze(HOME, patches)
    assert gimmicks.slippery(HOME, patches)
    assert not gimmicks.slippery(HOME + pygame.Vector2(5_000, 0), patches)


def test_frozen_ground_does_no_damage_at_all():
    # It takes footing, not health. Doing both would make it the fire with a
    # different colour.
    patches: list[Patch] = []
    gimmicks.freeze(HOME, patches)
    player = _player()
    gimmicks.touch(1.0, player, patches, moving=True)
    assert player.hp == config.PLAYER_MAX_HP
    assert not player.burning


# --- wind: it shoves ------------------------------------------------------


def test_a_shove_moves_you_away_from_whatever_threw_it():
    player = _player(HOME + pygame.Vector2(100, 0))
    gimmicks.shove(player, HOME)
    assert player.pos.x > HOME.x + 100


def test_a_shove_from_on_top_of_you_still_picks_a_direction():
    player = _player()
    gimmicks.shove(player, pygame.Vector2(HOME))
    assert player.pos != HOME


def test_a_shove_cannot_throw_you_off_the_map():
    player = _player(HOME + pygame.Vector2(WORLD.radius - 10, 0))
    gimmicks.shove(player, HOME, world=WORLD)
    assert WORLD.contains(player.pos)


def test_a_shove_does_no_damage_by_itself():
    # It is dangerous because of what you land in, which is why the plateau
    # has holes in it.
    player = _player()
    gimmicks.shove(player, HOME + pygame.Vector2(50, 0))
    assert player.hp == config.PLAYER_MAX_HP


# --- poison: it leaves mires ----------------------------------------------


def test_fouling_leaves_a_mire():
    patches: list[Patch] = []
    gimmicks.foul(HOME, patches)
    assert [p.kind for p in patches] == [SLUDGE]


def test_a_left_mire_takes_breath_from_someone_moving():
    patches: list[Patch] = []
    gimmicks.foul(HOME, patches)
    player = _player()
    gimmicks.touch(1.0, player, patches, moving=True)
    assert player.stamina < player.max_stamina


def test_a_left_mire_takes_nothing_from_someone_standing_still():
    patches: list[Patch] = []
    gimmicks.foul(HOME, patches)
    player = _player()
    gimmicks.touch(1.0, player, patches, moving=False)
    assert player.stamina == player.max_stamina


def test_it_works_outside_the_bog():
    # The boss carries this, it is not the biome's. Fought anywhere, it would
    # still leave mud.
    patches: list[Patch] = []
    spot = HOME + pygame.Vector2(100, 0)
    gimmicks.foul(spot, patches)
    assert gimmicks.sludgy(spot, patches)


# --- lightning: marks, and arcs between them -------------------------------


def test_marking_puts_a_mark_down():
    marks: list[pygame.Vector2] = []
    gimmicks.mark(HOME, marks)
    assert len(marks) == 1


def test_one_mark_alone_does_nothing():
    # It is the arc BETWEEN marks that hurts, which is what makes spreading
    # out the answer -- and the wasteland the place with nowhere to spread to.
    marks = [pygame.Vector2(HOME)]
    player = _player()
    gimmicks.arc(1.0, player, marks)
    assert player.hp == config.PLAYER_MAX_HP


def test_standing_between_two_marks_is_struck():
    marks = [HOME + pygame.Vector2(-200, 0), HOME + pygame.Vector2(200, 0)]
    player = _player()
    gimmicks.arc(1.0, player, marks)
    assert player.hp < config.PLAYER_MAX_HP


def test_standing_well_off_the_line_is_not():
    marks = [HOME + pygame.Vector2(-200, 0), HOME + pygame.Vector2(200, 0)]
    player = _player(HOME + pygame.Vector2(0, 2_000))
    gimmicks.arc(1.0, player, marks)
    assert player.hp == config.PLAYER_MAX_HP


def test_more_marks_make_more_lines_to_be_caught_by():
    def hurt(marks) -> float:
        player = _player()
        gimmicks.arc(1.0, player, marks)
        return config.PLAYER_MAX_HP - player.hp

    # The third has to sit where its own two lines also cross the player --
    # marks far off to one side add lines that miss, and a line that misses
    # is exactly what spreading out is for.
    two = [HOME + pygame.Vector2(-200, 0), HOME + pygame.Vector2(200, 0)]
    three = [*two, HOME + pygame.Vector2(0, -30)]
    assert hurt(three) > hurt(two)


def test_a_mark_set_well_aside_adds_lines_that_miss():
    def hurt(marks) -> float:
        player = _player()
        gimmicks.arc(1.0, player, marks)
        return config.PLAYER_MAX_HP - player.hp

    two = [HOME + pygame.Vector2(-200, 0), HOME + pygame.Vector2(200, 0)]
    aside = [*two, HOME + pygame.Vector2(0, -4_000)]
    assert hurt(aside) == hurt(two)


# --- none of them is an execution -----------------------------------------


@pytest.mark.parametrize("gimmick", list(gimmicks.GIMMICKS))
def test_no_gimmick_kills_outright_from_full_health(gimmick):
    patches: list[Patch] = []
    marks: list[pygame.Vector2] = []
    player = _player()
    gimmick.apply(player, HOME, patches, marks)
    gimmicks.touch(1.0, player, patches, moving=True)
    gimmicks.arc(1.0, player, marks)
    assert player.hp > 0
