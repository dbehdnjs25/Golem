import pygame
import pytest

from game import config
from game.entities.enemy import Golem
from game.entities.projectile import Projectile
from game.inventory import grid
from game.inventory.stack import Stack
from game.inventory.storage import Container
from game.items import glyphs as glyph_table
from game.items.item_kinds import CORE_SHARD, ITEM_KINDS, STONE, WORN_PACK
from game.items.tools import WeaponTool
from game.scenes.play import PlayScene
from game.systems import raids
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


def test_the_run_opens_with_nothing_but_a_weapon():
    # No tools handed over. Bare hands take wood off a tree, wood makes the
    # first axe, and the opening is something the player does.
    scene = PlayScene()
    assert isinstance(scene.hotbar.slots[4], WeaponTool)
    assert all(slot is None for slot in scene.hotbar.slots[:4])


def test_trees_stand_by_the_pedestal_to_start_from():
    from game.items.item_kinds import WOOD

    scene = PlayScene()
    assert sum(1 for f in scene.fragments if f.kind is WOOD) >= 5


def test_no_backpack_is_lying_about_any_more():
    from game.items.item_kinds import WORN_PACK

    scene = PlayScene()
    assert not any(f.kind is WORN_PACK for f in scene.fragments)


def test_firing_weapon_spawns_projectile():
    scene = PlayScene()
    scene.hotbar.select(4)  # weapon
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


def _ready_to_build(scene, kind):
    scene.core.ignite()
    scene.hotbar.slots[3] = Stack(kind, 1)
    scene.hotbar.select(3)
    scene.player.pos = pygame.Vector2(scene.core.pos)
    scene.camera.center_on(scene.player.pos)
    return scene


def test_clicking_with_a_station_in_hand_builds_it():
    from game.items.item_kinds import BENCH

    scene = _ready_to_build(PlayScene(), BENCH)
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(480, 270)))
    assert len(scene.stations) == 1
    assert scene.hotbar.count(BENCH) == 0  # the item is spent


def test_a_failed_build_keeps_the_item():
    from game.items.item_kinds import BENCH

    scene = PlayScene()  # core never lit -> no ward -> nowhere to build
    scene.hotbar.slots[3] = Stack(BENCH, 1)
    scene.hotbar.select(3)
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(480, 270)))
    assert scene.stations == []
    assert scene.hotbar.count(BENCH) == 1


def test_building_does_not_also_start_swinging():
    # One press should do one thing. Otherwise placing a bench would also chew
    # whatever node happens to be under the cursor.
    from game.items.item_kinds import BENCH

    scene = _ready_to_build(PlayScene(), BENCH)
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(480, 270)))
    assert scene._mouse_held is False


def test_a_station_keeps_working_while_the_player_is_away():
    # The whole value of smelting taking time: set it going, leave, come back.
    from game.entities.station import Station
    from game.items.item_kinds import COPPER_INGOT, SMELTER
    from game.items.recipes import RECIPES

    recipe = next(r for r in RECIPES if r.output is COPPER_INGOT)
    scene = PlayScene()
    smelter = Station(pos=scene.core.pos + pygame.Vector2(20_000, 0), kind=SMELTER)
    smelter.start(recipe)
    scene.stations.append(smelter)
    for _ in range(int(recipe.seconds / config.FIXED_DT) + 2):
        scene.update(config.FIXED_DT)
    assert smelter.job is None
    assert smelter.output.count(COPPER_INGOT) == recipe.count


def test_standing_by_a_finished_station_empties_it():
    from game.entities.station import Station
    from game.items.item_kinds import COPPER_INGOT, SMELTER

    scene = PlayScene()
    scene.backpack = Container.empty(config.BACKPACK_SLOTS)
    smelter = Station(pos=pygame.Vector2(scene.player.pos), kind=SMELTER)
    smelter.output.add(COPPER_INGOT, 3)
    scene.stations.append(smelter)
    scene.update(config.FIXED_DT)
    assert smelter.output.used == 0
    assert scene.backpack.count(COPPER_INGOT) == 3


