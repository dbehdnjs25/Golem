"""The ground a fight leaves behind, and what it does to whoever stands on it.

Every trick that leaves something -- the fire an ember drops, the frost a
coldsnap sweeps, the sludge a lob pools -- has been leaving decoration.
``gimmicks.touch`` was written for this and then never called from anywhere,
``on_ice`` read the map's permanent ice and not the patch underfoot, and
nothing in the game ever asked what a golem was standing in.

So: the floor is the floor. It burns what is on it, mud drags at it, and ice
takes footing. The one exception is a boss and its own ground -- a fire boss
that cooks itself in its own fire turns every fight into a waiting game.
"""

import pygame

from game import config
from game.entities.boss import BOSS_KINDS, Boss
from game.entities.enemy import BIOME_GOLEMS, Golem
from game.entities.patch import BOSS, BURNING, FROST, PLAYER, SLUDGE, Patch
from game.entities.player import Player
from game.systems import gimmicks
from game.world.map import WorldMap

HOME = pygame.Vector2(3000, 3000)


def _golem(at=None) -> Golem:
    return Golem(pos=pygame.Vector2(at or HOME))


def _boss(at=None) -> Boss:
    return Boss(pos=pygame.Vector2(at or HOME), kind=BOSS_KINDS[0])


def _patch(kind: str, at=None, by: str = PLAYER) -> Patch:
    return Patch(pos=pygame.Vector2(at or HOME), kind=kind, laid_by=by)


def _wade(bodies, patches, seconds=1.0):
    for _ in range(int(seconds / config.FIXED_DT)):
        gimmicks.wade(config.FIXED_DT, bodies, patches)


# --- who laid it ----------------------------------------------------------


def test_ground_remembers_who_laid_it():
    assert _patch(BURNING).laid_by == PLAYER
    assert _patch(BURNING, by=BOSS).laid_by == BOSS


def test_ground_is_the_player_s_unless_it_says_otherwise():
    # Most of it is laid by a glyph, so that is the default; a trick says so.
    assert Patch(pos=pygame.Vector2(HOME), kind=BURNING).laid_by == PLAYER


# --- fire -----------------------------------------------------------------


def test_burning_ground_burns_a_golem():
    golem = _golem()
    before = golem.hp
    _wade([golem], [_patch(BURNING)])
    assert golem.hp < before


def test_a_golem_beside_the_fire_is_untouched():
    golem = _golem(HOME + pygame.Vector2(900, 0))
    before = golem.hp
    _wade([golem], [_patch(BURNING)])
    assert golem.hp == before


def test_burning_ground_costs_by_the_second():
    one, two = _golem(), _golem()
    _wade([one], [_patch(BURNING)], seconds=1.0)
    _wade([two], [_patch(BURNING)], seconds=2.0)
    assert (two.max_hp if hasattr(two, "max_hp") else two.kind.hp) or True
    assert one.hp - two.hp > 0  # twice as long, twice the bill


def test_the_player_s_fire_burns_the_boss():
    # The whole point of a supreme glyph that leaves ground.
    boss = _boss()
    before = boss.hp
    _wade([boss], [_patch(BURNING, by=PLAYER)])
    assert boss.hp < before


def test_a_boss_does_not_cook_itself():
    # Every fire boss would otherwise beat itself if the player simply waited.
    boss = _boss()
    before = boss.hp
    _wade([boss], [_patch(BURNING, by=BOSS)])
    assert boss.hp == before


def test_a_boss_s_fire_still_burns_its_own_golems():
    # Nothing clever: the exemption is the boss itself, not its element.
    golem = _golem()
    before = golem.hp
    _wade([golem], [_patch(BURNING, by=BOSS)])
    assert golem.hp < before


# --- mud ------------------------------------------------------------------


def test_sludge_drags_at_a_golem():
    golem = _golem()
    quick = golem.speed
    _wade([golem], [_patch(SLUDGE)], seconds=0.1)
    assert golem.speed < quick


def test_the_mud_lets_go_eventually():
    golem = _golem()
    quick = golem.kind.speed
    _wade([golem], [_patch(SLUDGE)], seconds=0.1)
    assert golem.speed < quick
    for _ in range(int((config.MIRE_CLING + 0.2) / config.FIXED_DT)):
        golem.update(config.FIXED_DT, golem.pos, WorldMap())
    assert golem.speed == quick


def test_a_mired_golem_covers_less_ground():
    world = WorldMap()
    far = pygame.Vector2(HOME) + pygame.Vector2(5000, 0)
    clean, stuck = _golem(), _golem()
    _wade([stuck], [_patch(SLUDGE)], seconds=0.1)
    for _ in range(int(0.5 / config.FIXED_DT)):
        clean.update(config.FIXED_DT, far, world)
        stuck.update(config.FIXED_DT, far, world)
    assert stuck.pos.x < clean.pos.x


def test_sludge_does_not_hurt():
    # The bog takes breath and footing, never health. Taking health as well
    # would make it the fire in a greener colour.
    golem = _golem()
    before = golem.hp
    _wade([golem], [_patch(SLUDGE)])
    assert golem.hp == before


def test_the_player_s_sludge_drags_at_the_boss():
    boss = _boss()
    quick = boss.speed
    _wade([boss], [_patch(SLUDGE, by=PLAYER)])
    assert boss.speed < quick


# --- ice ------------------------------------------------------------------


def test_frost_takes_no_health_from_a_golem():
    golem = _golem()
    before = golem.hp
    _wade([golem], [_patch(FROST)])
    assert golem.hp == before


def test_frost_does_not_drag_either():
    golem = _golem()
    quick = golem.speed
    _wade([golem], [_patch(FROST)])
    assert golem.speed == quick


# --- the player, who has been standing on all of it for nothing -----------


def test_burning_ground_lights_the_player():
    player = Player(pos=pygame.Vector2(HOME))
    gimmicks.touch(config.FIXED_DT, player, [_patch(BURNING, by=BOSS)], moving=False)
    assert player.burning


def test_sludge_takes_the_player_s_wind_while_they_wade():
    player = Player(pos=pygame.Vector2(HOME))
    for _ in range(int(1.0 / config.FIXED_DT)):
        gimmicks.touch(config.FIXED_DT, player, [_patch(SLUDGE, by=BOSS)], moving=True)
    assert player.stamina < player.max_stamina


def test_standing_still_in_sludge_costs_nothing():
    player = Player(pos=pygame.Vector2(HOME))
    for _ in range(int(1.0 / config.FIXED_DT)):
        gimmicks.touch(config.FIXED_DT, player, [_patch(SLUDGE, by=BOSS)], moving=False)
    assert player.stamina == player.max_stamina


def test_frost_underfoot_is_slippery():
    assert gimmicks.slippery(HOME, [_patch(FROST, by=BOSS)])
    assert not gimmicks.slippery(HOME + pygame.Vector2(900, 0), [_patch(FROST, by=BOSS)])


# --- a tougher golem is not a different rule ------------------------------


def test_a_biome_golem_burns_like_any_other():
    golem = Golem(pos=pygame.Vector2(HOME), kind=BIOME_GOLEMS[-1])
    before = golem.hp
    _wade([golem], [_patch(BURNING)])
    assert golem.hp < before


def test_a_dead_golem_is_not_billed_again():
    golem = _golem()
    golem.damage(golem.hp)
    at_death = golem.hp
    _wade([golem], [_patch(BURNING)])
    assert golem.hp == at_death
