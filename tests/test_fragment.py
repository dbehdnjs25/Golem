import pygame

from game import config
from game.entities.fragment import Fragment


def test_damage_reduces_hp():
    f = Fragment(pos=pygame.Vector2(0, 0))
    depleted = f.damage(10)
    assert f.hp == config.FRAGMENT_HP - 10
    assert depleted is False


def test_damage_returns_true_when_it_depletes():
    f = Fragment(pos=pygame.Vector2(0, 0), hp=15)
    assert f.damage(10) is False
    assert f.damage(10) is True
    assert f.is_depleted


def test_the_trojan_hook_is_gone():
    import dataclasses

    fields = {field.name for field in dataclasses.fields(Fragment)}
    assert "on_depleted" not in fields
