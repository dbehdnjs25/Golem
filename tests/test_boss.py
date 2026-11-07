"""The five bosses: their table, their two phases, and the arm they throw.

What the tricks DO is not here -- that is the fifteen attribute gimmicks and
the five commons, and they land in their own task. This is the skeleton: how
much a boss has, which tricks it holds, when the second phase opens, and the
one common whose shape changes the fight whether or not it connects.
"""

import pygame

from game import config
from game.entities.boss import BOSS_KINDS, COMMONS, TRICKS, Boss
from game.entities.enemy import TARGET_PLAYER, EnemyKind
from game.systems import boss_fight
from game.world import biomes

CENTRE = pygame.Vector2(2000, 2000)


def _boss(index: int = 0) -> Boss:
    return Boss(pos=pygame.Vector2(CENTRE), kind=BOSS_KINDS[index])


def _hurt_into_phase_two(boss: Boss) -> None:
    boss.damage(boss.kind.hp * (1 - config.BOSS_PHASE_AT) + 1)


# --- the table ------------------------------------------------------------


def test_there_is_one_boss_for_each_ring_biome():
    assert len(BOSS_KINDS) == len(biomes.RING_BIOMES)
    assert [k.biome for k in BOSS_KINDS] == list(biomes.RING_BIOMES)


def test_a_boss_row_is_an_enemy_row():
    # Same shape as a golem's, so combat and drawing need no special case.
    for kind in BOSS_KINDS:
        assert isinstance(kind, EnemyKind)


def test_a_boss_comes_after_the_player_not_the_core():
    # It never leaves its temple, so a core it cannot reach would leave it
    # standing still while someone shot it from across the room.
    for kind in BOSS_KINDS:
        assert kind.target == TARGET_PLAYER


def test_health_climbs_with_the_ring_order():
    # The ring is in difficulty order and a boss is the gate at the end of its
    # biome; a later one that died faster would invert the whole ladder.
    health = [kind.hp for kind in BOSS_KINDS]
    assert health == sorted(health)
    assert len(set(health)) == len(health)


def test_every_boss_holds_three_tricks_of_its_own_element():
    for kind in BOSS_KINDS:
        assert len(kind.tricks) == 3
        for key in kind.tricks:
            assert TRICKS[key].biome is kind.biome


def test_the_three_run_basic_greater_supreme():
    for kind in BOSS_KINDS:
        assert [TRICKS[key].tier for key in kind.tricks] == [1, 2, 3]


def test_the_fifteen_tricks_are_all_spoken_for():
    assert len(TRICKS) == 15
    held = {key for kind in BOSS_KINDS for key in kind.tricks}
    assert held == set(TRICKS)


def test_every_boss_holds_two_commons():
    for kind in BOSS_KINDS:
        assert len(kind.commons) == 2
        assert len(set(kind.commons)) == 2  # not the same one twice
        for key in kind.commons:
            assert key in COMMONS


def test_no_two_bosses_open_with_the_same_pair():
    # Phase one is one attribute trick and these two. Share a pair and two of
    # the five fights are the same fight until half health.
    pairs = {frozenset(kind.commons) for kind in BOSS_KINDS}
    assert len(pairs) == len(BOSS_KINDS)


def test_all_five_commons_get_used():
    used = {key for kind in BOSS_KINDS for key in kind.commons}
    assert used == set(COMMONS)


# --- the two phases -------------------------------------------------------


def test_it_opens_in_the_first_phase():
    assert _boss().phase == 1


def test_half_health_turns_it():
    boss = _boss()
    boss.damage(boss.kind.hp * (1 - config.BOSS_PHASE_AT) - 1)
    assert boss.phase == 1
    boss.damage(2)
    assert boss.phase == 2


def test_the_phase_never_goes_back():
    # Anything that heals it -- its own trick, a missed hit, a later idea --
    # must not hand the player the easier fight a second time.
    boss = _boss()
    _hurt_into_phase_two(boss)
    boss.hp = boss.kind.hp
    assert boss.phase == 2


def test_there_is_no_third_phase():
    boss = _boss()
    boss.damage(boss.kind.hp - 1)
    assert boss.phase == 2


def test_the_first_phase_still_throws_the_element():
    # A boss whose element waits for phase two has no element for half the
    # fight, and the ground it stands on stops meaning anything.
    boss = _boss()
    assert len(boss.tricks_now) == 1
    assert TRICKS[boss.tricks_now[0]].tier == 1


def test_the_second_phase_adds_the_other_two():
    boss = _boss()
    _hurt_into_phase_two(boss)
    assert list(boss.tricks_now) == list(boss.kind.tricks)
    assert [TRICKS[k].tier for k in boss.tricks_now] == [1, 2, 3]


