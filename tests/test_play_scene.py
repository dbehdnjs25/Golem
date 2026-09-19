import pygame
import pytest

from game import config
from game.entities.enemy import Golem
from game.entities.projectile import Projectile
from game.inventory import grid
from game.inventory.storage import Container
from game.items.item_kinds import CORE_SHARD, WORN_PACK
from game.items.tools import WeaponTool
from game.scenes.play import PlayScene
from game.systems.camera import FREE


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


def test_standing_on_core_does_not_sync_by_itself():
    scene = PlayScene()
    scene.core.ignite()
    scene.player.pos = pygame.Vector2(scene.core.pos)  # stand on the core
    scene.hotbar.add(CORE_SHARD, 3)
    scene.update(config.FIXED_DT)
    assert scene.hotbar.count(CORE_SHARD) == 3  # sync is manual now
    assert scene.store.count(CORE_SHARD) == 0


def test_sync_key_transfers_backpack_at_core():
    scene = PlayScene()
    scene.core.ignite()
    scene.player.pos = pygame.Vector2(scene.core.pos)
    scene.hotbar.add(CORE_SHARD, 3)
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    assert scene.hotbar.count(CORE_SHARD) == 0
    assert scene.store.count(CORE_SHARD) == 3


def test_sync_key_does_nothing_out_of_range():
    scene = PlayScene()
    scene.core.ignite()
    scene.player.pos = scene.core.pos + pygame.Vector2(1000, 0)  # outside the sync zone
    scene.hotbar.add(CORE_SHARD, 3)
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    assert scene.hotbar.count(CORE_SHARD) == 3
    assert scene.store.count(CORE_SHARD) == 0


def test_sync_key_is_consumed_after_one_step():
    scene = PlayScene()
    scene.core.ignite()
    scene.player.pos = pygame.Vector2(scene.core.pos)
    scene.hotbar.add(CORE_SHARD, 3)
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    scene.hotbar.add(CORE_SHARD, 2)  # mined more without pressing again
    scene.update(config.FIXED_DT)
    assert scene.hotbar.count(CORE_SHARD) == 2  # one press, one transfer
    assert scene.store.count(CORE_SHARD) == 3


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


def test_death_never_touches_the_hotbar():
    # The five hotbar slots are the one thing a death spares. That is what
    # makes choosing their contents a decision worth making.
    scene = PlayScene()
    scene.player.pos = scene.core.pos + pygame.Vector2(5_000, 0)
    scene.hotbar.add(CORE_SHARD, 5)
    scene.player.hp = 0
    scene.update(config.FIXED_DT)
    assert scene.hotbar.count(CORE_SHARD) == 5
    assert scene._respawn_timer > 0


def _packed(scene, count=5):
    scene.backpack = Container.empty(config.BACKPACK_SLOTS)
    scene.worn_pack = WORN_PACK
    scene.backpack.add(CORE_SHARD, count)
    scene.player.pos = scene.core.pos + pygame.Vector2(5_000, 0)
    return scene


def test_death_leaves_the_whole_pack_in_a_pile():
    scene = _packed(PlayScene())
    scene.player.hp = 0
    scene.update(config.FIXED_DT)
    assert scene.backpack is None  # every slot is gone, not half the goods
    assert scene.worn_pack is None
    assert len(scene.loot) == 1
    assert scene.loot[0].contents.count(CORE_SHARD) == 5
    assert scene.loot[0].pack is WORN_PACK


def test_walking_onto_the_pile_takes_it_all_back():
    scene = _packed(PlayScene())
    where = pygame.Vector2(scene.player.pos)
    scene.player.hp = 0
    scene.update(config.FIXED_DT)
    scene._respawn_timer = 0.0
    scene.player.hp = scene.player.max_hp
    scene.player.pos = where
    scene.update(config.FIXED_DT)
    assert scene.loot == []
    assert scene.backpack is not None
    assert scene.backpack.count(CORE_SHARD) == 5
    assert scene.worn_pack is WORN_PACK


def test_a_pile_out_of_reach_is_left_where_it_is():
    scene = _packed(PlayScene())
    scene.player.hp = 0
    scene.update(config.FIXED_DT)
    scene._respawn_timer = 0.0
    scene.player.hp = scene.player.max_hp
    scene.player.pos = scene.core.pos  # respawned far away
    scene.update(config.FIXED_DT)
    assert len(scene.loot) == 1
    assert scene.backpack is None


