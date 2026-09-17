"""Core-loop gameplay scene: mine shards, fill the inventory, return to the core
and press E to move them into its store. Wires the entities and systems
together; accumulates input from events (no polling) and owns all rendering."""

from __future__ import annotations

import math
import random

import pygame

from game import config
from game.core.scene import Scene
from game.entities.core import Core
from game.entities.enemy import Golem
from game.entities.fragment import Fragment
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.inventory.hotbar import Hotbar
from game.inventory.storage import Container
from game.items.item_kinds import CORE_SHARD
from game.items.tools import MiningTool, WeaponTool
from game.systems import combat, mining
from game.systems.camera import LOCKED, Camera
from game.systems.enemy_spawner import EnemySpawner
from game.systems.spawner import Spawner
from game.world import biomes
from game.world.map import WorldMap

_MOVE_KEYS = {pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d}

# HUD gauges: same left edge and width, stacked down the top-left corner.
_BAR_X = 10
_BAR_W = 120
_BAR_BG = (60, 60, 80)


def _draw_bar(
    surface: pygame.Surface,
    y: int,
    height: int,
    frac: float,
    color: tuple[int, int, int],
    bg: tuple[int, int, int] = _BAR_BG,
) -> None:
    """A left-anchored gauge filled to ``frac`` (0..1) of its width."""
    pygame.draw.rect(surface, bg, pygame.Rect(_BAR_X, y, _BAR_W, height))
    pygame.draw.rect(surface, color, pygame.Rect(_BAR_X, y, int(_BAR_W * frac), height))


