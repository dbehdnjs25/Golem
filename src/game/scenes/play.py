"""Core-loop gameplay scene: mine fragments, fill the backpack, return to the
core and press E to sync into /Documents. Wires the entities and systems
together; accumulates input from events (no polling) and owns all rendering."""

from __future__ import annotations

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
from game.inventory.storage import Folder
from game.items.item_kinds import FRAGMENT
from game.items.tools import MiningTool, WeaponTool
from game.systems import combat, mining
from game.systems.camera import LOCKED, Camera
from game.systems.enemy_spawner import EnemySpawner
from game.systems.spawner import Spawner

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
        center = pygame.Vector2(config.WORLD_WIDTH / 2, config.WORLD_HEIGHT / 2)
        self.core = Core(pos=pygame.Vector2(center))
        self.player = Player(pos=pygame.Vector2(center))
        self.camera = Camera(
            offset=pygame.Vector2(0, 0),
            view_size=config.SCREEN_SIZE,
            world_size=config.WORLD_SIZE,
            mode=LOCKED,
        )
        self.camera.center_on(self.player.pos)
        self.backpack = Folder(cap_mb=config.BACKPACK_CAP_MB)
        self.documents = Folder(cap_mb=config.DOCUMENTS_CAP_MB)
        self.hotbar = Hotbar.create()
        # slot 0 mines (key "1"); slot 1 shoots (key "2").
        self.hotbar.slots[0] = MiningTool()
        self.hotbar.slots[1] = WeaponTool()
        self.fragments: list[Fragment] = []
        self.spawner = Spawner()
        self.rng = random.Random(1234)

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

        self.player.update(dt, self._move_dir(), config.WORLD_SIZE, dodge)
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
        combat.update_projectiles(dt, self.projectiles, self.enemies, config.WORLD_SIZE)
        combat.update_enemies(dt, self.enemies, self.player, config.WORLD_SIZE)

        new_fragment = self.spawner.update(dt, self.fragments, self.core, self.rng)
        if new_fragment is not None and self.rng.random() < config.TROJAN_CHANCE:
            new_fragment.on_depleted = self._hatch_golem
        self.enemy_spawner.update(dt, self.enemies, self.player.pos, self.core, self.rng)

        if sync and self.core.is_in_sync_range(self.player.pos):
            moved = self.documents.add(FRAGMENT, self.backpack.count(FRAGMENT))
            self.backpack.remove(FRAGMENT, moved)

        if self.player.hp <= 0:
            combat.apply_death_penalty(self.backpack)
            self._respawn_timer = config.RESPAWN_DELAY

    def _hatch_golem(self, fragment: Fragment) -> None:
        """Trojan payload: mining this fragment out releases a golem in its place."""
        self.enemies.append(Golem(pos=pygame.Vector2(fragment.pos)))

    # --- rendering -------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(config.BACKGROUND)
        self._draw_floor(surface)
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

    def _draw_floor(self, surface: pygame.Surface) -> None:
        view_w, view_h = surface.get_size()
        tile = config.TILE_SIZE
        off_x, off_y = int(self.camera.offset.x), int(self.camera.offset.y)
        first_col, first_row = off_x // tile, off_y // tile
        for row in range(first_row, (off_y + view_h) // tile + 1):
            for col in range(first_col, (off_x + view_w) // tile + 1):
                color = config.FLOOR_A if (row + col) % 2 == 0 else config.FLOOR_B
                pygame.draw.rect(
                    surface, color, pygame.Rect(col * tile - off_x, row * tile - off_y, tile, tile)
                )

    def _draw_hud(self, surface: pygame.Surface) -> None:
        # backpack fill gauge
        frac = self.backpack.used_mb / self.backpack.cap_mb if self.backpack.cap_mb else 0.0
        _draw_bar(surface, 10, 14, frac, (90, 200, 120))
        # hp bar
        hp_frac = max(0.0, self.player.hp / self.player.max_hp) if self.player.max_hp else 0.0
        _draw_bar(surface, 30, 14, hp_frac, config.HP_COLOR)
        # dodge cooldown strip (full = ready)
        ready = 1 - self.player.dodge_cooldown_timer / config.DODGE_COOLDOWN
        _draw_bar(surface, 48, 5, ready, (120, 160, 220), bg=(40, 40, 55))
        # hotbar (bottom-left), only unlocked slots
        for i in range(self.hotbar.unlocked):
            x = 10 + i * 44
            color = config.WHITE if i == self.hotbar.selected else (120, 120, 140)
            pygame.draw.rect(surface, color, pygame.Rect(x, surface.get_height() - 50, 40, 40), 2)
