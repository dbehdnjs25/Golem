"""Core-loop gameplay scene: mine shards, fill the inventory, return to the core
and press E to move them into its store. Wires the entities and systems
together; accumulates input from events (no polling) and owns all rendering."""

from __future__ import annotations

import math
import random

import pygame

from game import config
from game.core.scene import Scene
from game.entities.beast import Beast
from game.entities.core import Core
from game.entities.enemy import Creature, Golem
from game.entities.fragment import Fragment
from game.entities.loot import LootPile
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.entities.station import Station, place, stations_at
from game.inventory import grid, packs
from game.inventory.grid import Grid
from game.inventory.hotbar import Hotbar
from game.inventory.stack import Stack
from game.inventory.storage import Container
from game.items import engraving, grades
from game.items.engraving import Engraved
from game.items.glyphs import Glyph
from game.items.item_kinds import (
    CHISEL,
    CORE_SHARD,
    GRASS,
    PEBBLE,
    STONE,
    TWIG,
    WOOD,
    ItemKind,
)
from game.items.recipes import STATION_OF, Recipe
from game.items.staff import STAFF_KINDS, Staff
from game.items.tools import BARE_HAND, MiningTool, WeaponTool
from game.systems import carrying, combat, crafting, mining, raids, survival
from game.systems.beast_spawner import BeastSpawner
from game.systems.camera import LOCKED, Camera, edge_marker
from game.systems.daynight import DayNight
from game.systems.enemy_spawner import EnemySpawner
from game.systems.grimoire import Grimoire
from game.systems.spawn_common import near_player
from game.systems.spawner import Spawner
from game.world import biomes, structures
from game.world.map import WorldMap

_MOVE_KEYS = {pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d}

# Korean first, since every item name is Korean; the fallbacks are only so a
# machine without these still draws something rather than raising.
_FONT_NAMES = ("malgungothic", "gulim", "arial")
_fonts: dict[int, pygame.font.Font] = {}


