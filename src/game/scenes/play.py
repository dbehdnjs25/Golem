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
from game.entities.loot import LootPile
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.inventory import grid, packs
from game.inventory.grid import Grid
from game.inventory.hotbar import Hotbar
from game.inventory.stack import Stack
from game.inventory.storage import Container
from game.items.item_kinds import CORE_SHARD, WORN_PACK, ItemKind
from game.items.tools import MiningTool, WeaponTool
from game.systems import combat, mining, survival
from game.systems.camera import LOCKED, Camera
from game.systems.daynight import DayNight
from game.systems.enemy_spawner import EnemySpawner
from game.systems.spawn_common import near_player
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
        self.clock = DayNight()
        self.player = Player(pos=pygame.Vector2(center))
        self.camera = Camera(
            offset=pygame.Vector2(0, 0),
            view_size=config.SCREEN_SIZE,
            world_size=config.WORLD_SIZE,
            mode=LOCKED,
        )
        self.camera.center_on(self.player.pos)
        # No base inventory: without a pack the hotbar is all there is.
        self.backpack: Container | None = None
        self.worn_pack: ItemKind | None = None  # which pack, so a death can drop it
        self.loot: list[LootPile] = []  # several may be outstanding at once
        self.grid = Grid()
        self.grid_open = False
        self.store = Container.empty(config.CORE_STORE_SLOTS)
        self.hotbar = Hotbar.create()
        # slot 0 mines (key "1"); slot 1 shoots (key "2").
        self.hotbar.slots[0] = MiningTool()
        self.hotbar.slots[1] = WeaponTool()
        self.fragments: list[Fragment] = []
        self.spawner = Spawner()
        self._scatter_starting_shards()

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

    def _scatter_starting_shards(self) -> None:
        """Seed the pedestal's surroundings with the shards that light the core.

        They sit within reach of the spawn on purpose: the opening should be a
        short errand, not a search. Placing the core is what starts day one, and
        the player chooses when.
        """
        for _ in range(config.CORE_SHARDS_TO_IGNITE + 2):  # two spare
            spot = near_player(self.player.pos, self.rng, self.world)
            if spot is not None:
                self.fragments.append(Fragment(pos=spot, kind=CORE_SHARD))
        # SCAFFOLDING until crafting lands in step 5: one worn pack out in the
        # grass, so the backpack can be exercised before it can be made.
        spot = near_player(self.player.pos, self.rng, self.world)
        if spot is not None:
            self.fragments.append(Fragment(pos=spot, kind=WORN_PACK))

    def _wear_if_pack(self, kind: ItemKind | None) -> None:
        """A pack is worn the moment it is dug up -- it is what holds things.

        A bigger one replaces a smaller one. Swapping without losing what was
        inside is the grid screen's job.
        """
        if kind is None or not packs.is_pack(kind):
            return
        if self.backpack is None or packs.slots_of(kind) > self.backpack.size:
            self.backpack = Container.empty(packs.slots_of(kind))
            self.worn_pack = kind

    def _tick_loot(self, dt: float) -> None:
        """Run every pile's clock down and clear the ones that ran out.

        Called before the respawn wait returns, because a deadline that pauses
        while the player is dead is not a deadline.
        """
        for pile in self.loot:
            pile.update(dt)
        self.loot = [pile for pile in self.loot if not pile.is_gone]

    def _recover_underfoot(self) -> None:
        """Pick up any pile the player is standing on."""
        for pile in list(self.loot):
            if self.player.pos.distance_to(pile.pos) <= config.LOOT_PICKUP_RADIUS:
                self._recover(pile)

    def _recover(self, pile: LootPile) -> None:
        """Take back what a death left, if it will fit."""
        if self.backpack is None:
            self.backpack, self.worn_pack = pile.contents, pile.pack
        else:
            for kind, n in pile.contents.rows():
                pile.contents.remove(kind, self.backpack.add(kind, n))
            if pile.contents.used:
                return  # a smaller pack cannot hold it all -- leave the rest
        self.loot.remove(pile)

    def _carried(self, kind: ItemKind) -> int:
        """How many of ``kind`` the player has on them, wherever it sits."""
        in_pack = self.backpack.count(kind) if self.backpack is not None else 0
        return in_pack + self.hotbar.count(kind)

    def _spend(self, kind: ItemKind, n: int) -> int:
        """Take ``n`` from the backpack first, then the hotbar."""
        taken = self.backpack.remove(kind, n) if self.backpack is not None else 0
        return taken + self.hotbar.remove(kind, n - taken)

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
            elif event.key == pygame.K_i:
                self._toggle_grid()
            elif event.key == pygame.K_ESCAPE and self.manager is not None:
                self.manager.pop()
        elif event.type == pygame.KEYUP:
            self._held_keys.discard(event.key)
        elif event.type == pygame.MOUSEMOTION:
            self._mouse_screen = pygame.Vector2(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.grid_open:
                self._click_grid(pygame.Vector2(event.pos))
                return
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

        self.clock.update(dt)
        self._tick_loot(dt)

        if self.grid_open:
            return  # the world waits while the belongings are open

        down = self._respawn_timer > 0
        if down:
            self._respawn_timer -= dt
            if self._respawn_timer <= 0:
                self.player.pos = pygame.Vector2(self.core.pos)
                self.player.hp = self.player.max_hp
                self.player.iframe_timer = config.RESPAWN_IFRAMES
                down = False

        # The camera keeps following even while down, so the wait shows the
        # world carrying on rather than a frozen frame.
        self.camera.update(dt, self.player.pos, self._mouse_screen, self._mouse_held)

        if not down:
            self._update_living(dt, dodge, sync)

        # The world does not stop for a death: golems keep walking, shots keep
        # flying, and what was chasing the player is still out there on the way
        # back. Only the player's own half of the step waits.
        combat.update_projectiles(dt, self.projectiles, self.enemies, self.world)
        combat.update_enemies(dt, self.enemies, self.player, self.world, self.core)
        self.spawner.update(dt, self.fragments, self.core, self.rng, self.world, self.player.pos)
        self.enemy_spawner.update(
            dt, self.enemies, self.player.pos, self.core, self.rng, self.world
        )

        if not down and self.player.hp <= 0:
            # Piles accumulate; each runs out on its own clock rather than
            # being erased by the next death. The deadline is the pressure.
            dropped = combat.apply_death_penalty(self.player.pos, self.backpack, self.worn_pack)
            if dropped is not None:
                self.loot.append(dropped)
            self.backpack = None
            self.worn_pack = None
            self._respawn_timer = config.RESPAWN_DELAY

    def _update_living(self, dt: float, dodge: bool, sync: bool) -> None:
        """The half of a step that only happens while the player is on their feet."""
        self.player.update(dt, self._move_dir(), self.world, dodge)
        aim_world = self.camera.screen_to_world(self._mouse_screen)

        tool = self.hotbar.active_tool
        _, mined = mining.update_mining(
            dt,
            active_tool=tool,
            held=self._mouse_held,
            aim_world=aim_world,
            player_pos=self.player.pos,
            fragments=self.fragments,
            backpack=self.backpack,
            hotbar=self.hotbar,
        )
        self._wear_if_pack(mined)
        self._fire_timer, shots = combat.fire_weapon(
            dt,
            weapon=tool,
            held=self._mouse_held,
            aim_world=aim_world,
            player_pos=self.player.pos,
            fire_timer=self._fire_timer,
        )
        self.projectiles.extend(shots)
        survival.update_regen(dt, self.player, self.core)

        if sync and self.core.is_in_sync_range(self.player.pos):
            if self.core.ignited:
                moved = self.store.add(CORE_SHARD, self._carried(CORE_SHARD))
                self._spend(CORE_SHARD, moved)
            elif self._carried(CORE_SHARD) >= config.CORE_SHARDS_TO_IGNITE:
                self._spend(CORE_SHARD, config.CORE_SHARDS_TO_IGNITE)
                self.core.ignite()

        self._recover_underfoot()

    # --- rendering -------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        self._draw_world(surface)
        self._draw_ward(surface)
        self._draw_temples(surface)
        self._draw_loot(surface)
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
        self._draw_night(surface)
        self._draw_hud(surface)
        self._draw_grid(surface)

    # --- the belongings screen -------------------------------------------
    def _toggle_grid(self) -> None:
        self.grid_open = not self.grid_open
        if not self.grid_open:
            self.grid.close(self.backpack, self.hotbar)

    def _grid_origin(self) -> tuple[int, int]:
        """Top-left of the pack grid. The hotbar row sits one gap below it."""
        step = config.GRID_CELL + config.GRID_GAP
        rows = self._pack_rows()
        width = config.GRID_COLS * step - config.GRID_GAP
        height = (rows + 1) * step + config.GRID_GAP  # +1 for the hotbar row
        return (config.SCREEN_WIDTH - width) // 2, (config.SCREEN_HEIGHT - height) // 2

    def _pack_rows(self) -> int:
        size = self.backpack.size if self.backpack is not None else 0
        return -(-size // config.GRID_COLS)  # ceiling division

    def _cell_rect(self, row: int, col: int) -> pygame.Rect:
        step = config.GRID_CELL + config.GRID_GAP
        x, y = self._grid_origin()
        return pygame.Rect(x + col * step, y + row * step, config.GRID_CELL, config.GRID_CELL)

    def _click_grid(self, where: pygame.Vector2) -> None:
        """Turn a screen point into a slot and hand it to the pure Grid."""
        rows = self._pack_rows()
        for row in range(rows):
            for col in range(config.GRID_COLS):
                index = row * config.GRID_COLS + col
                if self.backpack is not None and index >= self.backpack.size:
                    break
                if self._cell_rect(row, col).collidepoint(where):
                    self.grid.click(grid.PACK, index, self.backpack, self.hotbar)
                    return
        for col in range(len(self.hotbar.slots)):
            if self._cell_rect(rows + 1, col).collidepoint(where):  # +1 leaves a gap
                self.grid.click(grid.HOTBAR, col, self.backpack, self.hotbar)
                return

    def _draw_grid(self, surface: pygame.Surface) -> None:
        """The pack above, the hotbar below, and whatever is in hand on top."""
        if not self.grid_open:
            return
        rows = self._pack_rows()
        panel = pygame.Rect(0, 0, *config.SCREEN_SIZE).inflate(-80, -80)
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))
        pygame.draw.rect(surface, config.GRID_PANEL, panel, border_radius=6)

        for row in range(rows):
            for col in range(config.GRID_COLS):
                index = row * config.GRID_COLS + col
                if self.backpack is None or index >= self.backpack.size:
                    break
                self._draw_cell(surface, self._cell_rect(row, col), self.backpack.slots[index])
        for col, slot in enumerate(self.hotbar.slots):
            rect = self._cell_rect(rows + 1, col)
            self._draw_cell(surface, rect, slot)
            if col == self.hotbar.selected:
                pygame.draw.rect(surface, config.WHITE, rect.inflate(6, 6), 2)

        held = self.grid.held
        if held is not None:
            at = pygame.Rect(0, 0, config.GRID_CELL - 10, config.GRID_CELL - 10)
            at.center = (int(self._mouse_screen.x), int(self._mouse_screen.y))
            self._draw_contents(surface, at, held)

    def _draw_cell(self, surface: pygame.Surface, rect: pygame.Rect, slot: object) -> None:
        pygame.draw.rect(surface, (58, 58, 74), rect, border_radius=3)
        pygame.draw.rect(surface, (90, 90, 110), rect, 1, border_radius=3)
        if slot is not None:
            self._draw_contents(surface, rect.inflate(-10, -10), slot)

    def _draw_contents(self, surface: pygame.Surface, rect: pygame.Rect, slot: object) -> None:
        """A coloured block stands in for an icon until there is art.

        A stack shows its kind's colour; a tool shows a neutral one, since tools
        are not catalogue rows and have no colour of their own.
        """
        if isinstance(slot, Stack):
            pygame.draw.rect(surface, slot.kind.color, rect, border_radius=2)
            filled = max(1, int(rect.width * slot.count / slot.kind.stack_max))
            pygame.draw.rect(
                surface, config.WHITE, pygame.Rect(rect.left, rect.bottom - 3, filled, 3)
            )
        else:
            pygame.draw.rect(surface, (200, 200, 215), rect, border_radius=2)

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

    def _draw_ward(self, surface: pygame.Surface) -> None:
        """The ward's rim, or the bare pedestal before the core is lit."""
        center = self.camera.world_to_screen(self.core.pos)
        if not self.core.ignited:
            pygame.draw.circle(surface, config.PEDESTAL_COLOR, center, self.core.radius, 3)
            return
        pygame.draw.circle(surface, config.WARD_COLOR, center, self.core.ward_radius, 2)

    def _draw_night(self, surface: pygame.Surface) -> None:
        """Darken everything outside the ward once night falls.

        Drawn before the HUD so the gauges stay readable, and punched through
        inside the ward so the safe ground reads as safe at a glance.
        """
        if not self.clock.is_night:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 20, config.NIGHT_DARKNESS))
        if self.core.ignited:
            pygame.draw.circle(
                overlay,
                (0, 0, 0, 0),
                self.camera.world_to_screen(self.core.pos),
                self.core.ward_radius,
            )
        surface.blit(overlay, (0, 0))

    def _draw_loot(self, surface: pygame.Surface) -> None:
        """Everything a death took, sitting where it happened.

        A pile shrinks as its clock runs down, so how long is left is readable
        from across the field rather than only from a number somewhere.
        """
        for pile in self.loot:
            left = pile.ttl / config.LOOT_LIFETIME
            pygame.draw.circle(
                surface,
                config.LOOT_COLOR,
                self.camera.world_to_screen(pile.pos),
                max(4.0, config.LOOT_RADIUS * left),
            )

    def _draw_temples(self, surface: pygame.Surface) -> None:
        """Placeholder markers so the five sites are visible before temples exist."""
        for site in self.temple_sites:
            pygame.draw.circle(surface, config.WHITE, self.camera.world_to_screen(site), 9, 3)

    def _draw_hud(self, surface: pygame.Surface) -> None:
        # inventory fill gauge
        pack = self.backpack
        frac = pack.used / pack.size if pack is not None and pack.size else 0.0
        _draw_bar(surface, 10, 14, frac, (90, 200, 120))
        # hp bar
        hp_frac = max(0.0, self.player.hp / self.player.max_hp) if self.player.max_hp else 0.0
        _draw_bar(surface, 30, 14, hp_frac, config.HP_COLOR)
        # dodge cooldown strip (full = ready)
        ready = 1 - self.player.dodge_cooldown_timer / config.DODGE_COOLDOWN
        _draw_bar(surface, 48, 5, ready, (120, 160, 220), bg=(40, 40, 55))
        # day/night progress: warm across the day, cold across the night
        phase_color = (90, 110, 200) if self.clock.is_night else (240, 220, 130)
        _draw_bar(surface, 62, 5, self.clock.phase_fraction, phase_color, bg=(40, 40, 55))
        # hotbar (bottom-left). Hidden while the belongings screen is open,
        # which draws its own -- two hotbars on screen reads as two hotbars.
        if self.grid_open:
            return
        for i in range(len(self.hotbar.slots)):
            x = 10 + i * 44
            color = config.WHITE if i == self.hotbar.selected else (120, 120, 140)
            pygame.draw.rect(surface, color, pygame.Rect(x, surface.get_height() - 50, 40, 40), 2)
