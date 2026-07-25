import pygame

from game import config
from game.entities.enemy import Virus
from game.entities.projectile import Projectile
from game.items.tools import WeaponTool
from game.scenes.play import PlayScene


def _key_event(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def test_number_keys_select_hotbar():
    scene = PlayScene()
    scene.handle_event(_key_event(pygame.K_2))
    assert scene.hotbar.selected == 1
    scene.handle_event(_key_event(pygame.K_1))
    assert scene.hotbar.selected == 0


def test_y_toggles_camera_lock():
    scene = PlayScene()
    start_mode = scene.camera.mode
    scene.handle_event(_key_event(pygame.K_y))
    assert scene.camera.mode != start_mode
    scene.handle_event(_key_event(pygame.K_y))
    assert scene.camera.mode == start_mode


def test_movement_key_moves_player():
    scene = PlayScene()
    start_x = scene.player.pos.x
    scene.handle_event(_key_event(pygame.K_d))
    scene.update(config.FIXED_DT)
    assert scene.player.pos.x > start_x


def test_sync_transfers_backpack_at_core():
    scene = PlayScene()
    scene.player.pos = pygame.Vector2(scene.core.pos)  # stand on the core
    scene.backpack.add(3)
    scene.update(config.FIXED_DT)
    assert scene.backpack.count == 0
    assert scene.documents.count == 3


def test_draw_runs_without_error(surface):
    scene = PlayScene()
    scene.draw(surface)  # must not raise on the 64x64 offscreen surface


def test_weapon_in_slot_one_on_start():
    scene = PlayScene()
    assert isinstance(scene.hotbar.slots[1], WeaponTool)


def test_firing_weapon_spawns_projectile():
    scene = PlayScene()
    scene.hotbar.select(1)  # weapon
    scene._mouse_held = True
    scene._mouse_screen = pygame.Vector2(0, 0)  # aim off to a side
    scene.update(config.FIXED_DT)
    assert len(scene.projectiles) >= 1
    assert isinstance(scene.projectiles[0], Projectile)


def test_space_triggers_dodge():
    scene = PlayScene()
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    scene.update(config.FIXED_DT)
    assert scene.player.invulnerable is True


def test_death_applies_penalty_and_starts_respawn():
    scene = PlayScene()
    scene.player.pos = pygame.Vector2(500, 500)  # away from the core's sync zone
    scene.backpack.add(5)
    scene.player.hp = 0
    scene.update(config.FIXED_DT)
    assert scene.backpack.count == 3  # halved, round up
    assert scene._respawn_timer > 0


def test_respawn_returns_player_to_core():
    scene = PlayScene()
    scene.player.hp = 0
    scene.update(config.FIXED_DT)  # triggers death
    scene._respawn_timer = config.FIXED_DT  # fast-forward to the respawn frame
    scene.update(config.FIXED_DT)
    assert scene.player.pos == scene.core.pos
    assert scene.player.hp == scene.player.max_hp


def test_draw_runs_with_enemies_and_projectiles(surface):
    scene = PlayScene()
    scene.enemies.append(Virus(pos=pygame.Vector2(scene.player.pos)))
    scene.projectiles.append(
        Projectile(pos=pygame.Vector2(scene.player.pos), vel=pygame.Vector2(1, 0), damage=1)
    )
    scene.draw(surface)  # must not raise