class PlayScene(Scene):
    def __init__(self) -> None:
        self.rng = random.Random(1234)
        self.world = WorldMap.create(self.rng)
        self.temple_sites = self.world.temple_sites(self.rng)
        center = self.world.center
        self.core = Core(pos=pygame.Vector2(center))
        self.player = Player(pos=pygame.Vector2(center))
        self.camera = Camera(
            offset=pygame.Vector2(0, 0),
            view_size=config.SCREEN_SIZE,
            world_size=config.WORLD_SIZE,
            mode=LOCKED,
        )
        self.camera.center_on(self.player.pos)
        self.backpack = Container(slots=config.INVENTORY_SLOTS)
        self.store = Container(slots=config.CORE_STORE_SLOTS)
        self.hotbar = Hotbar.create()
        # slot 0 mines (key "1"); slot 1 shoots (key "2").
        self.hotbar.slots[0] = MiningTool()
        self.hotbar.slots[1] = WeaponTool()
        self.fragments: list[Fragment] = []
        self.spawner = Spawner()

        self.enemies: list[Golem] = []
        self.projectiles: list[Projectile] = []
        self.enemy_spawner = EnemySpawner()
        self._fire_timer = 0.0
        self._dodge_pressed = False
        self._sync_pressed = False
        self._respawn_timer = 0.0

        self._held_keys: set[int] = set()
        self._mouse_screen = pygame.Vector2(config.SCREEN_WIDTH / 2, config.SCREEN_HEIGHT / 2)
        self._mouse_held = False

    # --- input (event-driven, no polling) --------------------------------
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in _MOVE_KEYS:
                self._held_keys.add(event.key)
            elif event.key == pygame.K_1:
                self.hotbar.select(0)
            elif event.key == pygame.K_2:
                self.hotbar.select(1)
            elif event.key == pygame.K_y:
                self.camera.toggle_lock(self.player.pos)
            elif event.key == pygame.K_SPACE:
                self._dodge_pressed = True
            elif event.key == pygame.K_e:
                self._sync_pressed = True
            elif event.key == pygame.K_ESCAPE and self.manager is not None:
                self.manager.pop()
        elif event.type == pygame.KEYUP:
            self._held_keys.discard(event.key)
        elif event.type == pygame.MOUSEMOTION:
            self._mouse_screen = pygame.Vector2(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._mouse_held = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._mouse_held = False

    def _move_dir(self) -> pygame.Vector2:
        direction = pygame.Vector2(0, 0)
        if pygame.K_w in self._held_keys:
            direction.y -= 1
        if pygame.K_s in self._held_keys:
            direction.y += 1
        if pygame.K_a in self._held_keys:
            direction.x -= 1
        if pygame.K_d in self._held_keys:
            direction.x += 1
        return direction

    # --- logic -----------------------------------------------------------
    def update(self, dt: float) -> None:
        # consumed once per step whether or not we are dead, so a press during
        # the respawn wait cannot queue up an action for the frame we come back
        dodge = self._dodge_pressed
        sync = self._sync_pressed
        self._dodge_pressed = False
        self._sync_pressed = False

        if self._respawn_timer > 0:
            self._respawn_timer -= dt
            if self._respawn_timer <= 0:
                self.player.pos = pygame.Vector2(self.core.pos)
                self.player.hp = self.player.max_hp
                self.player.iframe_timer = config.RESPAWN_IFRAMES
            return

        self.player.update(dt, self._move_dir(), self.world, dodge)
        self.camera.update(dt, self.player.pos, self._mouse_screen, self._mouse_held)
        aim_world = self.camera.screen_to_world(self._mouse_screen)

        tool = self.hotbar.active_tool
        mining.update_mining(
            dt,
            active_tool=tool,
            held=self._mouse_held,
            aim_world=aim_world,
            player_pos=self.player.pos,
            fragments=self.fragments,
            backpack=self.backpack,
        )
        self._fire_timer, shots = combat.fire_weapon(
            dt,
            weapon=tool,
            held=self._mouse_held,
            aim_world=aim_world,
            player_pos=self.player.pos,
            fire_timer=self._fire_timer,
        )
        self.projectiles.extend(shots)
        combat.update_projectiles(dt, self.projectiles, self.enemies, self.world)
        combat.update_enemies(dt, self.enemies, self.player, self.world, self.core)

        self.spawner.update(dt, self.fragments, self.core, self.rng, self.world, self.player.pos)
        self.enemy_spawner.update(
            dt, self.enemies, self.player.pos, self.core, self.rng, self.world
        )

        if sync and self.core.is_in_sync_range(self.player.pos):
            moved = self.store.add(CORE_SHARD, self.backpack.count(CORE_SHARD))
            self.backpack.remove(CORE_SHARD, moved)

        if self.player.hp <= 0:
            combat.apply_death_penalty(self.backpack)
            self._respawn_timer = config.RESPAWN_DELAY

    # --- rendering -------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        self._draw_world(surface)
        self._draw_temples(surface)
        for fragment in self.fragments:
            pygame.draw.circle(
                surface,
                config.FRAGMENT_COLOR,
                self.camera.world_to_screen(fragment.pos),
                config.FRAGMENT_RADIUS,
            )
        for enemy in self.enemies:
            pygame.draw.circle(
                surface,
                config.GOLEM_COLOR,
                self.camera.world_to_screen(enemy.pos),
                enemy.radius,
            )
        for shot in self.projectiles:
            pygame.draw.circle(
                surface,
                config.PROJECTILE_COLOR,
                self.camera.world_to_screen(shot.pos),
                shot.radius,
            )
        pygame.draw.circle(
            surface, config.CORE_COLOR, self.camera.world_to_screen(self.core.pos), self.core.radius
        )
        pygame.draw.circle(
            surface,
            config.PLAYER_COLOR,
            self.camera.world_to_screen(self.player.pos),
            self.player.radius,
        )
        self._draw_hud(surface)

    def _draw_world(self, surface: pygame.Surface) -> None:
        """Paint the map: void, then one wedge per ring biome, then the grassland.

        Flat colours until real tiles exist. Wedges rather than tiles because the
        biomes ARE angular sectors -- five polygons draw them exactly, in seven
        calls a frame instead of the five hundred a tile grid costs, with no
        stair-stepping and no per-tile biome lookup.
        """
        surface.fill(config.VOID_COLOR)
        center = self.camera.world_to_screen(self.world.center)
        steps = 24  # arc samples per wedge; the chord error is under a pixel
        for index, biome in enumerate(biomes.RING_BIOMES):
            start = self.world.rotation + index * self.world.sector_degrees
            points = [center]
            for step in range(steps + 1):
                angle = math.radians(start + self.world.sector_degrees * step / steps)
                points.append(
                    center + pygame.Vector2(math.cos(angle), math.sin(angle)) * self.world.radius
                )
            pygame.draw.polygon(surface, biome.color, points)
        pygame.draw.circle(surface, biomes.GRASSLAND.color, center, self.world.grassland_radius)

    def _draw_temples(self, surface: pygame.Surface) -> None:
        """Placeholder markers so the five sites are visible before temples exist."""
        for site in self.temple_sites:
            pygame.draw.circle(surface, config.WHITE, self.camera.world_to_screen(site), 9, 3)

    def _draw_hud(self, surface: pygame.Surface) -> None:
        # inventory fill gauge
        frac = self.backpack.slots_used / self.backpack.slots if self.backpack.slots else 0.0
        _draw_bar(surface, 10, 14, frac, (90, 200, 120))
        # hp bar
        hp_frac = max(0.0, self.player.hp / self.player.max_hp) if self.player.max_hp else 0.0
        _draw_bar(surface, 30, 14, hp_frac, config.HP_COLOR)
        # dodge cooldown strip (full = ready)
        ready = 1 - self.player.dodge_cooldown_timer / config.DODGE_COOLDOWN
        _draw_bar(surface, 48, 5, ready, (120, 160, 220), bg=(40, 40, 55))
        # hotbar (bottom-left)
        for i in range(len(self.hotbar.slots)):
            x = 10 + i * 44
            color = config.WHITE if i == self.hotbar.selected else (120, 120, 140)
            pygame.draw.rect(surface, color, pygame.Rect(x, surface.get_height() - 50, 40, 40), 2)