def _press_c(scene):
    scene.handle_event(_key_event(pygame.K_c))


def test_c_opens_the_crafting_menu():
    scene = PlayScene()
    assert scene.craft_open is False
    _press_c(scene)
    assert scene.craft_open is True
    _press_c(scene)
    assert scene.craft_open is False


def test_only_one_screen_is_open_at_a_time():
    scene = PlayScene()
    _press_i(scene)
    _press_c(scene)
    assert scene.craft_open is True
    assert scene.grid_open is False


def test_the_menu_offers_only_what_the_spot_allows():
    from game.items.item_kinds import BENCH, SMELTER

    scene = PlayScene()
    offered = {r.output for r, _ in scene._craft_rows()}
    assert BENCH in offered  # empty hands can manage a bench
    assert SMELTER not in offered  # the smelter wants a bench standing


def test_standing_at_a_bench_widens_the_menu():
    from game.entities.station import Station
    from game.items.item_kinds import BENCH, SMELTER

    scene = PlayScene()
    scene.stations.append(Station(pos=pygame.Vector2(scene.player.pos), kind=BENCH))
    assert SMELTER in {r.output for r, _ in scene._craft_rows()}


def test_affordable_rows_sort_to_the_top():
    from game.items.item_kinds import WOOD

    scene = PlayScene()
    scene.hotbar.add(WOOD, 3)
    rows = scene._craft_rows()
    assert rows[0][1] is True  # something is makeable and it is listed first


def test_clicking_an_instant_recipe_makes_it():
    from game.items.item_kinds import WOOD, WOOD_PICK

    scene = PlayScene()
    scene.hotbar.add(WOOD, 3)
    _press_c(scene)
    index = next(i for i, (r, _) in enumerate(scene._craft_rows()) if r.output is WOOD_PICK)
    at = scene._craft_row_rect(index).center
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=at))
    assert scene.hotbar.count(WOOD_PICK) == 1


def test_clicking_an_unaffordable_row_does_nothing():
    from game.items.item_kinds import BENCH

    scene = PlayScene()
    _press_c(scene)
    index = next(i for i, (r, _) in enumerate(scene._craft_rows()) if r.output is BENCH)
    at = scene._craft_row_rect(index).center
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=at))
    assert scene._carried(BENCH) == 0


def test_a_timed_recipe_goes_to_the_station_instead_of_the_hand():
    # Smelting is set going and walked away from; it does not appear in a pack.
    from game.entities.station import Station
    from game.items.item_kinds import COPPER_INGOT, COPPER_ORE, SMELTER

    scene = PlayScene()
    scene.backpack = Container.empty(config.BACKPACK_SLOTS)
    scene.backpack.add(COPPER_ORE, 4)
    smelter = Station(pos=pygame.Vector2(scene.player.pos), kind=SMELTER)
    scene.stations.append(smelter)
    _press_c(scene)
    index = next(i for i, (r, _) in enumerate(scene._craft_rows()) if r.output is COPPER_INGOT)
    at = scene._craft_row_rect(index).center
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=at))
    assert smelter.is_busy is True
    assert scene.backpack.count(COPPER_ORE) == 2  # the ore went in
    assert scene._carried(COPPER_INGOT) == 0  # nothing yet -- it has to run


def test_walking_over_litter_picks_it_up():
    # Twigs and pebbles are lying there, not embedded in anything. Swinging at
    # them was busywork; stepping on them is not.
    from game.items.item_kinds import TWIG

    scene = PlayScene()
    twig = next(f for f in scene.fragments if f.kind is TWIG)
    scene.player.pos = pygame.Vector2(twig.pos)
    scene.update(config.FIXED_DT)
    assert scene._carried(TWIG) >= 1
    assert twig not in scene.fragments