def test_a_second_death_leaves_a_second_pile():
    # Piles accumulate. Dying again does not erase the first one; each runs out
    # on its own clock, so the pressure is a deadline rather than a rule about
    # not dying twice.
    scene = _packed(PlayScene())
    scene.player.hp = 0
    scene.update(config.FIXED_DT)
    scene._respawn_timer = 0.0
    scene.player.hp = scene.player.max_hp
    scene.backpack = Container.empty(config.BACKPACK_SLOTS)
    scene.worn_pack = WORN_PACK
    scene.player.pos = scene.core.pos + pygame.Vector2(9_000, 0)
    scene.player.hp = 0
    scene.update(config.FIXED_DT)
    assert len(scene.loot) == 2
    assert scene.loot[0].pos != scene.loot[1].pos


def test_a_pile_left_too_long_is_gone():
    scene = _packed(PlayScene())
    scene.player.hp = 0
    scene.update(config.FIXED_DT)
    scene._respawn_timer = 0.0
    scene.player.hp = scene.player.max_hp
    scene.player.pos = scene.core.pos  # nowhere near it
    scene.update(config.LOOT_LIFETIME)
    assert scene.loot == []


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
    scene.enemies.append(Golem(pos=pygame.Vector2(scene.player.pos)))
    scene.projectiles.append(
        Projectile(pos=pygame.Vector2(scene.player.pos), vel=pygame.Vector2(1, 0), damage=1)
    )
    scene.draw(surface)  # must not raise


def test_the_scene_owns_a_map_and_five_temple_sites():
    scene = PlayScene()
    assert scene.world.contains(scene.player.pos)
    assert len(scene.temple_sites) == 5
    assert all(scene.world.contains(site) for site in scene.temple_sites)


def test_the_core_stands_at_the_centre_of_the_map():
    scene = PlayScene()
    assert scene.core.pos == scene.world.center


def test_the_centre_of_the_view_is_painted_grassland():
    from game.world import biomes

    scene = PlayScene()
    surface = pygame.Surface(config.SCREEN_SIZE)
    scene.camera.center_on(scene.world.center)
    scene.draw(surface)
    # The camera is centred on the core, so the middle of the screen is the
    # middle of the grassland. Sample to the side of the core, which is drawn
    # on top of it.
    probe = (config.SCREEN_WIDTH // 2 + int(config.CORE_RADIUS) + 20, config.SCREEN_HEIGHT // 2)
    assert surface.get_at(probe)[:3] == biomes.GRASSLAND.color


def test_outside_the_map_is_painted_void():
    scene = PlayScene()
    surface = pygame.Surface(config.SCREEN_SIZE)
    # Park the camera on the world box's top-left corner, which is outside the
    # inscribed circle.
    scene.camera.mode = FREE
    scene.camera.offset = pygame.Vector2(0, 0)
    scene.draw(surface)
    assert surface.get_at((2, 2))[:3] == config.VOID_COLOR


def test_the_run_starts_with_an_unlit_core_and_no_ward():
    scene = PlayScene()
    assert scene.core.ignited is False
    assert scene.core.ward_radius == 0.0
    assert scene.clock.day == 1


def test_shards_are_scattered_within_reach_of_the_spawn():
    scene = PlayScene()
    on_ground = [f for f in scene.fragments if f.kind is CORE_SHARD]
    assert len(on_ground) >= config.CORE_SHARDS_TO_IGNITE
    assert all(scene.player.pos.distance_to(f.pos) < config.SPAWN_RADIUS for f in on_ground)


def test_pressing_e_on_the_pedestal_with_enough_shards_ignites_the_core():
    scene = PlayScene()
    scene.player.pos = pygame.Vector2(scene.core.pos)
    scene.hotbar.add(CORE_SHARD, config.CORE_SHARDS_TO_IGNITE)
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    assert scene.core.ignited is True
    assert scene.core.level == 1
    assert scene.hotbar.count(CORE_SHARD) == 0  # the shards are consumed


def test_too_few_shards_does_not_ignite():
    scene = PlayScene()
    scene.player.pos = pygame.Vector2(scene.core.pos)
    scene.hotbar.add(CORE_SHARD, config.CORE_SHARDS_TO_IGNITE - 1)
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    assert scene.core.ignited is False
    assert scene.hotbar.count(CORE_SHARD) == config.CORE_SHARDS_TO_IGNITE - 1


def test_igniting_away_from_the_pedestal_does_nothing():
    scene = PlayScene()
    scene.player.pos = scene.core.pos + pygame.Vector2(5_000, 0)
    scene.hotbar.add(CORE_SHARD, config.CORE_SHARDS_TO_IGNITE)
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    assert scene.core.ignited is False


def test_the_clock_advances_with_the_scene():
    scene = PlayScene()
    for _ in range(120):
        scene.update(config.FIXED_DT)
    assert scene.clock.elapsed == pytest.approx(120 * config.FIXED_DT)


def test_the_player_heals_only_after_ignition():
    scene = PlayScene()
    scene.player.pos = pygame.Vector2(scene.core.pos)
    scene.player.hp = 10.0
    scene.update(config.FIXED_DT)
    assert scene.player.hp == 10.0  # no ward yet
    scene.core.ignite()
    scene.update(config.FIXED_DT)
    assert scene.player.hp > 10.0


def test_night_darkens_the_screen():
    scene = PlayScene()
    scene.camera.center_on(scene.world.center)
    probe = (config.SCREEN_WIDTH // 2 + int(config.CORE_RADIUS) + 20, config.SCREEN_HEIGHT // 2)

    lit = pygame.Surface(config.SCREEN_SIZE)
    scene.draw(lit)
    day_pixel = lit.get_at(probe)[:3]

    scene.clock.elapsed = config.DAY_LENGTH + 1  # into the night
    dark = pygame.Surface(config.SCREEN_SIZE)
    scene.draw(dark)
    night_pixel = dark.get_at(probe)[:3]

    assert sum(night_pixel) < sum(day_pixel)


def test_a_pile_decays_while_the_player_waits_to_respawn():
    # The respawn wait returns early from update(). A deadline that stops while
    # the player is dead would not be a deadline at all.
    scene = _packed(PlayScene())
    scene.player.hp = 0
    scene.update(config.FIXED_DT)
    assert scene._respawn_timer > 0
    before = scene.loot[0].ttl
    scene.update(1.0)
    assert scene.loot[0].ttl < before


def _press_i(scene):
    scene.handle_event(_key_event(pygame.K_i))


def test_i_opens_and_closes_the_belongings_screen():
    scene = PlayScene()
    assert scene.grid_open is False
    _press_i(scene)
    assert scene.grid_open is True
    _press_i(scene)
    assert scene.grid_open is False


def test_the_world_waits_while_the_screen_is_open():
    scene = PlayScene()
    scene.core.ignite()
    _press_i(scene)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d))
    where = pygame.Vector2(scene.player.pos)
    scene.update(config.FIXED_DT)
    assert scene.player.pos == where  # movement is held


