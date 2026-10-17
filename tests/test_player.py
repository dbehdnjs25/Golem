import pygame
import pytest

from game import config
from game.entities.player import Player
from game.world.map import WorldMap

WORLD = WorldMap()
CENTRE = WORLD.center


def _player(offset=(0, 0)) -> Player:
    return Player(pos=CENTRE + pygame.Vector2(offset))


def test_moves_in_direction():
    p = _player()
    start = pygame.Vector2(p.pos)
    p.update(1.0, pygame.Vector2(1, 0), WORLD)
    assert p.pos.x == start.x + config.PLAYER_SPEED
    assert p.pos.y == start.y


def test_diagonal_is_normalized():
    p = _player()
    start = pygame.Vector2(p.pos)
    p.update(1.0, pygame.Vector2(1, 1), WORLD)
    assert p.pos.distance_to(start) == pytest.approx(config.PLAYER_SPEED)


def test_zero_direction_does_not_move():
    p = _player((300, -200))
    start = pygame.Vector2(p.pos)
    p.update(1.0, pygame.Vector2(0, 0), WORLD)
    assert p.pos == start


def test_clamped_to_the_map_rim():
    # Standing just inside the rim and walking straight out: the body's radius
    # keeps the whole circle on the map, so it stops short of the edge.
    p = Player(pos=CENTRE + pygame.Vector2(WORLD.radius - 1, 0))
    p.update(1.0, pygame.Vector2(1, 0), WORLD)
    assert CENTRE.distance_to(p.pos) == pytest.approx(WORLD.radius - config.PLAYER_RADIUS)
    assert WORLD.contains(p.pos)


def test_the_square_corner_is_off_the_map():
    # The world box's corner is outside the inscribed circle, so a player put
    # there is pulled back onto the rim rather than left standing in the void.
    p = Player(pos=pygame.Vector2(0, 0))
    p.update(1.0, pygame.Vector2(0, 0), WORLD)
    assert WORLD.contains(p.pos)


def test_dodge_grants_iframes_and_cooldown():
    p = _player()
    assert p.invulnerable is False
    p.update(0.0, pygame.Vector2(0, 0), WORLD, dodge_pressed=True)
    assert p.invulnerable is True
    assert p.dodge_cooldown_timer == config.DODGE_COOLDOWN


def test_dodge_iframes_expire():
    p = _player()
    p.update(0.0, pygame.Vector2(0, 0), WORLD, dodge_pressed=True)
    p.update(config.DODGE_IFRAMES, pygame.Vector2(0, 0), WORLD)
    assert p.invulnerable is False


def test_dodge_dashes_faster_when_moving():
    normal = _player()
    normal.update(config.DODGE_DURATION, pygame.Vector2(1, 0), WORLD)
    dashed = _player()
    dashed.update(config.DODGE_DURATION, pygame.Vector2(1, 0), WORLD, dodge_pressed=True)
    assert dashed.pos.x > normal.pos.x


def test_dodge_blocked_during_cooldown():
    p = _player()
    p.update(0.0, pygame.Vector2(0, 0), WORLD, dodge_pressed=True)
    p.update(config.DODGE_IFRAMES, pygame.Vector2(0, 0), WORLD)  # iframes end, still cooling
    assert p.invulnerable is False
    p.update(0.0, pygame.Vector2(0, 0), WORLD, dodge_pressed=True)  # re-press mid-cooldown
    assert p.invulnerable is False  # blocked


# --- stamina --------------------------------------------------------------


def test_a_fresh_player_is_full_of_wind():
    player = Player(pos=pygame.Vector2(0, 0))
    assert player.stamina == player.max_stamina
    assert not player.winded


def test_spending_takes_it():
    player = Player(pos=pygame.Vector2(0, 0))
    assert player.spend(30) is True
    assert player.stamina == player.max_stamina - 30


def test_spending_more_than_there_is_takes_nothing_at_all():
    # No half a dodge. Either the move happens or it does not, and a partial
    # charge would leave the player paying for something they did not get.
    player = Player(pos=pygame.Vector2(0, 0))
    player.stamina = 10
    assert player.spend(30) is False
    assert player.stamina == 10


def test_spending_exactly_what_is_left_works_and_leaves_nothing():
    player = Player(pos=pygame.Vector2(0, 0))
    player.stamina = 30
    assert player.spend(30) is True
    assert player.stamina == 0
    assert player.winded


def test_draining_is_allowed_to_run_dry():
    # Unlike spend, a drain is a trickle -- it takes whatever is there and does
    # not refuse. Digging and the bog work this way.
    player = Player(pos=pygame.Vector2(0, 0))
    player.stamina = 5
    player.drain(40)
    assert player.stamina == 0