def test_a_tree_is_not_picked_up_by_walking_into_it():
    from game.items.item_kinds import WOOD

    scene = PlayScene()
    tree = next(f for f in scene.fragments if f.kind is WOOD)
    scene.player.pos = pygame.Vector2(tree.pos)
    scene.update(config.FIXED_DT)
    assert scene._carried(WOOD) == 0
    assert tree in scene.fragments


def test_litter_out_of_reach_stays_put():
    from game.items.item_kinds import TWIG

    scene = PlayScene()
    twig = next(f for f in scene.fragments if f.kind is TWIG)
    scene.player.pos = twig.pos + pygame.Vector2(config.PICKUP_RADIUS * 3, 0)
    scene.update(config.FIXED_DT)
    assert twig in scene.fragments


def test_litter_stays_on_the_ground_when_there_is_nowhere_to_put_it():
    from game.items.item_kinds import TWIG
    from game.items.tools import MiningTool

    scene = PlayScene()
    for i in range(len(scene.hotbar.slots)):
        scene.hotbar.slots[i] = MiningTool()
    twig = next(f for f in scene.fragments if f.kind is TWIG)
    scene.player.pos = pygame.Vector2(twig.pos)
    scene.update(config.FIXED_DT)
    assert twig in scene.fragments


def test_no_golems_before_the_core_is_lit():
    scene = PlayScene()
    for _ in range(int(60 / config.FIXED_DT)):
        scene.update(config.FIXED_DT)
    assert scene.enemies == []


def test_an_unlit_core_is_not_drawn_lit():
    # It looked like a bright disc before ignition, which read as a ward that
    # was already there -- the opening looked won before it began.
    surface = pygame.Surface(config.SCREEN_SIZE)
    scene = PlayScene()
    scene.camera.center_on(scene.core.pos)
    scene.player.pos = scene.core.pos + pygame.Vector2(400, 0)  # out of the way
    scene.draw(surface)
    middle = (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2)
    assert surface.get_at(middle)[:3] != config.CORE_COLOR


def test_lighting_it_makes_it_show():
    surface = pygame.Surface(config.SCREEN_SIZE)
    scene = PlayScene()
    scene.core.ignite()
    scene.camera.center_on(scene.core.pos)
    scene.player.pos = scene.core.pos + pygame.Vector2(400, 0)
    scene.draw(surface)
    middle = (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2)
    assert surface.get_at(middle)[:3] == config.CORE_COLOR


def test_the_core_gets_a_pointer_when_it_is_off_screen():
    from game.systems.camera import FREE

    scene = PlayScene()
    scene.camera.mode = FREE
    scene.camera.offset = pygame.Vector2(scene.core.pos) + pygame.Vector2(8_000, 8_000)
    surface = pygame.Surface(config.SCREEN_SIZE)
    scene.draw(surface)
    # It pins to whichever edge the ray crosses first -- here the top, since
    # the view is wider than it is tall. Scan the whole band rather than
    # guessing a pixel.
    top = int(config.COMPASS_MARGIN)
    band = [
        surface.get_at((x, y))[:3]
        for x in range(0, config.SCREEN_WIDTH, 2)
        for y in range(top - 8, top + 9)
    ]
    assert config.CORE_COLOR in band


def test_no_pointer_when_the_core_is_in_view():
    # The thing itself is the marker; a second one would just be clutter.
    scene = PlayScene()
    scene.core.ignite()
    scene.camera.center_on(scene.core.pos)
    surface = pygame.Surface(config.SCREEN_SIZE)
    scene.draw(surface)
    # Started below the gauges: the core's own health bar is drawn in the same
    # colour up in the corner, and it is not a compass marker.
    edge = [surface.get_at((int(config.COMPASS_MARGIN), y))[:3] for y in range(120, 500)]
    assert config.CORE_COLOR not in edge