def test_the_clock_keeps_running_while_the_screen_is_open():
    # Pausing the world is a convenience; pausing the day would be an exploit.
    scene = PlayScene()
    _press_i(scene)
    before = scene.clock.elapsed
    scene.update(config.FIXED_DT)
    assert scene.clock.elapsed > before


def test_closing_the_screen_returns_what_was_in_hand():
    scene = PlayScene()
    scene.backpack = Container.empty(config.BACKPACK_SLOTS)
    scene.backpack.add(CORE_SHARD, 4)
    _press_i(scene)
    scene.grid.click(grid.PACK, 0, scene.backpack, scene.hotbar)
    assert scene.grid.held is not None
    _press_i(scene)
    assert scene.grid.held is None
    assert scene._carried(CORE_SHARD) == 4


def test_the_world_keeps_running_while_the_player_is_down():
    # A death should not freeze the field. What was chasing the player is still
    # out there on the way back.
    scene = PlayScene()
    scene.player.pos = scene.core.pos + pygame.Vector2(5_000, 0)
    scene.enemies.append(Golem(pos=scene.player.pos + pygame.Vector2(400, 0)))
    scene.player.hp = 0
    scene.update(config.FIXED_DT)
    assert scene._respawn_timer > 0
    where = pygame.Vector2(scene.enemies[0].pos)
    scene.update(config.FIXED_DT)
    assert scene.enemies[0].pos != where  # it kept walking


def test_a_downed_player_takes_no_further_damage():
    scene = PlayScene()
    scene.player.pos = scene.core.pos + pygame.Vector2(5_000, 0)
    scene.enemies.append(Golem(pos=pygame.Vector2(scene.player.pos)))
    scene.player.hp = 0
    scene.update(config.FIXED_DT)
    for _ in range(30):
        scene.update(config.FIXED_DT)
    assert scene.player.hp == 0  # not driven further under


def test_only_one_pile_comes_of_one_death():
    # The death branch must not re-fire every frame the player lies at zero.
    scene = _packed(PlayScene())
    scene.player.hp = 0
    for _ in range(30):
        scene.update(config.FIXED_DT)
    assert len(scene.loot) == 1