def test_the_supreme_trick_is_held_back_for_the_second_phase():
    # It is the one the player takes away from the fight; seeing it early
    # spends the reveal.
    boss = _boss()
    assert all(TRICKS[k].tier < 3 for k in boss.tricks_now)


def test_the_commons_do_not_change_with_the_phase():
    # What grows is the element. The two blows stay the two blows, so the
    # second phase reads as the same thing hitting harder.
    boss = _boss()
    before = boss.commons_now
    _hurt_into_phase_two(boss)
    assert boss.commons_now == before


def test_the_second_phase_raises_all_three():
    boss = _boss()
    tough, hit, quick = boss.taken_multiplier, boss.contact_dps, boss.speed
    _hurt_into_phase_two(boss)
    assert boss.taken_multiplier > tough  # frailer: it takes more
    assert boss.contact_dps > hit
    assert boss.speed > quick


def test_damage_is_scaled_by_how_frail_it_has_become():
    boss = _boss()
    _hurt_into_phase_two(boss)
    before = boss.hp
    boss.damage(100)
    assert boss.hp == before - 100 * boss.taken_multiplier


# --- it stays in its temple ----------------------------------------------


def test_it_walks_at_the_player():
    boss = _boss()
    boss.update(1.0, CENTRE + pygame.Vector2(500, 0), CENTRE, config.TEMPLE_RADIUS)
    assert boss.pos.x > CENTRE.x


def test_it_will_not_follow_you_out_of_the_room():
    # Loose on the map it would wander into the ring, and the temple would
    # stop being the place the fight happens.
    boss = _boss()
    far = CENTRE + pygame.Vector2(config.TEMPLE_RADIUS * 10, 0)
    for _ in range(600):
        boss.update(config.FIXED_DT, far, CENTRE, config.TEMPLE_RADIUS)
    assert CENTRE.distance_to(boss.pos) <= config.TEMPLE_RADIUS


def test_it_dies_once():
    boss = _boss()
    boss.damage(boss.kind.hp * 10)
    assert boss.is_dead
    assert boss.hp <= 0


# --- the thrown arm -------------------------------------------------------


def test_the_arm_starts_at_home():
    arm = boss_fight.Arm()
    assert not arm.out
    assert not arm.melee_locked


def test_a_thrown_arm_flies_at_where_you_were():
    arm = boss_fight.Arm()
    arm.throw(CENTRE, CENTRE + pygame.Vector2(400, 0))
    before = arm.pos.distance_to(CENTRE)
    arm.update(0.2, CENTRE, None)
    assert arm.pos.distance_to(CENTRE) > before


def test_nothing_happens_until_it_touches_you():
    # It is a blow you can step out of, not a tax on standing in the room.
    arm = boss_fight.Arm()
    arm.throw(CENTRE, CENTRE + pygame.Vector2(400, 0))
    dodged = pygame.Vector2(CENTRE) + pygame.Vector2(0, 600)
    for _ in range(200):
        arm.update(config.FIXED_DT, CENTRE, dodged)
    assert arm.caught is None


def test_catching_you_drags_you_back():
    arm = boss_fight.Arm()
    stood = CENTRE + pygame.Vector2(400, 0)
    arm.throw(CENTRE, stood)
    for _ in range(200):
        arm.update(config.FIXED_DT, CENTRE, pygame.Vector2(stood))
        if arm.caught is not None:
            break
    assert arm.caught is not None
    assert arm.caught.distance_to(CENTRE) < stood.distance_to(CENTRE)


def test_the_close_blows_stop_while_the_arm_is_away():
    # Half of what it hits with is in flight. Dodging the arm is what buys the
    # window, so the window has to exist.
    arm = boss_fight.Arm()
    arm.throw(CENTRE, CENTRE + pygame.Vector2(400, 0))
    assert arm.out
    assert arm.melee_locked


def test_a_missed_arm_comes_home():
    # Left out forever, one dodge would disarm the boss for the whole fight.
    arm = boss_fight.Arm()
    arm.throw(CENTRE, CENTRE + pygame.Vector2(400, 0))
    away = CENTRE + pygame.Vector2(0, 5000)
    for _ in range(2000):
        arm.update(config.FIXED_DT, CENTRE, away)
        if not arm.out:
            break
    assert not arm.out
    assert not arm.melee_locked
    assert arm.pos.distance_to(CENTRE) < 1.0


def test_it_cannot_be_thrown_twice_at_once():
    arm = boss_fight.Arm()
    arm.throw(CENTRE, CENTRE + pygame.Vector2(400, 0))
    arm.update(0.3, CENTRE, None)
    where = pygame.Vector2(arm.pos)
    arm.throw(CENTRE, CENTRE + pygame.Vector2(-400, 0))
    assert arm.pos == where  # the second throw was refused