def _font(size: int) -> pygame.font.Font:
    """A cached font. Built on first use so importing this module needs no display."""
    cached = _fonts.get(size)
    if cached is not None:
        return cached
    for name in _FONT_NAMES:
        try:
            made = pygame.font.SysFont(name, size)
        except Exception:  # noqa: BLE001 - any font failure just means try the next
            continue
        if made.render("가", True, (255, 255, 255)).get_width() > 2:
            _fonts[size] = made
            return made
    _fonts[size] = pygame.font.Font(None, size)
    return _fonts[size]


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
        self.defeated = False
        self.grimoire = Grimoire()
        self.note = ""  # a line that fades; see _say
        self.note_left = 0.0
        # Cuts left on the chisel in hand. On the scene rather than on the item
        # because a stack of chisels is a stack of FRESH ones -- only the one
        # actually being used is part-worn.
        self.chisel_left = config.CHISEL_USES
        # One staff, upgraded in place. The item in a slot is a token for it, the
        # same way the chisel's remaining cuts live here: what matters about a
        # staff is what is carved on it, and that cannot ride in a Stack.
        self.staff = Staff()
        self.structures = structures.place(self.world, self.rng)
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
        self.stations: list[Station] = []
        self.grid = Grid()
        self.grid_open = False
        self.craft_open = False
        self.carve_open = False
        self.store = Container.empty(config.CORE_STORE_SLOTS)
        self.hotbar = Hotbar.create()
        # Nothing but the weapon. Wood comes off a tree with bare hands, and the
        # first axe is crafted from it -- the opening is a thing the player does
        # rather than a kit they are handed.
        self.hotbar.slots[4] = WeaponTool()
        self.fragments: list[Fragment] = []
        self.spawner = Spawner()
        self._scatter_starting_shards()

        self.enemies: list[Golem] = []
        self.projectiles: list[Projectile] = []
        self.enemy_spawner = EnemySpawner()
        self.beasts: list[Beast] = []
        self.beast_spawner = BeastSpawner()
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
        # Litter first, then trees. A player holding nothing can only take the
        # litter, and the crude axe it makes is what opens the trees -- so the
        # first five minutes have an order to them rather than a wall.
        for kind, count in ((TWIG, 6), (PEBBLE, 4), (GRASS, 6), (WOOD, 6)):
            for _ in range(count):
                spot = near_player(self.player.pos, self.rng, self.world)
                if spot is not None:
                    self.fragments.append(Fragment(pos=spot, kind=kind))

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
            elif event.key == pygame.K_3:
                self.hotbar.select(2)
            elif event.key == pygame.K_4:
                self.hotbar.select(3)
            elif event.key == pygame.K_5:
                self.hotbar.select(4)
            elif event.key == pygame.K_y:
                self.camera.toggle_lock(self.player.pos)
            elif event.key == pygame.K_SPACE:
                self._dodge_pressed = True
            elif event.key == pygame.K_e:
                self._sync_pressed = True
            elif event.key == pygame.K_i:
                self._toggle_grid()
            elif event.key == pygame.K_c:
                self._toggle_craft()
            elif event.key == pygame.K_g:
                self._toggle_carve()
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
            if self.craft_open:
                self._click_craft(pygame.Vector2(event.pos))
                return
            if self.carve_open:
                self._click_carve(pygame.Vector2(event.pos))
                return
            if self._try_place(pygame.Vector2(event.pos)):
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
        self.note_left = max(0.0, self.note_left - dt)
        # A signal and nothing more. What a run does about losing its core is
        # the ending's business, and the ending is still being designed.
        self.defeated = self.defeated or self.core.is_destroyed
        self._tick_loot(dt)
        for station in self.stations:
            station.update(dt)

        if self.grid_open or self.craft_open or self.carve_open:
            return  # the world waits while a screen is open

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
        combat.update_enemies(
            dt, self.enemies, self.player, self.world, self.core, raid=self.is_raid
        )
        self.spawner.update(dt, self.fragments, self.core, self.rng, self.world, self.player.pos)
        self.enemy_spawner.update(
            dt, self.enemies, self.player.pos, self.core, self.rng, self.world, raid=self.is_raid
        )
        self.beast_spawner.update(
            dt,
            self.beasts,
            self.player.pos,
            self.core,
            self.rng,
            self.world,
            night=self.clock.is_night,
        )
        combat.update_beasts(
            dt, self.beasts, self.player, self.world, self.core, self.rng, self.fragments
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

    @property
    def is_raid(self) -> bool:
        """Whether the ward is open tonight.

        Only ever at night. A raid is a night the wall comes down, and one
        running through the afternoon would make the word meaningless.
        """
        return self.clock.is_night and raids.is_raid_night(self.clock.day, self.core.bosses_killed)

    @property
    def days_to_raid(self) -> int:
        return raids.days_until(self.clock.day, self.core.bosses_killed)

    @property
    def ward_colour(self) -> tuple[int, int, int]:
        """Red on a raid night. The wall being down has to read from inside."""
        return config.WARD_BROKEN_COLOR if self.is_raid else config.WARD_COLOR

    @property
    def calendar_line(self) -> str:
        """What day it is and how long until the next raid.

        The spec's shortening cycle only means something if the player can
        count it; unreadable, it is just the occasional bad night.
        """
        left = self.days_to_raid
        when = "습격 오늘 밤" if left == 0 else f"습격까지 {left}일"
        return f"{self.clock.day}일차 · {when}"

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
        if self.holding_staff:
            self._fire_timer, shots = combat.fire_staff(
                dt,
                staff=self.staff,
                held=self._mouse_held,
                aim_world=aim_world,
                player_pos=self.player.pos,
                fire_timer=self._fire_timer,
            )
        else:
            # Cooling even while slung. A staff put away to swing something
            # else should not come back out exactly as hot as it went in.
            self.staff.update(dt)
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

        if sync:
            self._open_structure()
        if sync and self.core.is_in_sync_range(self.player.pos):
            if self.core.ignited:
                # Mending first. The same key already means "deal with the
                # core", and after a raid the urgent business is the cracks.
                self._spend(STONE, self.core.repair(self._carried(STONE)))
                moved = self.store.add(CORE_SHARD, self._carried(CORE_SHARD))
                self._spend(CORE_SHARD, moved)
            elif self._carried(CORE_SHARD) >= config.CORE_SHARDS_TO_IGNITE:
                self._spend(CORE_SHARD, config.CORE_SHARDS_TO_IGNITE)
                self.core.ignite()

        self._recover_underfoot()
        self._collect_stations()
        self._gather_underfoot()

    # --- rendering -------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        self._draw_world(surface)
        self._draw_ward(surface)
        self._draw_temples(surface)
        self._draw_structures(surface)
        self._draw_stations(surface)
        self._draw_nodes(surface)
        # Night falls on the GROUND. Everything alive, everything in flight and
        # everything on a clock is drawn over it, because a wolf you cannot
        # tell from yourself is not atmosphere, it is a lost fight -- and a
        # loot pile with five minutes left should not be hidden by the hour.
        self._draw_night(surface)
        self._draw_loot(surface)
        on_field: tuple[Creature, ...] = (*self.enemies, *self.beasts)
        for creature in on_field:
            pygame.draw.circle(
                surface,
                creature.color,  # from its kind, so each sort reads differently
                self.camera.world_to_screen(creature.pos),
                creature.radius,
            )
        for shot in self.projectiles:
            pygame.draw.circle(
                surface,
                config.PROJECTILE_COLOR,
                self.camera.world_to_screen(shot.pos),
                shot.radius,
            )
        if self.core.ignited:
            # Only once it burns. An unlit core is an empty socket, and drawing
            # it lit made the opening look like it had already been won.
            pygame.draw.circle(
                surface,
                config.CORE_COLOR,
                self.camera.world_to_screen(self.core.pos),
                self.core.radius,
            )
        pygame.draw.circle(
            surface,
            config.PLAYER_COLOR,
            self.camera.world_to_screen(self.player.pos),
            self.player.radius,
        )
        self._draw_raid_edge(surface)
        self._draw_compass(surface)
        self._draw_hud(surface)
        self._draw_grid(surface)
        self._draw_craft(surface)
        self._draw_carve(surface)

    # --- the belongings screen -------------------------------------------
    def _toggle_grid(self) -> None:
        self.grid_open = not self.grid_open
        if self.grid_open:
            self.craft_open = False  # one screen at a time
        else:
            self.grid.close(self.backpack, self.hotbar)

    # --- the crafting menu ------------------------------------------------
    def _toggle_craft(self) -> None:
        self.craft_open = not self.craft_open
        if self.craft_open:
            if self.grid_open:
                self.grid.close(self.backpack, self.hotbar)
            self.grid_open = False
            self.carve_open = False

    # --- the carving screen -----------------------------------------------
    def _toggle_carve(self) -> None:
        self.carve_open = not self.carve_open
        if self.carve_open:
            if self.grid_open:
                self.grid.close(self.backpack, self.hotbar)
            self.grid_open = False
            self.craft_open = False

    @property
    def holding_staff(self) -> bool:
        held = self.hotbar.active_stack
        return held is not None and held.kind in STAFF_KINDS

    @property
    def staff_slots(self) -> int:
        """How much room the staff in hand has, read off the item itself."""
        held = self.hotbar.active_stack
        return STAFF_KINDS.get(held.kind, 0) if held is not None else 0

    @property
    def carve_target(self) -> Engraved | None:
        """What is cut into the thing in hand, if it is the sort that takes it.

        The held item rather than a separate equipment screen: the hotbar is
        already where tools live, and a second place to pick a weapon from
        would be a screen whose whole job is choosing between one option.
        """
        if self.holding_staff:
            # A better staff widens the one the player owns. Carried on the
            # item instead, every glyph already cut in would be thrown out with
            # the old staff -- not an upgrade anyone would take.
            self.staff.engraved.slots = max(self.staff.engraved.slots, self.staff_slots)
            return self.staff.engraved
        held = self.hotbar.active_tool
        piece = getattr(held, "engraved", None)
        return piece if isinstance(piece, Engraved) else None

    def carve_rows(self) -> list[tuple[Glyph, str | None]]:
        """Every learned glyph, each with the reason it cannot go on, or None.

        Refused ones are listed too. A list that quietly hid what does not fit
        would leave the player wondering whether they had lost a drawing or
        were simply holding the wrong thing.
        """
        piece = self.carve_target
        if piece is None:
            return []
        return [
            (glyph, engraving.can_engrave(piece, glyph, self.grimoire))
            for glyph in self.grimoire.known()
        ]

    def _click_carve(self, at: pygame.Vector2) -> None:
        for index, (glyph, refusal) in enumerate(self.carve_rows()):
            if not self._carve_row_rect(index).collidepoint(at):
                continue
            if refusal is not None:
                self._say(refusal)
            else:
                self.carve(glyph)
            return

    def carve(self, glyph: Glyph) -> None:
        """Cut it in, wearing the chisel down by one."""
        piece = self.carve_target
        if piece is None:
            return
        if engraving.can_engrave(piece, glyph, self.grimoire) is not None:
            return
        if self._carried(CHISEL) <= 0:
            self._say("새김 도구가 없다")
            return
        engraving.engrave(piece, glyph, self.grimoire)
        self.chisel_left -= 1
        if self.chisel_left <= 0:
            self._spend(CHISEL, 1)
            self.chisel_left = config.CHISEL_USES
            self._say(f"{glyph.name} 을(를) 새겼다 · 도구가 부서졌다")
        else:
            self._say(f"{glyph.name} 을(를) 새겼다 · {self.chisel_left}회 남음")

    def _carve_panel(self) -> pygame.Rect:
        rows = max(1, min(len(self.carve_rows()), config.CRAFT_ROWS_VISIBLE))
        panel = pygame.Rect(0, 0, 520, rows * config.CRAFT_ROW_HEIGHT + 48)
        panel.center = (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2)
        return panel

    def _carve_row_rect(self, index: int) -> pygame.Rect:
        panel = self._carve_panel()
        return pygame.Rect(
            panel.left + 10,
            panel.top + 36 + index * config.CRAFT_ROW_HEIGHT,
            panel.width - 20,
            config.CRAFT_ROW_HEIGHT - 2,
        )

    def carve_header(self) -> str:
        piece = self.carve_target
        if piece is None:
            return "손에 든 것엔 새길 수 없다"
        left = self.chisel_left if self._carried(CHISEL) else 0
        return f"칸 {len(piece.glyphs)}/{piece.slots} · 새김 도구 {left}회"

    def _draw_carve(self, surface: pygame.Surface) -> None:
        if not self.carve_open:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))
        panel = self._carve_panel()
        pygame.draw.rect(surface, config.GRID_PANEL, panel, border_radius=6)
        surface.blit(
            _font(14).render(self.carve_header(), True, config.WHITE),
            (panel.left + 12, panel.top + 12),
        )
        for index, (glyph, refusal) in enumerate(self.carve_rows()):
            rect = self._carve_row_rect(index)
            pygame.draw.rect(surface, (48, 48, 62), rect, border_radius=3)
            ink = config.WHITE if refusal is None else (132, 128, 145)
            swatch = pygame.Rect(rect.left + 6, rect.top + 5, 14, 14)
            colour = glyph.biome.color if glyph.biome is not None else (150, 150, 165)
            pygame.draw.rect(surface, colour, swatch, border_radius=2)
            surface.blit(_font(14).render(glyph.name, True, ink), (swatch.right + 8, rect.top + 4))
            tail = refusal.split(": ")[-1] if refusal else f"+{glyph.power:.0f}"
            label = _font(12).render(tail, True, ink)
            surface.blit(label, (rect.right - label.get_width() - 8, rect.top + 6))

    def _craft_rows(self) -> list[tuple[Recipe, bool]]:
        """What is offered where the player is standing, affordable first.

        Sorting the affordable ones up means the menu answers "what can I do
        right now" at a glance, and the rest read as a list of what to go and
        find.
        """
        here = stations_at(self.player.pos, self.stations)
        rows = crafting.available(here, self.backpack, self.hotbar)
        return sorted(rows, key=lambda row: (not row[1], row[0].output.name))

    def _craft_panel(self) -> pygame.Rect:
        rows = min(len(self._craft_rows()), config.CRAFT_ROWS_VISIBLE)
        height = rows * config.CRAFT_ROW_HEIGHT + 24
        panel = pygame.Rect(0, 0, 520, max(height, 60))
        panel.center = (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2)
        return panel

    def _craft_row_rect(self, index: int) -> pygame.Rect:
        panel = self._craft_panel()
        return pygame.Rect(
            panel.left + 10,
            panel.top + 12 + index * config.CRAFT_ROW_HEIGHT,
            panel.width - 20,
            config.CRAFT_ROW_HEIGHT - 2,
        )

    def _click_craft(self, where: pygame.Vector2) -> None:
        for index, (recipe, afford) in enumerate(self._craft_rows()):
            if index >= config.CRAFT_ROWS_VISIBLE:
                break
            if not self._craft_row_rect(index).collidepoint(where):
                continue
            if not afford:
                return
            if recipe.seconds > 0:
                self._start_job(recipe)
            else:
                crafting.craft(recipe, self.backpack, self.hotbar)
            return

    def _start_job(self, recipe: Recipe) -> None:
        """Hand a timed recipe to a station in reach that can take it."""
        for station in self.stations:
            if self.player.pos.distance_to(station.pos) > config.STATION_REACH:
                continue
            if recipe.station not in STATION_OF.get(station.kind, set()):
                continue
            if station.is_busy or not crafting.affordable(recipe, self.backpack, self.hotbar):
                continue
            if station.start(recipe):
                for kind, n in recipe.inputs:
                    crafting.spend(kind, n, self.backpack, self.hotbar)
            return

    def _draw_craft(self, surface: pygame.Surface) -> None:
        """One line per recipe: what it makes, and what it costs."""
        if not self.craft_open:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))
        pygame.draw.rect(surface, config.GRID_PANEL, self._craft_panel(), border_radius=6)
        for index, (recipe, afford) in enumerate(self._craft_rows()):
            if index >= config.CRAFT_ROWS_VISIBLE:
                break
            rect = self._craft_row_rect(index)
            pygame.draw.rect(surface, (48, 48, 62), rect, border_radius=3)
            swatch = pygame.Rect(rect.left + 4, rect.top + 4, 16, rect.height - 8)
            # Dim when it cannot be made, so "what can I do now" reads at a glance.
            colour = recipe.output.color if afford else tuple(c // 3 for c in recipe.output.color)
            pygame.draw.rect(surface, colour, swatch, border_radius=2)
            ink = config.WHITE if afford else (120, 120, 134)
            made = (
                recipe.output.name if recipe.count == 1 else f"{recipe.output.name} x{recipe.count}"
            )
            if recipe.seconds:
                made += f"  ({recipe.seconds:.0f}초)"
            surface.blit(_font(14).render(made, True, ink), (swatch.right + 8, rect.top + 4))
            cost = "  ".join(f"{kind.name} {n}" for kind, n in recipe.inputs)
            label = _font(12).render(cost, True, (150, 150, 165) if afford else (90, 90, 102))
            surface.blit(label, (rect.right - label.get_width() - 8, rect.top + 6))

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

    def _gather_underfoot(self) -> None:
        """Pick up loose things by walking over them.

        Only what an empty hand could take anyway -- twigs, pebbles, grass.
        Swinging at a twig is busywork; swinging at a tree is not, so trees and
        ore are left to the pickaxe.

        Anything that will not fit stays on the ground rather than vanishing.
        """
        for node in list(self.fragments):
            if grades.need_for(node.kind).family != grades.HAND:
                continue
            if self.player.pos.distance_to(node.pos) > config.PICKUP_RADIUS:
                continue
            if carrying.store(node.kind, 1, self.backpack, self.hotbar):
                self.fragments.remove(node)

    def _collect_stations(self) -> None:
        """Take finished goods out of anything the player is standing by."""
        for station in self.stations:
            if self.player.pos.distance_to(station.pos) > config.STATION_REACH:
                continue
            if not station.output.used:
                continue
            for kind, n in station.collect():
                left = n - carrying.store(kind, n, self.backpack, self.hotbar)
                if left:
                    station.output.add(kind, left)  # no room: leave it in there

    def _try_place(self, where: pygame.Vector2) -> bool:
        """Put down the selected station item, if that is what is held.

        Returns True when the click was spent on building, so the same press
        does not also start swinging a tool at whatever is underneath.
        """
        held = self.hotbar.active_stack
        if held is None or held.kind not in STATION_OF:
            return False
        at = self.camera.screen_to_world(where)
        if not place(held.kind, at, self.stations, self.core):
            return True  # the click was a build attempt; it simply failed
        self.hotbar.remove(held.kind, 1)
        return True

    def _draw_stations(self, surface: pygame.Surface) -> None:
        """Built stations, and a ring on the one whose recipes are open."""
        open_here = stations_at(self.player.pos, self.stations)
        for station in self.stations:
            at = self.camera.world_to_screen(station.pos)
            pygame.draw.circle(surface, station.kind.color, at, config.STATION_RADIUS)
            if station.is_busy and station.job is not None:
                # Fills up as the job runs, so progress is readable in passing.
                done = 1 - station.remaining / max(station.job.seconds, 1e-9)
                pygame.draw.circle(surface, config.LOOT_COLOR, at, config.STATION_RADIUS * done)
            elif station.output.used:
                pygame.draw.circle(surface, config.LOOT_COLOR, at, config.STATION_RADIUS - 6)
            if STATION_OF.get(station.kind, set()) & open_here:
                pygame.draw.circle(surface, config.WHITE, at, config.STATION_RADIUS + 3, 2)

    def _draw_nodes(self, surface: pygame.Surface) -> None:
        """Nodes in the colour of what they hold, and a ring on the one aimed at.

        The ring is red when the tool in hand cannot take it. Without that,
        being under-equipped looks exactly like the game ignoring the click.
        """
        # An empty hand still reaches for litter, so it gets a reach too.
        tool = self.hotbar.active_tool or BARE_HAND
        aimed = (
            mining.pick_target(
                self.camera.screen_to_world(self._mouse_screen),
                self.player.pos,
                self.fragments,
                tool.range,
            )
            if isinstance(tool, MiningTool)
            else None
        )
        for node in self.fragments:
            at = self.camera.world_to_screen(node.pos)
            pygame.draw.circle(surface, node.kind.color, at, config.FRAGMENT_RADIUS)
            if node is aimed:
                usable = mining.can_take(tool, node.kind)
                ring = config.WHITE if usable else config.BLOCKED_COLOR
                pygame.draw.circle(surface, ring, at, config.FRAGMENT_RADIUS + 4, 2)

    def _draw_ward(self, surface: pygame.Surface) -> None:
        """The ward's rim, or the empty pedestal waiting for the shards."""
        center = self.camera.world_to_screen(self.core.pos)
        if not self.core.ignited:
            # A socket with nothing in it: a dark hollow inside a stone rim, so
            # it reads as somewhere to put something rather than as a thing.
            pygame.draw.circle(surface, config.VOID_COLOR, center, self.core.radius - 4)
            pygame.draw.circle(surface, config.PEDESTAL_COLOR, center, self.core.radius, 4)
            return
        pygame.draw.circle(surface, self.ward_colour, center, self.core.ward_radius, 2)

    def _draw_night(self, surface: pygame.Surface) -> None:
        """Darken the ground outside the ward once night falls.

        Punched through inside the ward, so the safe land reads as safe at a
        glance. Laid over the terrain and the scenery only -- creatures, the
        player, shots and loot all go on top, so the dark is a mood rather than
        a blindfold.
        """
        if not self.clock.is_night:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 20, config.NIGHT_DARKNESS))
        # On a raid night the hole is not punched at all. The ward is holding
        # nothing out, so there is no safe circle to show -- and it makes the
        # bad nights look different from the quiet ones at a glance, which
        # matters when the rim itself is far off screen.
        if self.core.ignited and not self.is_raid:
            pygame.draw.circle(
                overlay,
                (0, 0, 0, 0),
                self.camera.world_to_screen(self.core.pos),
                self.core.ward_radius,
            )
        surface.blit(overlay, (0, 0))

    def _draw_raid_edge(self, surface: pygame.Surface) -> None:
        """A red pulse around the screen's rim while the ward is open.

        The ward is thousands of units across and the view is hundreds, so on
        a raid night the broken rim and the golems walking in on it are both
        off screen. Something has to say "this is happening" at a size that
        does not depend on where the camera is pointed.
        """
        if not self.is_raid:
            return
        beat = 0.5 + 0.5 * math.sin(self.clock.elapsed * config.RAID_PULSE_SPEED)
        alpha = int(config.RAID_PULSE_MIN + beat * (config.RAID_PULSE_MAX - config.RAID_PULSE_MIN))
        glow = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        width, height = surface.get_size()
        for step in range(config.RAID_EDGE_WIDTH):
            fade = 1 - step / config.RAID_EDGE_WIDTH
            pygame.draw.rect(
                glow,
                (*config.WARD_BROKEN_COLOR, int(alpha * fade)),
                pygame.Rect(step, step, width - 2 * step, height - 2 * step),
                1,
            )
        surface.blit(glow, (0, 0))

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

    def _say(self, line: str) -> None:
        """Put a line on screen for a few seconds.

        Learning a glyph is otherwise invisible: the ruin dims and nothing
        else happens, which reads as a bug rather than as a reward.
        """
        self.note = line
        self.note_left = config.NOTE_SECONDS

    def _open_structure(self) -> None:
        """Read whatever ruin the player is standing at.

        The same key that deals with the core. There is nowhere both a ruin and
        the core can be reached from, so the two never argue over the press.
        """
        for site in self.structures:
            if site.opened or not site.in_reach(self.player.pos):
                continue
            glyph = site.open()
            if glyph is None:
                continue
            fresh = self.grimoire.learn(glyph)
            self._say(f"{glyph.name} 을(를) 배웠다" if fresh else f"{glyph.name} — 이미 아는 그림")
            return

    def _draw_structures(self, surface: pygame.Surface) -> None:
        """Ruins, drawn so an unopened one is worth walking to.

        An opened one keeps its outline and loses its fill: still a landmark,
        plainly finished with.
        """
        for site in self.structures:
            at = self.camera.world_to_screen(site.pos)
            colour = config.VAULT_COLOR if site.guarded else config.RUIN_COLOR
            if site.opened:
                pygame.draw.circle(surface, config.RUIN_SPENT_COLOR, at, site.radius, 2)
                continue
            pygame.draw.circle(surface, colour, at, site.radius)
            pygame.draw.circle(surface, config.WHITE, at, site.radius, 2)
            if site.in_reach(self.player.pos):
                pygame.draw.circle(surface, config.WHITE, at, site.radius + 6, 2)

    def _draw_temples(self, surface: pygame.Surface) -> None:
        """Placeholder markers so the five sites are visible before temples exist."""
        for site in self.temple_sites:
            pygame.draw.circle(surface, config.WHITE, self.camera.world_to_screen(site), 9, 3)

    def _draw_compass(self, surface: pygame.Surface) -> None:
        """Point at the core when it is off screen, and say how far.

        The grassland alone is seventy-five screens across, so home is out of
        sight almost all the time. Without this it is not merely far, it is
        lost -- there is nothing on an empty field to steer by.

        Distance is given in walking time, because that is the unit every other
        decision is made in: a day is twelve minutes and the biomes are three.
        """
        self._point_at(surface, self.core.pos, config.CORE_COLOR, "코어")
        for pile in self.loot:
            self._point_at(surface, pile.pos, config.LOOT_COLOR, "짐")

    def _point_at(
        self,
        surface: pygame.Surface,
        target: pygame.Vector2,
        colour: tuple[int, int, int],
        label: str,
    ) -> None:
        at = edge_marker(
            self.camera.world_to_screen(target), config.SCREEN_SIZE, config.COMPASS_MARGIN
        )
        if at is None:
            return  # it is on screen; the thing itself is the marker
        pygame.draw.circle(surface, colour, at, 7)
        pygame.draw.circle(surface, (20, 20, 28), at, 7, 2)
        seconds = self.player.pos.distance_to(target) / config.PLAYER_SPEED
        far = f"{seconds / 60:.1f}분" if seconds >= 60 else f"{seconds:.0f}초"
        text = _font(12).render(f"{label} {far}", True, colour)
        box = text.get_rect(center=(int(at.x), int(at.y) + 16))
        box.clamp_ip(surface.get_rect())
        surface.blit(text, box)

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
        # day/night progress: warm across the day, cold across the night, and
        # red while the ward is open, so the hour and the danger are one gauge.
        if self.is_raid:
            phase_color = config.WARD_BROKEN_COLOR
        else:
            phase_color = (90, 110, 200) if self.clock.is_night else (240, 220, 130)
        _draw_bar(surface, 62, 5, self.clock.phase_fraction, phase_color, bg=(40, 40, 55))
        # the core's own health, below the clock -- only once it can be hurt
        if self.core.ignited:
            _draw_bar(surface, 74, 8, self.core.hp / self.core.max_hp, config.CORE_COLOR)
        line = _font(13).render(self.calendar_line, True, config.WHITE)
        surface.blit(line, (10, 88))
        if self.note_left > 0:
            # Fades out rather than vanishing, so a glance that catches the
            # tail of it still reads as "something just happened".
            said = _font(16).render(self.note, True, config.WHITE)
            said.set_alpha(int(255 * min(1.0, self.note_left / config.NOTE_FADE)))
            surface.blit(said, said.get_rect(midtop=(surface.get_width() // 2, 24)))
        # hotbar (bottom-left). Hidden while the belongings screen is open,
        # which draws its own -- two hotbars on screen reads as two hotbars.
        if self.grid_open:
            return
        for i in range(len(self.hotbar.slots)):
            x = 10 + i * 44
            color = config.WHITE if i == self.hotbar.selected else (120, 120, 140)
            pygame.draw.rect(surface, color, pygame.Rect(x, surface.get_height() - 50, 40, 40), 2)