def test_night_does_not_darken_the_player():
    # The dark is a mood, not a blindfold. Dimmed to the same grey as a wolf,
    # the player loses track of themselves in exactly the fight that matters.
    scene = PlayScene()
    scene.core.ignite()
    scene.player.pos.update(scene.core.pos + pygame.Vector2(scene.core.ward_radius + 500, 0))
    scene.camera.center_on(scene.player.pos)

    while not scene.clock.is_night:
        scene.clock.update(1.0)
    # A full-size surface: the camera maps into the real screen, so the tiny
    # shared fixture cannot hold the point we want to look at.
    surface = pygame.Surface(config.SCREEN_SIZE)
    scene.draw(surface)
    middle = scene.camera.world_to_screen(scene.player.pos)
    lit = surface.get_at((int(middle.x), int(middle.y)))[:3]
    assert lit == config.PLAYER_COLOR


# --- raids ----------------------------------------------------------------


def _wind_to(scene, day: int, night: bool) -> None:
    """Drive the clock to a given day and phase without touching anything else."""
    while scene.clock.day < day or scene.clock.is_night != night:
        scene.clock.update(10.0)


def test_a_raid_is_a_night_not_an_afternoon():
    scene = PlayScene()
    scene.core.ignite()
    raid_day = next(d for d in range(2, 40) if raids.is_raid_night(d, 0))
    _wind_to(scene, raid_day, night=False)
    assert not scene.is_raid  # the daytime of a raid day is still just a day
    _wind_to(scene, raid_day, night=True)
    assert scene.is_raid


def test_the_first_night_is_quiet():
    scene = PlayScene()
    scene.core.ignite()
    _wind_to(scene, 1, night=True)
    assert not scene.is_raid


def test_the_scene_counts_down_to_the_next_raid():
    scene = PlayScene()
    scene.core.ignite()
    assert scene.days_to_raid == raids.interval(0)


def test_killing_bosses_brings_the_raids_closer():
    scene = PlayScene()
    scene.core.ignite()
    before = scene.days_to_raid
    scene.core.bosses_killed = 5
    assert scene.days_to_raid < before


def test_losing_the_core_raises_the_signal_and_it_sticks():
    # A flag, not an ending. What a run does about it belongs with step 9.
    scene = PlayScene()
    scene.core.ignite()
    assert not scene.defeated
    scene.core.damage(scene.core.max_hp)
    scene.update(config.FIXED_DT)
    assert scene.defeated
    scene.core.repair(100)
    scene.update(config.FIXED_DT)
    assert scene.defeated  # it happened; mending the stone does not unhappen it


def test_stone_in_hand_mends_the_core_at_its_own_key():
    # The same press that deals with the core deals with its cracks. After a
    # raid that is the urgent half of the errand.
    scene = PlayScene()
    scene.core.ignite()
    scene.core.damage(config.CORE_REPAIR_PER_ITEM * 3)
    scene.player.pos.update(scene.core.pos)
    scene.hotbar.add(STONE, 10)
    hurt = scene.core.hp

    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    scene.update(config.FIXED_DT)

    assert scene.core.hp > hurt
    assert scene.hotbar.count(STONE) == 7  # three spent, the rest kept


def test_mending_a_whole_core_spends_no_stone():
    scene = PlayScene()
    scene.core.ignite()
    scene.player.pos.update(scene.core.pos)
    scene.hotbar.add(STONE, 10)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    scene.update(config.FIXED_DT)
    assert scene.hotbar.count(STONE) == 10


def _shot(scene) -> pygame.Surface:
    surface = pygame.Surface(config.SCREEN_SIZE)
    scene.draw(surface)
    return surface


def _has_ink(surface: pygame.Surface, rect: pygame.Rect, colour) -> bool:
    """Whether any pixel in ``rect`` is drawn in ``colour``."""
    for x in range(rect.left, rect.right, 2):
        for y in range(rect.top, rect.bottom, 2):
            if surface.get_at((x, y))[:3] == colour:
                return True
    return False


def test_the_calendar_is_on_screen():
    # The spec's shortening cycle only means anything if the player can count
    # it. Unreadable, it is just the occasional bad night.
    scene = PlayScene()
    scene.core.ignite()
    assert "1일차" in scene.calendar_line
    assert "7일" in scene.calendar_line  # a whole week stands between


