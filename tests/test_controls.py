import pygame

from game.core import controls as ctl
from game.core.controls import Controls


def test_the_defaults_are_the_documented_keys():
    c = Controls()
    assert c.keys_for(ctl.ACTION) == (pygame.K_f,)
    assert c.keys_for(ctl.MOVE_UP) == (pygame.K_w,)
    assert c.action_of(pygame.K_SPACE) == ctl.DODGE


def test_every_action_has_a_label_and_a_default():
    assert set(ctl.LABELS) == set(ctl.DEFAULTS)


def test_no_default_key_is_shared_between_actions():
    seen: dict[int, str] = {}
    for action, keys in ctl.DEFAULTS.items():
        for key in keys:
            assert key not in seen, (action, seen.get(key))
            seen[key] = action


def test_rebinding_moves_the_action_to_the_new_key():
    c = Controls()
    assert c.rebind(ctl.ACTION, pygame.K_j)
    assert c.keys_for(ctl.ACTION) == (pygame.K_j,)
    assert c.action_of(pygame.K_f) is None


def test_taking_a_used_key_swaps_rather_than_orphans():
    c = Controls()
    c.rebind(ctl.ACTION, pygame.K_e)  # E was "sync"
    assert c.keys_for(ctl.ACTION) == (pygame.K_e,)
    assert c.keys_for(ctl.SYNC) == (pygame.K_f,)  # handed the old key


def test_taking_one_of_two_keys_leaves_the_other():
    c = Controls()
    c.rebind(ctl.DODGE, pygame.K_RSHIFT)
    assert c.keys_for(ctl.SPRINT) == (pygame.K_LSHIFT,)


def test_reserved_keys_cannot_be_bound():
    c = Controls()
    assert not c.rebind(ctl.ACTION, pygame.K_ESCAPE)
    assert not c.rebind(ctl.ACTION, pygame.K_F1)
    assert c.keys_for(ctl.ACTION) == (pygame.K_f,)


def test_reset_puts_everything_back():
    c = Controls()
    c.rebind(ctl.ACTION, pygame.K_j)
    c.reset()
    assert c.keys_for(ctl.ACTION) == (pygame.K_f,)


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "controls.json"
    c = Controls()
    c.rebind(ctl.ACTION, pygame.K_j)
    c.save(path)
    assert '"j"' in path.read_text(encoding="utf-8")  # names, readable by hand
    assert Controls.load(path).keys_for(ctl.ACTION) == (pygame.K_j,)


def test_a_missing_file_gives_the_defaults(tmp_path):
    assert Controls.load(tmp_path / "nope.json").keys_for(ctl.ACTION) == (pygame.K_f,)


def test_a_broken_file_gives_the_defaults(tmp_path):
    path = tmp_path / "controls.json"
    path.write_text("{not json", encoding="utf-8")
    assert Controls.load(path).keys_for(ctl.ACTION) == (pygame.K_f,)


def test_one_bad_entry_costs_only_that_entry():
    c = Controls.from_dict({"action": ["j"], "dodge": ["no such key"], "sync": "e"})
    assert c.keys_for(ctl.ACTION) == (pygame.K_j,)
    assert c.keys_for(ctl.DODGE) == (pygame.K_SPACE,)
    assert c.keys_for(ctl.SYNC) == (pygame.K_e,)


def test_a_file_cannot_bind_a_reserved_key():
    c = Controls.from_dict({"action": ["escape"]})
    assert c.keys_for(ctl.ACTION) == (pygame.K_f,)
