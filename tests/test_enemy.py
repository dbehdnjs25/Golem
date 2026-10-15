import dataclasses

import pygame
import pytest

from game import config
from game.entities.enemy import GOLEM_KINDS, PLAIN_GOLEM, TARGET_CORE, EnemyKind, Golem
from game.world.map import WorldMap

WORLD = WorldMap()
CENTRE = WORLD.center


def test_a_bare_golem_is_the_plain_kind():
    assert Golem(pos=pygame.Vector2(CENTRE)).kind is PLAIN_GOLEM


def test_a_golem_takes_its_numbers_from_its_kind():
    g = Golem(pos=pygame.Vector2(CENTRE))
    assert g.hp == PLAIN_GOLEM.hp
    assert g.speed == PLAIN_GOLEM.speed
    assert g.radius == PLAIN_GOLEM.radius


def test_every_golem_kind_marches_on_the_core():
    # That is what a golem IS. Anything hunting the player is an animal.
    for kind in GOLEM_KINDS:
        assert kind.target == TARGET_CORE


def test_kinds_are_frozen_rows_with_unique_keys():
    with pytest.raises(dataclasses.FrozenInstanceError):
        PLAIN_GOLEM.hp = 1.0  # type: ignore[misc]
    keys = [k.key for k in GOLEM_KINDS]
    assert len(keys) == len(set(keys))


def test_a_kind_can_be_stronger_without_a_new_class():
    # The point of the table. Five biome golems arrive in step 8 as five rows,
    # not five subclasses.
    tough = EnemyKind(
        key="tough",
        name="단단한 골렘",
        target=TARGET_CORE,
        hp=PLAIN_GOLEM.hp * 3,
        speed=PLAIN_GOLEM.speed,
        radius=PLAIN_GOLEM.radius,
        contact_dps=PLAIN_GOLEM.contact_dps,
        color=(1, 2, 3),
    )
    g = Golem(pos=pygame.Vector2(CENTRE), kind=tough)
    assert g.hp == PLAIN_GOLEM.hp * 3
    assert isinstance(g, Golem)


def test_scaling_multiplies_health_and_speed_without_touching_the_kind():
    g = Golem(pos=pygame.Vector2(CENTRE), scale=2.0)
    assert g.hp == PLAIN_GOLEM.hp * 2
    assert g.speed > PLAIN_GOLEM.speed
    assert PLAIN_GOLEM.hp == config.GOLEM_HP  # the row itself is untouched


def test_moves_toward_target():
    g = Golem(pos=pygame.Vector2(CENTRE))
    g.update(1.0, CENTRE + pygame.Vector2(100, 0), WORLD)
    assert g.pos.x == CENTRE.x + g.speed
    assert g.pos.y == CENTRE.y


def test_does_not_move_when_on_target():
    g = Golem(pos=pygame.Vector2(CENTRE))
    g.update(1.0, pygame.Vector2(CENTRE), WORLD)
    assert g.pos == CENTRE


def test_chasing_past_the_rim_stops_at_the_rim():
    g = Golem(pos=CENTRE + pygame.Vector2(WORLD.radius - 10, 0))
    g.update(1.0, CENTRE + pygame.Vector2(WORLD.radius * 2, 0), WORLD)
    assert WORLD.contains(g.pos)


def test_damage_and_death():
    g = Golem(pos=pygame.Vector2(CENTRE))
    g.hp = 10
    assert g.is_dead is False
    g.damage(10)
    assert g.is_dead is True