def test_the_calendar_says_tonight_on_a_raid_day():
    scene = PlayScene()
    scene.core.ignite()
    raid_day = next(d for d in range(2, 40) if raids.is_raid_night(d, 0))
    _wind_to(scene, raid_day, night=False)
    assert "오늘" in scene.calendar_line


def test_the_core_bar_only_appears_once_the_core_can_be_hurt():
    # An unlit pedestal with a health bar promises a fight that cannot happen.
    scene = PlayScene()
    before = _shot(scene)
    gauge = pygame.Rect(8, 74, 126, 8)
    assert not _has_ink(before, gauge, config.CORE_COLOR)
    scene.core.ignite()
    assert _has_ink(_shot(scene), gauge, config.CORE_COLOR)


def test_a_raid_night_recolours_the_ward():
    # The wall is down, and that has to be visible from inside it.
    scene = PlayScene()
    scene.core.ignite()
    assert scene.ward_colour == config.WARD_COLOR
    raid_day = next(d for d in range(2, 40) if raids.is_raid_night(d, 0))
    _wind_to(scene, raid_day, night=True)
    assert scene.ward_colour == config.WARD_BROKEN_COLOR


def test_a_raid_paints_the_screen_edge():
    # The ward is thousands of units across and the view is hundreds, so the
    # broken rim and the golems on it are both off screen. This is the one
    # sign that does not depend on where the camera is looking.
    scene = PlayScene()
    scene.core.ignite()
    quiet = _shot(scene)
    corner = pygame.Rect(0, 0, config.RAID_EDGE_WIDTH, config.RAID_EDGE_WIDTH)
    assert not _has_ink(quiet, corner, config.WARD_BROKEN_COLOR)

    raid_day = next(d for d in range(2, 40) if raids.is_raid_night(d, 0))
    _wind_to(scene, raid_day, night=True)
    loud = _shot(scene)
    assert loud.get_at((1, 1))[:3] != quiet.get_at((1, 1))[:3]


def test_a_raid_night_leaves_no_safe_circle_in_the_dark():
    # The ward is holding nothing out, so there is no bright patch to show.
    scene = PlayScene()
    scene.core.ignite()
    scene.camera.center_on(scene.core.pos)
    middle = scene.camera.world_to_screen(scene.core.pos)
    probe = (int(middle.x) + 200, int(middle.y) + 120)

    _wind_to(scene, 2, night=True)  # an ordinary night
    assert not scene.is_raid
    calm = _shot(scene).get_at(probe)[:3]

    raid_day = next(d for d in range(3, 40) if raids.is_raid_night(d, 0))
    _wind_to(scene, raid_day, night=True)
    assert sum(_shot(scene).get_at(probe)[:3]) < sum(calm)


# --- structures and glyphs ------------------------------------------------


def test_standing_at_a_ruin_and_pressing_the_key_teaches_its_drawing():
    scene = PlayScene()
    site = scene.structures[0]
    scene.player.pos.update(site.pos)
    assert not scene.grimoire.knows(site.glyph)

    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    scene.update(config.FIXED_DT)

    assert scene.grimoire.knows(site.glyph)
    assert site.opened
    assert site.glyph.name in scene.note


def test_a_looted_ruin_gives_nothing_the_second_time():
    scene = PlayScene()
    site = scene.structures[0]
    scene.player.pos.update(site.pos)
    for _ in range(2):
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
        scene.update(config.FIXED_DT)
    assert len(scene.grimoire.learned) == 1


def test_a_ruin_across_the_map_cannot_be_read():
    scene = PlayScene()
    scene.player.pos.update(scene.core.pos)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    scene.update(config.FIXED_DT)
    assert scene.grimoire.learned == set()


def test_the_note_fades_on_its_own():
    scene = PlayScene()
    scene._say("아무 말")
    assert scene.note_left > 0
    for _ in range(int(config.NOTE_SECONDS / config.FIXED_DT) + 2):
        scene.update(config.FIXED_DT)
    assert scene.note_left == 0