def test_wind_comes_back_on_its_own():
    from game.systems import survival

    player = Player(pos=pygame.Vector2(0, 0))
    player.stamina = 0
    survival.update_stamina(config.STAMINA_DELAY + 1.0, player)
    assert player.stamina > 0


def test_it_does_not_come_back_the_instant_it_is_spent():
    # Without the pause, mashing dodge would recover between presses and the
    # cost would never be felt.
    from game.systems import survival

    player = Player(pos=pygame.Vector2(0, 0))
    player.spend(50)
    before = player.stamina
    survival.update_stamina(config.STAMINA_DELAY / 2, player)
    assert player.stamina == before


def test_a_drain_also_holds_the_recovery_off():
    from game.systems import survival

    player = Player(pos=pygame.Vector2(0, 0))
    player.drain(50)
    before = player.stamina
    survival.update_stamina(config.STAMINA_DELAY / 2, player)
    assert player.stamina == before


def test_it_never_climbs_past_full():
    from game.systems import survival

    player = Player(pos=pygame.Vector2(0, 0))
    survival.update_stamina(600.0, player)
    assert player.stamina == player.max_stamina


# --- running --------------------------------------------------------------


def test_running_covers_more_ground():
    # The map is a six-minute walk across. Running trades the wind you would
    # have fought with for the distance you would have walked.
    walked, ran = Player(pos=pygame.Vector2(0, 0)), Player(pos=pygame.Vector2(0, 0))
    east = pygame.Vector2(1, 0)
    walked.update(1.0, east, WORLD)
    ran.update(1.0, east, WORLD, sprinting=True)
    assert ran.pos.x > walked.pos.x


def test_running_costs_wind():
    player = Player(pos=pygame.Vector2(0, 0))
    player.update(1.0, pygame.Vector2(1, 0), WORLD, sprinting=True)
    assert player.stamina < player.max_stamina


def test_standing_still_and_holding_run_costs_nothing():
    # Wind pays for ground covered, not for a key being down.
    player = Player(pos=pygame.Vector2(0, 0))
    player.update(1.0, pygame.Vector2(0, 0), WORLD, sprinting=True)
    assert player.stamina == player.max_stamina


def test_an_empty_player_simply_walks():
    # Not a stutter, not a refusal to move -- just no longer fast.
    winded, walking = Player(pos=pygame.Vector2(0, 0)), Player(pos=pygame.Vector2(0, 0))
    winded.stamina = 0
    east = pygame.Vector2(1, 0)
    winded.update(1.0, east, WORLD, sprinting=True)
    walking.update(1.0, east, WORLD)
    assert winded.pos.x == pytest.approx(walking.pos.x)


def test_a_dodge_is_not_slowed_down_by_running_out():
    # The dash is already paid for; having no wind left must not cut it short.
    player = Player(pos=pygame.Vector2(0, 0))
    player.update(0.01, pygame.Vector2(1, 0), WORLD, dodge_pressed=True)
    player.stamina = 0
    before = player.pos.x
    player.update(0.05, pygame.Vector2(1, 0), WORLD, sprinting=True)
    assert player.pos.x - before > config.PLAYER_SPEED * 0.05


def test_running_is_slower_than_dodging():
    # Otherwise the dodge would be a worse sprint, and nobody would dodge.
    assert config.PLAYER_SPRINT_MULT < config.DODGE_SPEED_MULT


def test_a_dodge_costs_wind():
    player = Player(pos=pygame.Vector2(0, 0))
    player.update(0.01, pygame.Vector2(1, 0), WORLD, dodge_pressed=True)
    assert player.stamina == player.max_stamina - config.DODGE_COST


def test_a_dodge_with_nothing_left_simply_does_not_happen():
    # Not a slow dodge and not a free one. The i-frames are the whole value of
    # the move, so a half-priced version would be a half-priced escape.
    player = Player(pos=pygame.Vector2(0, 0))
    player.stamina = config.DODGE_COST / 2
    player.update(0.01, pygame.Vector2(1, 0), WORLD, dodge_pressed=True)
    assert not player.invulnerable
    assert player.dodge_timer == 0
    assert player.stamina == config.DODGE_COST / 2  # nothing taken either


def test_the_dodge_cooldown_is_not_burned_by_a_refused_dodge():
    player = Player(pos=pygame.Vector2(0, 0))
    player.stamina = 0
    player.update(0.01, pygame.Vector2(1, 0), WORLD, dodge_pressed=True)
    assert player.dodge_cooldown_timer == 0