def test_the_world_puts_out_a_ruin_for_every_basic_glyph():
    # Belt and braces over the placement test: this is the one that would
    # catch the scene seeding it wrong rather than the placer.
    scene = PlayScene()
    held = {s.glyph.key for s in scene.structures}
    for glyph in glyph_table.basic_glyphs():
        assert glyph.key in held


# --- carving --------------------------------------------------------------


def _ready_to_carve(scene) -> None:
    """Hold the weapon, know a glyph, have a chisel."""
    scene.hotbar.select(4)
    scene.grimoire.learn(glyph_table.VOLCANO_GLYPHS[0])
    scene.hotbar.add(ITEM_KINDS["chisel"], 1)


def test_carving_adds_its_power_to_what_the_weapon_lands_for():
    # The whole point. Without this the glyphs are a collection and nothing
    # else -- an engraved weapon has to actually hit harder.
    scene = PlayScene()
    _ready_to_carve(scene)
    fire = glyph_table.VOLCANO_GLYPHS[0]
    weapon = scene.hotbar.active_tool
    before = weapon.total_damage

    scene.carve(fire)

    assert weapon.engraved.glyphs == [fire]
    assert weapon.total_damage == before + fire.power


def test_three_cuts_and_the_chisel_is_gone():
    scene = PlayScene()
    _ready_to_carve(scene)
    for glyph in glyph_table.GLYPHS[:3]:
        scene.grimoire.learn(glyph)
    scene.hotbar.slots[4].engraved.slots = 9  # room enough to spend the tool

    for n, glyph in enumerate(glyph_table.GLYPHS[:3], start=1):
        assert scene.hotbar.count(ITEM_KINDS["chisel"]) == 1, f"gone after {n - 1}"
        scene.carve(glyph)
    assert scene.hotbar.count(ITEM_KINDS["chisel"]) == 0
    assert scene.chisel_left == config.CHISEL_USES  # the next one starts fresh


def test_carving_without_a_chisel_does_nothing_and_says_so():
    scene = PlayScene()
    scene.hotbar.select(4)
    fire = glyph_table.VOLCANO_GLYPHS[0]
    scene.grimoire.learn(fire)

    scene.carve(fire)

    assert scene.hotbar.active_tool.engraved.glyphs == []
    assert "새김 도구" in scene.note


def test_an_unknown_glyph_cannot_be_carved_even_by_calling_straight_in():
    scene = PlayScene()
    _ready_to_carve(scene)
    unknown = glyph_table.SNOWFIELD_GLYPHS[0]
    scene.carve(unknown)
    assert scene.hotbar.active_tool.engraved.glyphs == []
    assert scene.hotbar.count(ITEM_KINDS["chisel"]) == 1  # nothing spent either


def test_the_rows_list_refusals_rather_than_hiding_them():
    # Hidden, the player cannot tell a lost drawing from a wrong thing held.
    scene = PlayScene()
    _ready_to_carve(scene)
    swift = glyph_table.LESSER_SWIFT
    scene.grimoire.learn(swift)
    assert len(scene.carve_rows()) == 2


def test_holding_a_pickaxe_offers_nothing_to_carve():
    scene = PlayScene()
    scene.grimoire.learn(glyph_table.VOLCANO_GLYPHS[0])
    scene.hotbar.select(0)
    scene.hotbar.slots[0] = Stack(ITEM_KINDS["stone_pick"], 1)
    assert scene.carve_target is None
    assert scene.carve_rows() == []
    assert "새길 수 없" in scene.carve_header()


def test_the_carving_screen_pauses_the_world_like_the_others():
    scene = PlayScene()
    scene.core.ignite()
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_g))
    assert scene.carve_open
    where = pygame.Vector2(scene.player.pos)
    scene.update(config.FIXED_DT)
    assert scene.player.pos == where


def test_only_one_screen_at_a_time():
    scene = PlayScene()
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_g))
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c))
    assert scene.craft_open and not scene.carve_open
