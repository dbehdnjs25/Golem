"""Core-loop gameplay scene: mine shards, fill the inventory, return to the core
and press E to deal with it. Wires the entities and systems together;
accumulates input from events (no polling) and owns all rendering."""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Any

import pygame

from game import config, saves
from game.core import controls as ctl
from game.core.controls import Controls
from game.core.scene import Scene
from game.entities.beast import Beast
from game.entities.boss import BOSS_KINDS, Boss
from game.entities.core import Core
from game.entities.dropped import Dropped
from game.entities.enemy import Creature, Golem, golem_of
from game.entities.enemy import swing as enemy_swing
from game.entities.fragment import Fragment
from game.entities.hazard import Pillar, Rod
from game.entities.loot import LootPile
from game.entities.patch import BURNING, FROST, SLUDGE, Patch
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.entities.station import Station, place, stations_at
from game.entities.structure import Structure
from game.entities.temple import Temple
from game.inventory import grid, packs
from game.inventory.grid import Grid
from game.inventory.hotbar import Hotbar
from game.inventory.stack import Stack
from game.inventory.storage import Container
from game.items import glyphs as glyph_table
from game.items import grades, strokes
from game.items.item_kinds import (
    CORE_SHARD,
    CORE_SIGIL,
    GRASS,
    OBSIDIAN_STONE,
    PEBBLE,
    STONE,
    TWIG,
    WOOD,
    ItemKind,
    yield_of,
)
from game.items.recipes import STATION_OF, Recipe
from game.items.staff import STAFF_ITEMS, Staff
from game.items.tools import WeaponTool
from game.render import art
from game.render.floor import Floor
from game.render.resources import resource_image, world_resource_image
from game.render.trees import has_own_shadow, tree_image, tree_shadow
from game.systems import (
    aim,
    arena,
    boss_moves,
    carrying,
    combat,
    consume,
    crafting,
    detector,
    drawing,
    falling,
    gimmicks,
    mining,
    raids,
    spoils,
    status,
    survival,
    weather,
)
from game.systems import (
    ending as ending_rules,
)
from game.systems.beast_spawner import BeastSpawner
from game.systems.camera import Camera, edge_marker
from game.systems.daynight import DayNight
from game.systems.enemy_spawner import EnemySpawner
from game.systems.grimoire import Grimoire
from game.systems.spawn_common import SPAWN_ATTEMPTS, near_player
from game.systems.spawner import Spawner, TreeSpawner
from game.world import biomes, chasms, dungeon, ice, lava, mires, rooms, structures, temples
from game.world.biomes import Biome
from game.world.map import WorldMap

# Held, not tapped: these ride in the held set rather than firing on a press.
_HELD_ACTIONS = (
    ctl.MOVE_UP,
    ctl.MOVE_DOWN,
    ctl.MOVE_LEFT,
    ctl.MOVE_RIGHT,
    ctl.SPRINT,
    ctl.ACTION,
)
_STROKE_OF = {
    ctl.DRAW_UP: strokes.UP,
    ctl.DRAW_DOWN: strokes.DOWN,
    ctl.DRAW_LEFT: strokes.LEFT,
    ctl.DRAW_RIGHT: strokes.RIGHT,
}
# Moving a menu cursor: either hand works, so the walking keys and the drawing
# keys both steer it. Enter confirms as well as the action key, because a menu
# is the one place a player reaches for it without thinking.
_MENU_STEP = {
    ctl.MOVE_UP: (0, -1),
    ctl.MOVE_DOWN: (0, 1),
    ctl.MOVE_LEFT: (-1, 0),
    ctl.MOVE_RIGHT: (1, 0),
    ctl.DRAW_UP: (0, -1),
    ctl.DRAW_DOWN: (0, 1),
    ctl.DRAW_LEFT: (-1, 0),
    ctl.DRAW_RIGHT: (1, 0),
}
_CONFIRM_KEYS = {pygame.K_RETURN, pygame.K_KP_ENTER}
# What Esc opens. The world waits behind it, and leaving the game is a row
# here rather than a bare key, so one stray press cannot end a run.
RESUME = "resume"
KEYS = "keys"
QUIT = "quit"
_PAUSE_ROWS: tuple[tuple[str, str], ...] = (
    (RESUME, "계속하기"),
    (KEYS, "키 설정"),
    (QUIT, "저장하고 나가기"),
)

# Korean first, since every item name is Korean; the fallbacks are only so a
# machine without these still draws something rather than raising.
_FONT_NAMES = ("malgungothic", "gulim", "arial")
_fonts: dict[int, pygame.font.Font] = {}
# The UI is drawn in code, not from images: charcoal boxes with a sage edge,
# the palette the old art used. Every framed thing -- slots, panels, bars,
# tooltips -- goes through ``_draw_frame``, so restyling is one place.
_UI_FILL = (32, 35, 34)
_UI_EDGE = (76, 81, 78)
_UI_EDGE_LIT = (205, 194, 156)  # the selected slot's edge
_HEART_COLOR = (207, 76, 100)
_STAMINA_ICON_COLOR = (147, 192, 136)
_BAG_COLOR = (150, 125, 84)
# Small icons as pixel masks, drawn by ``_draw_pixel_icon``.
_HEART_ICON = ("0110110", "1111111", "1111111", "0111110", "0011100", "0001000")
_STAMINA_ICON = ("0011", "0110", "1111", "0110", "1100")
_BAG_ICON = (
    "00111100",
    "01000010",
    "11111111",
    "10000001",
    "10011001",
    "10000001",
    "11111111",
)


def _draw_frame(surface: pygame.Surface, rect: pygame.Rect, *, selected: bool = False) -> None:
    """A dark rounded box with a thin edge; a light edge when ``selected``."""
    scale = config.UI_SCALE
    radius = min(4 * scale, rect.height // 2)
    pygame.draw.rect(surface, _UI_FILL, rect, border_radius=radius)
    edge = _UI_EDGE_LIT if selected else _UI_EDGE
    pygame.draw.rect(surface, edge, rect, scale, border_radius=radius)


def _draw_pixel_icon(
    surface: pygame.Surface,
    mask: tuple[str, ...],
    center: tuple[int, int],
    color: tuple[int, int, int],
    px: int,
) -> None:
    """Draw a pixel mask ("1" = filled) centred on ``center``, ``px`` per cell."""
    left = center[0] - len(mask[0]) * px // 2
    top = center[1] - len(mask) * px // 2
    for row, bits in enumerate(mask):
        for column, bit in enumerate(bits):
            if bit == "1":
                pygame.draw.rect(surface, color, (left + column * px, top + row * px, px, px))


def _has_final_consonant(word: str) -> bool:
    """Whether a Korean word ends in a consonant, which both markers turn on.

    Hangul syllables are laid out so that the remainder tells you. Anything
    that is not a syllable counts as a vowel ending, which is the safer guess
    for a loanword read aloud.
    """
    if not word:
        return False
    last = word.strip()[-1]
    if not ("가" <= last <= "힣"):
        return False
    return (ord(last) - 0xAC00) % 28 != 0


def _subject_particle(word: str) -> str:
    """Korean's subject marker: 이 after a final consonant, 가 after a vowel.

    Written out rather than as "이(가)", which is how a form looks and not how
    anyone speaks.
    """
    return "이" if _has_final_consonant(word) else "가"


def _object_particle(word: str) -> str:
    """Korean's object marker: 을 after a final consonant, 를 after a vowel.

    Picked from the last syllable rather than written as "을(를)", which is
    how a form looks, not how anyone speaks.
    """
    return "을" if _has_final_consonant(word) else "를"


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
# What each sort of left-behind ground is drawn in. Near its biome's own
# colour, so the floor still reads as that biome with a trick on it.
_PATCH_COLORS = {
    BURNING: config.BURNING_COLOR,
    FROST: config.FROST_COLOR,
    SLUDGE: config.SLUDGE_COLOR,
}

_BAR_X = 10 * config.UI_SCALE
_BAR_W = 120 * config.UI_SCALE
_BAR_BG = (60, 60, 80)

_PIXEL_DIGITS = {
    "1": ("010", "110", "010", "010", "111"),
    "2": ("110", "001", "010", "100", "111"),
    "3": ("110", "001", "010", "001", "110"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "110", "001", "110"),
}
_HOTBAR_DIGIT_SCALE = 2 * config.UI_SCALE


def _draw_hotbar_digit(
    surface: pygame.Surface,
    digit: int,
    x: int,
    y: int,
    color: tuple[int, int, int],
) -> None:
    """Draw a tiny pixel key number on the slot well, before its item sprite."""
    for row, bits in enumerate(_PIXEL_DIGITS[str(digit)]):
        for column, bit in enumerate(bits):
            if bit == "1":
                px = x + column * _HOTBAR_DIGIT_SCALE
                py = y + row * _HOTBAR_DIGIT_SCALE
                pygame.draw.rect(
                    surface,
                    color,
                    pygame.Rect(px, py, _HOTBAR_DIGIT_SCALE, _HOTBAR_DIGIT_SCALE),
                )


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


def _draw_gauge(
    surface: pygame.Surface,
    y: int,
    height: int,
    frac: float,
    color: tuple[int, int, int],
    *,
    icon: tuple[str, ...] | None = None,
    icon_color: tuple[int, int, int] = _STAMINA_ICON_COLOR,
) -> None:
    """A framed resource gauge, ``height`` UI units tall, with its fill inside
    the frame and an optional pixel icon at its left end."""
    scale = config.UI_SCALE
    rect = pygame.Rect(_BAR_X, y, 136 * scale, height * scale)
    _draw_frame(surface, rect)
    left = 13 * scale if icon else 3 * scale
    top = (2 if rect.height >= 16 else 1) * scale
    inner_height = max(scale, rect.height - 2 * top)
    inner_width = max(0, rect.width - left - 3 * scale)
    width = int(inner_width * min(1.0, max(0.0, frac)))
    if width:
        _draw_pixel_round_right(
            surface,
            pygame.Rect(rect.left + left, rect.top + top, width, inner_height),
            color,
            scale,
            1,
        )
    if icon:
        center = (rect.left + 7 * scale, rect.centery)
        _draw_pixel_icon(surface, icon, center, icon_color, scale)


def _draw_pixel_round_rect(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
    scale: int,
    cut: int,
) -> None:
    rows = rect.height // scale
    columns = rect.width // scale
    for row in range(rows):
        inset = max(0, cut - min(row, rows - 1 - row) - 1)
        pygame.draw.rect(
            surface,
            color,
            pygame.Rect(
                rect.x + inset * scale,
                rect.y + row * scale,
                (columns - 2 * inset) * scale,
                scale,
            ),
        )


def _draw_pixel_round_right(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
    scale: int,
    cut: int,
) -> None:
    rows = rect.height // scale
    columns = rect.width // scale
    for row in range(rows):
        inset = max(0, cut - min(row, rows - 1 - row) - 1)
        pygame.draw.rect(
            surface,
            color,
            pygame.Rect(
                rect.x,
                rect.y + row * scale,
                (columns - inset) * scale,
                scale,
            ),
        )


def _draw_health_bar(surface: pygame.Surface, y: int, frac: float) -> None:
    """Draw the health gauge joined to an enlarged square heart tile."""
    scale = config.UI_SCALE
    icon_size = 20 * scale
    height = 14 * scale
    cap_y = y - 4 * scale
    x = _BAR_X
    frame = (76, 81, 78)
    frame_light = (105, 111, 106)
    well = (32, 35, 34)

    # Heart cap: stepped pixel corners echo the hotbar's square slots.
    _draw_pixel_round_rect(surface, pygame.Rect(x, cap_y, icon_size, icon_size), frame, scale, 3)
    _draw_pixel_round_rect(
        surface,
        pygame.Rect(x + scale, cap_y + scale, icon_size - 2 * scale, icon_size - 2 * scale),
        frame_light,
        scale,
        2,
    )
    _draw_pixel_round_rect(
        surface,
        pygame.Rect(x + 3 * scale, cap_y + 3 * scale, icon_size - 6 * scale, icon_size - 6 * scale),
        well,
        scale,
        1,
    )

    # Keep the square's right edge. The gauge has no left end cap, so its
    # background begins flush against that edge and only its top/bottom/right
    # frame lines are drawn.
    body_x = x + icon_size
    # Match the other HUD gauges' overall right edge: the heart tile is part
    # of the health gauge's width rather than extra width added to it.
    body_width = _BAR_W - icon_size
    _draw_pixel_round_right(
        surface, pygame.Rect(body_x, y, body_width, height), frame_light, scale, 3
    )
    pygame.draw.line(
        surface,
        frame,
        (body_x, y),
        (body_x + body_width - 2 * scale - 1, y),
        scale,
    )
    pygame.draw.line(
        surface,
        frame,
        (body_x, y + height - scale),
        (body_x + body_width - 2 * scale - 1, y + height - scale),
        scale,
    )
    pygame.draw.rect(
        surface,
        frame,
        pygame.Rect(body_x + body_width - 2 * scale, y + scale, scale, scale),
    )
    pygame.draw.line(
        surface,
        frame,
        (body_x + body_width - scale, y + 2 * scale),
        (body_x + body_width - scale, y + height - 2 * scale - 1),
        scale,
    )
    pygame.draw.rect(
        surface,
        frame,
        pygame.Rect(
            body_x + body_width - 2 * scale,
            y + height - 2 * scale,
            scale,
            scale,
        ),
    )
    _draw_pixel_round_right(
        surface,
        pygame.Rect(body_x, y + 3 * scale, body_width - 3 * scale, height - 6 * scale),
        well,
        scale,
        1,
    )
    _draw_pixel_icon(
        surface,
        _HEART_ICON,
        (x + icon_size // 2, cap_y + icon_size // 2),
        _HEART_COLOR,
        3 * scale // 2,
    )

    fill_x = body_x
    fill_y = y + 3 * scale
    fill_width = body_width - 3 * scale
    fill_width = int(fill_width * max(0.0, min(1.0, frac)))
    if fill_width:
        _draw_pixel_round_right(
            surface,
            pygame.Rect(fill_x, fill_y, fill_width, height - 6 * scale),
            (255, 0, 0),
            scale,
            1,
        )


class PlayScene(Scene):
    def __init__(
        self,
        controls: Controls | None = None,
        controls_path: Path | None = None,
        seed: int | None = None,
        save_slot: int | None = None,
        save_folder: Path = saves.SAVE_DIR,
    ) -> None:
        # Which key does what. Saved only when a path is given, so a test
        # that rebinds a key never writes the player's settings file.
        self.controls = controls if controls is not None else Controls()
        self.controls_path = controls_path
        self.rng = random.Random(1234)
        self.world = WorldMap.create(self.rng)
        self.temple_sites = self.world.temple_sites(self.rng)
        self.temples = temples.place(self.world, self.temple_sites, self.rng)
        # ``seed`` is this run's: it rerolls what grows and what is built
        # INSIDE the land -- the trees, each temple's rooms -- while the land
        # (biomes, temple sites, lava) keeps the fixed 1234 above. A new game
        # passes a fresh one; None is the fixed run every test is written for.
        self.seed = seed
        # Which save slot this game lives in. Saved into it when the scene is
        # left -- quitting from the Esc menu or closing the window. None (every
        # test) saves nothing.
        self.save_slot = save_slot
        self.save_folder = save_folder
        run = random.Random(seed) if seed is not None else None
        if run is not None:
            for temple in self.temples:
                temple.salt = run.randrange(temples.SALT_SPAN)
        self.arena = arena.Ground()
        self.boss: Boss | None = None  # at most one, and only inside a temple
        self.boss_temple: Temple | None = None  # which room it is holding
        # The temple the player is INSIDE, which is a different question
        # from which one they are standing on top of on the map.
        self.inside: Temple | None = None
        self.brawl: boss_moves.Brawl | None = None  # its hands, while it has any
        center = self.world.center
        self.core = Core(pos=pygame.Vector2(center))
        self.clock = DayNight()
        self.ending = ending_rules.Ending()
        self.grimoire = Grimoire()
        self.note = ""  # a line that fades; see _say
        self.note_left = 0.0
        # One staff, upgraded in place: the item in a slot is a token for it,
        # since what matters about a staff -- how hot it is right now -- cannot
        # ride in a Stack.
        self.staff = Staff()
        # The shape being drawn. Not on the staff, because the hand is the
        # player's and goes on drawing whether or not one is being held.
        self.drawing = drawing.Drawing()
        self.structures = structures.place(self.world, self.rng)
        self.lava = lava.place(self.world, self.rng)
        self.mires = mires.place(self.world, self.rng)
        self.chasms = chasms.place(self.world, self.rng)
        self.ice = ice.place(self.world, self.rng)
        self.floor = Floor(self.world)  # the tiled ground, built in chunks
        self._art_frames = 0  # draws since the last look for re-saved art
        # What the tricks leave behind. One pair of lists for the whole field:
        # a supreme glyph and a boss write to the same ground, because they
        # are the same trick thrown from different ends.
        self.patches: list[Patch] = []
        self.marks: list[pygame.Vector2] = []
        self.mark_timers: list[float] = []
        self._field: pygame.Surface | None = None  # reused when the zoom != 1
        self.player = Player(pos=pygame.Vector2(center))
        self.camera = Camera(
            offset=pygame.Vector2(0, 0),
            view_size=config.SCREEN_SIZE,
            world_size=config.WORLD_SIZE,
        )
        self.camera.center_on(self.player.pos)
        # No base inventory: without a pack the hotbar is all there is.
        # The base inventory, grown by whatever pack is worn. Typed as maybe
        # None only for saves from before it existed; update() fills one in.
        self.backpack: Container | None = Container.empty(config.BASE_INVENTORY_SLOTS)
        self.worn_pack: ItemKind | None = None  # which pack, so a death can drop it
        self.loot: list[LootPile] = []  # several may be outstanding at once
        self.dropped: list[Dropped] = []  # put down on purpose; see _drop
        self.stations: list[Station] = []
        self.grid = Grid()
        self.grid_open = False
        self.craft_open = False
        self.hotbar = Hotbar.create()
        # Nothing but the weapon. Wood comes off a tree with bare hands, and the
        # first axe is crafted from it -- the opening is a thing the player does
        # rather than a kit they are handed.
        self.hotbar.slots[4] = WeaponTool()
        self.fragments: list[Fragment] = []
        # Terrain, laid down once: obsidian only ever comes off these, and they
        # stand close enough to the lava that chipping one means standing where
        # it is hot. Marked fixed so the roaming node spawner ignores them.
        self.fragments.extend(
            Fragment(pos=spot, kind=OBSIDIAN_STONE, fixed=True)
            for spot in lava.obsidian_sites(self.lava, self.rng)
        )
        self.spawner = Spawner()
        self._scatter_starting_shards()
        # Trees on their own clock and their own dice, so wooding the map does
        # not shift every other roll the run makes after it.
        self.tree_spawner = TreeSpawner()
        self.tree_rng = random.Random(run.randrange(2**32) if run is not None else 4321)
        self.tree_spawner.fill(
            self.fragments, self.core, self.tree_rng, self.world, self.player.pos
        )

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
        # The body is the aim: the way they last walked. Down to start with,
        # towards the camera, so the first swing lands somewhere visible.
        self.facing = pygame.Vector2(0, 1)
        self._swing_left = 0.0  # how long the last sweep stays drawn
        self._dig_timer = 0.0  # time until the tool can land its next blow
        # Menu cursors. The belongings screen starts on the hand that is
        # selected; the recipe list starts at the top.
        self.grid_cursor: tuple[str, int] = (grid.HOTBAR, 0)
        self.craft_cursor = 0
        self.pause_open = False  # the Esc menu
        self.pause_cursor = 0
        self.settings_open = False  # the key list, opened from it or by F1
        self.settings_cursor = 0
        self.settings_waiting = False  # the next key pressed is the new binding

    def _scatter_starting_shards(self) -> None:
        """Seed the pedestal's surroundings with the shards that light the core.

        They sit within reach of the spawn on purpose: the opening should be a
        short errand, not a search. Placing the core is what starts day one, and
        the player chooses when.
        """
        # Exactly as many as the core asks for. There used to be two spare,
        # which meant the opening ended with the player holding junk: once
        # lit, a shard is good for nothing, and the core has no store to drop
        # the leftovers into any more.
        #
        # Counted rather than looped, so a spot the world refuses does not
        # quietly leave the run one shard short of ever starting.
        placed = 0
        for _ in range(config.CORE_SHARDS_TO_IGNITE * SPAWN_ATTEMPTS):
            if placed >= config.CORE_SHARDS_TO_IGNITE:
                break
            spot = near_player(self.player.pos, self.rng, self.world)
            if spot is not None:
                self.fragments.append(Fragment(pos=spot, kind=CORE_SHARD))
                placed += 1
        # Litter first, then trees. A player holding nothing can only take the
        # litter, and the crude axe it makes is what opens the trees -- so the
        # first five minutes have an order to them rather than a wall.
        for kind, count in ((TWIG, 6), (PEBBLE, 4), (GRASS, 6), (WOOD, 6)):
            for _ in range(count):
                spot = near_player(self.player.pos, self.rng, self.world)
                if spot is not None:
                    self.fragments.append(Fragment(pos=spot, kind=kind))

    def _wear_if_pack(self, kind: ItemKind | None) -> None:
        """A pack is worn the moment it is dug up -- it adds its slots.

        On top of the base inventory, keeping everything already carried. A
        bigger one replaces a smaller one; a smaller one changes nothing.
        """
        if kind is None or not packs.is_pack(kind):
            return
        size = config.BASE_INVENTORY_SLOTS + packs.slots_of(kind)
        carried = self.backpack if self.backpack is not None else Container.empty(0)
        if size <= carried.size:
            return
        self.backpack = Container(slots=[*carried.slots, *([None] * (size - carried.size))])
        self.worn_pack = kind

    # --- dropping on purpose ----------------------------------------------
    def _drop(self, slots: list[Any], index: int) -> None:
        """Put the thing in ``slots[index]`` on the ground at the player's feet.

        One of a stack, or the whole stack with sprint held; a tool always
        goes whole. Pressed again before walking off, it joins the same pile
        rather than scattering a pile per press.
        """
        if not 0 <= index < len(slots) or slots[index] is None:
            return
        held = slots[index]
        whole = self.controls.any_held(self._held_keys, ctl.SPRINT)
        if isinstance(held, Stack) and not whole and held.count > 1:
            held.count -= 1
            item: object = Stack(held.kind, 1)
        else:
            slots[index] = None
            item = held
        for pile in self.dropped:
            if (
                not pile.armed
                and isinstance(item, Stack)
                and isinstance(pile.item, Stack)
                and pile.item.kind is item.kind
                and pile.item.room >= item.count
                and pile.pos.distance_to(self.player.pos) < 1
            ):
                pile.item.count += item.count
                return
        self.dropped.append(Dropped(pos=pygame.Vector2(self.player.pos), item=item))

    def _tick_dropped(self, dt: float) -> None:
        """Age what was dropped, and pick up whatever the player walks back onto."""
        for pile in self.dropped:
            pile.update(dt, self.player.pos)
            if pile.can_take(self.player.pos):
                self._take_dropped(pile)
        self.dropped = [
            pile
            for pile in self.dropped
            if not pile.is_gone
            and not (isinstance(pile.item, Stack) and pile.item.count == 0)
            and pile.item is not None
        ]

    def _take_dropped(self, pile: Dropped) -> None:
        """Back into the bag (or the hotbar); what will not fit stays put."""
        item = pile.item
        if isinstance(item, Stack):
            item.count -= carrying.store(item.kind, item.count, self.backpack, self.hotbar)
            return
        for i, slot in enumerate(self.hotbar.slots):
            if slot is None:
                self.hotbar.slots[i] = item
                pile.item = None
                return

    def _draw_dropped(self, surface: pygame.Surface) -> None:
        size = config.DROP_ICON
        for pile in self.dropped:
            if pile.item is None:
                continue
            at = self.camera.world_to_screen(pile.pos)
            box = pygame.Rect(0, 0, size, size)
            box.center = (round(at.x), round(at.y))
            self._draw_contents(surface, box, pile.item)

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
        """Take back what a death left: put its pack on, then its goods in."""
        if pile.pack is not None:
            self._wear_if_pack(pile.pack)
            pile.pack = None  # worn now, or a bigger one already is
        if self.backpack is not None:
            for kind, n in pile.contents.rows():
                pile.contents.remove(kind, self.backpack.add(kind, n))
        if pile.contents.used:
            return  # no room for all of it -- leave the rest where it lies
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
    @property
    def _action_held(self) -> bool:
        return self.controls.any_held(self._held_keys, ctl.ACTION)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYUP:
            self._held_keys.discard(event.key)
            return
        if event.type != pygame.KEYDOWN:
            return  # no mouse: the whole game is played from the keyboard
        key = event.key
        if self.settings_open:
            self._settings_key(key)
            return
        if self.pause_open:
            self._pause_key(key)
            return
        if key == ctl.SETTINGS_KEY:
            self._open_settings()
            return
        if self.grid_open or self.craft_open:
            self._menu_key(key)
            return
        if key == ctl.BACK_KEY:
            self._open_pause()
            return
        controls = self.controls
        if controls.is_key(key, ctl.ACTION):
            # A press is spent on building or eating if that is what is in
            # hand; otherwise it is the start of holding a swing or a dig.
            if self._try_place() or self._eat_held():
                return
            self._held_keys.add(key)
            return
        if any(controls.is_key(key, action) for action in _HELD_ACTIONS):
            self._held_keys.add(key)
            return
        action = controls.action_of(key)
        if action in ctl.SLOTS:
            self.hotbar.select(ctl.SLOTS.index(action))
        elif action == ctl.DODGE:
            self._dodge_pressed = True
        elif action == ctl.SYNC:
            self._sync_pressed = True
        elif action == ctl.INVENTORY:
            self._toggle_grid()
        elif action == ctl.CRAFT:
            self._toggle_craft()
        elif action == ctl.DROP:
            self._drop(self.hotbar.slots, self.hotbar.selected)
        elif action == ctl.ZOOM_IN:
            self.camera.zoom_by(1)
        elif action == ctl.ZOOM_OUT:
            self.camera.zoom_by(-1)
        elif action in _STROKE_OF:
            # The drawing keys draw. The walking keys are already walking, so
            # both hands work at once -- which is the whole reason a spell is
            # drawn rather than picked off a list.
            self.drawing.stroke(_STROKE_OF[action])

    def _menu_key(self, key: int) -> None:
        """A key while the belongings or the recipe screen is up."""
        action = self.controls.action_of(key)
        if action == ctl.SPRINT:
            self._held_keys.add(key)  # so Shift+drop works with the bag open
        if key == ctl.BACK_KEY:
            self._close_menus()
        elif action == ctl.INVENTORY:
            self._toggle_grid()
        elif action == ctl.CRAFT:
            self._toggle_craft()
        elif key in _CONFIRM_KEYS or action == ctl.ACTION:
            if self.grid_open:
                self._confirm_grid()
            else:
                self._confirm_craft()
        elif action in _MENU_STEP:
            dx, dy = _MENU_STEP[action]
            if self.grid_open:
                self._step_grid(dx, dy)
            else:
                self._step_craft(dy)
        elif action in ctl.SLOTS:
            self.hotbar.select(ctl.SLOTS.index(action))
        elif action == ctl.DROP and self.grid_open:
            where, index = self.grid_cursor
            if where == grid.HOTBAR:
                self._drop(self.hotbar.slots, index)
            elif self.backpack is not None:
                self._drop(self.backpack.slots, index)

    def _close_menus(self) -> None:
        if self.grid_open:
            self._toggle_grid()
        self.craft_open = False

    # --- the Esc menu ----------------------------------------------------
    def _open_pause(self) -> None:
        self._close_menus()
        self.pause_open = True
        self.pause_cursor = 0
        self._held_keys.clear()  # see _open_settings

    def _pause_key(self, key: int) -> None:
        controls = self.controls
        rows = len(_PAUSE_ROWS)
        if key == ctl.BACK_KEY:
            self.pause_open = False
        elif key == pygame.K_UP or controls.is_key(key, ctl.MOVE_UP):
            self.pause_cursor = (self.pause_cursor - 1) % rows
        elif key == pygame.K_DOWN or controls.is_key(key, ctl.MOVE_DOWN):
            self.pause_cursor = (self.pause_cursor + 1) % rows
        elif key in _CONFIRM_KEYS or controls.is_key(key, ctl.ACTION):
            choice = _PAUSE_ROWS[self.pause_cursor][0]
            if choice == RESUME:
                self.pause_open = False
            elif choice == KEYS:
                self._open_settings()
            elif choice == QUIT and self.manager is not None:
                self.manager.pop()  # on_exit saves

    # --- saving ------------------------------------------------------------
    def on_exit(self) -> None:
        if self.save_slot is not None:
            saves.save(self, self.save_slot, self.save_folder)

    def use_controls(self, controls: Controls, path: Path | None) -> None:
        """Hand a loaded game the player's current keys, not the saved ones."""
        self.controls = controls
        self.controls_path = path

    # What a save leaves out: pictures (rebuilt from disk), the scene stack,
    # the keyboard's state and the key settings (the player's, not the game's).
    _NOT_SAVED = ("floor", "_field", "manager", "controls", "controls_path", "_held_keys")

    def __getstate__(self) -> dict[str, object]:
        state = dict(self.__dict__)
        for name in self._NOT_SAVED:
            state.pop(name, None)
        return state

    def __setstate__(self, state: dict[str, object]) -> None:
        self.__dict__.update(state)
        self.floor = Floor(self.world)
        self._field = None
        self.controls = Controls()
        self.controls_path = None
        self._held_keys = set()
        # Left from the Esc menu, so it was open; arrive back in the game.
        self.pause_open = False
        self.settings_open = False
        self.settings_waiting = False

    # --- the key settings screen -----------------------------------------
    def _open_settings(self) -> None:
        self._close_menus()
        self.settings_open = True
        self.settings_cursor = 0
        self.settings_waiting = False
        # Whatever was held would stay held otherwise, and walk on by itself
        # once the screen closes, because its key-up went to the menu.
        self._held_keys.clear()

    def _settings_key(self, key: int) -> None:
        rows = len(ctl.ACTIONS) + 1  # the last row puts everything back
        if self.settings_waiting:
            self.settings_waiting = False
            if key == ctl.BACK_KEY:
                return  # cancelled, nothing changed
            if self.controls.rebind(ctl.ACTIONS[self.settings_cursor], key):
                self._save_controls()
            else:
                self._say(f"{ctl.key_label(key)} 키는 쓸 수 없다")
            return
        controls = self.controls
        if key in (ctl.BACK_KEY, ctl.SETTINGS_KEY):
            self.settings_open = False  # back to the Esc menu, if it was open
        elif key == pygame.K_UP or controls.is_key(key, ctl.MOVE_UP):
            self.settings_cursor = (self.settings_cursor - 1) % rows
        elif key == pygame.K_DOWN or controls.is_key(key, ctl.MOVE_DOWN):
            self.settings_cursor = (self.settings_cursor + 1) % rows
        elif key in _CONFIRM_KEYS or controls.is_key(key, ctl.ACTION):
            if self.settings_cursor == len(ctl.ACTIONS):
                controls.reset()
                self._save_controls()
            else:
                self.settings_waiting = True

    def _save_controls(self) -> None:
        if self.controls_path is None:
            return
        try:
            self.controls.save(self.controls_path)
        except OSError:
            self._say("키 설정을 저장하지 못했다")

    def _eat_held(self) -> bool:
        """Use up whatever is in hand, if it is food.

        Refused on a full tank rather than spent for nothing: a stack quietly
        eaten to no effect is worse than the key doing nothing. Returns True
        whenever the hand held food, so the same press does not also swing.
        """
        held = self.hotbar.active_stack
        if held is None:
            return False
        kind = held.kind
        if kind not in consume.EDIBLE:
            return False
        if not consume.eat(kind, self.player):
            self._say(f"{kind.name} — 지금은 필요 없다")
            return True
        self._spend(kind, 1)
        self._say(f"{kind.name}{_object_particle(kind.name)} 먹었다")
        return True

    @property
    def on_ice(self) -> bool:
        # The map's own ice, and whatever a fight has frozen since. Reading
        # only the first meant a coldsnap's frost was something to look at.
        return ice.holds(self.player.pos, self.ice) or gimmicks.slippery(
            self.player.pos, self.patches
        )

    @property
    def in_waste(self) -> bool:
        return self.world.biome_at(self.player.pos) is biomes.WASTELAND

    @property
    def sandstorm(self) -> float:
        """How hard the grit is blowing here, 0 outside the wasteland."""
        return weather.sandstorm_at(self.clock.elapsed) if self.in_waste else 0.0

    @property
    def in_mire(self) -> bool:
        return mires.holds(self.player.pos, self.mires)

    @property
    def wind_colour(self) -> tuple[int, int, int]:
        """Green normally; the bog's own colour while it is being taken.

        Empty reads differently again, because a bar that merely sits at zero
        does not say WHY nothing is happening when the dodge key stops working.
        """
        if self.player.winded:
            return config.WIND_EMPTY_COLOR
        if self.in_mire:
            return config.WIND_BOG_COLOR
        if self.sandstorm > config.SAND_NOTICEABLE:
            return config.WIND_SAND_COLOR
        return config.WIND_COLOR

    @property
    def sprinting(self) -> bool:
        return self.controls.any_held(self._held_keys, ctl.SPRINT)

    def _move_dir(self) -> pygame.Vector2:
        held, controls = self._held_keys, self.controls
        direction = pygame.Vector2(0, 0)
        if controls.any_held(held, ctl.MOVE_UP):
            direction.y -= 1
        if controls.any_held(held, ctl.MOVE_DOWN):
            direction.y += 1
        if controls.any_held(held, ctl.MOVE_LEFT):
            direction.x -= 1
        if controls.any_held(held, ctl.MOVE_RIGHT):
            direction.x += 1
        return direction

    # --- logic -----------------------------------------------------------
    def update(self, dt: float) -> None:
        if self.backpack is None:
            # A save from before the base inventory existed loads without one.
            self.backpack = Container.empty(config.BASE_INVENTORY_SLOTS)
        # consumed once per step whether or not we are dead, so a press during
        # the respawn wait cannot queue up an action for the frame we come back
        dodge = self._dodge_pressed
        sync = self._sync_pressed
        self._dodge_pressed = False
        self._sync_pressed = False

        # Settled before anything moves, the clock included. A run that keeps
        # running underneath its own ending is not an ending, it is a
        # notification -- and a day counter still climbing behind the words
        # "버텼다" is the clearest way to say the game did not notice.
        self.ending.update(
            sigils_taken=self.core.sigils_taken,
            is_night=self.clock.is_night,
            core_destroyed=self.core.is_destroyed,
        )
        if self.ending.over:
            return

        day = self.clock.day
        self.clock.update(dt)
        if self.clock.day != day and self.save_slot is not None:
            # Autosave at dawn, so a crash costs at most the day in progress.
            # The one place update writes to disk, and only for a game in a
            # slot -- a test's scene has none.
            saves.save(self, self.save_slot, self.save_folder)
        self.note_left = max(0.0, self.note_left - dt)
        self._tick_loot(dt)
        self._tick_dropped(dt)
        for station in self.stations:
            station.update(dt)

        self._swing_left = max(0.0, self._swing_left - dt)
        if self.grid_open or self.craft_open or self.settings_open or self.pause_open:
            return  # the world waits while a screen is open

        down = self._respawn_timer > 0
        if down:
            self._respawn_timer -= dt
            if self._respawn_timer <= 0:
                self.player.pos = pygame.Vector2(self.core.pos)
                self.player.hp = self.player.max_hp
                self.player.iframe_timer = config.RESPAWN_IFRAMES
                down = False

        if not down:
            self._update_living(dt, dodge, sync)

        # The camera keeps following even while down, so the wait shows the
        # world carrying on rather than a frozen frame. Inside a temple it
        # follows nothing: one room fills the screen, and a view that drifted
        # with the player would push the far wall and its doors off the edge
        # of the very thing they are meant to be read from.
        #
        # AFTER the player moves. Before, the view sat one step behind, and
        # the 3.33 px step left a fraction that cycled through thirds -- drawn
        # without it, the player shivered a pixel side to side while walking.
        self.camera.update(dt, self.inside.pos if self.inside is not None else self.player.pos)

        # The world does not stop for a death: golems keep walking, shots keep
        # flying, and what was chasing the player is still out there on the way
        # back. Only the player's own half of the step waits.
        combat.update_projectiles(
            dt,
            self.projectiles,
            self.enemies,
            self.world,
            boss=self.boss,
            standing=self._breakables(),
            patches=self.patches,
            marks=self.marks,
            timers=self.mark_timers,
            from_pos=self.player.pos,
        )
        gimmicks.update_patches(dt, self.patches)
        # The floor is the floor. Until now every patch a trick or a glyph
        # left was decoration: ``touch`` was written for this and never
        # called from anywhere, and nothing ever asked what a golem was
        # standing in.
        gimmicks.touch(
            dt,
            self.player,
            self.patches,
            # Where they are actually heading, which on ice is not where they
            # are pushing -- and wading is what the bog charges for.
            moving=self.player.slide.length_squared() > 0,
        )
        standing: list[gimmicks.Standing] = [*self.enemies]
        if self.boss is not None:
            standing.append(self.boss)
        gimmicks.wade(dt, standing, self.patches)
        gimmicks.update_marks(dt, self.marks, self.mark_timers)
        self._update_boss(dt)
        combat.update_enemies(
            dt, self.enemies, self.player, self.world, self.core, raid=self.is_raid
        )
        self.spawner.update(dt, self.fragments, self.core, self.rng, self.world, self.player.pos)
        self.tree_spawner.update(
            dt, self.fragments, self.core, self.tree_rng, self.world, self.player.pos
        )
        self.enemy_spawner.update(
            dt,
            self.enemies,
            self.player.pos,
            self.core,
            self.rng,
            self.world,
            raid=self.is_raid,
            last_stand=self.is_last_stand,
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
            # Back to the base inventory, empty: everything went in the pile.
            self.backpack = Container.empty(config.BASE_INVENTORY_SLOTS)
            self.worn_pack = None
            self._respawn_timer = config.RESPAWN_DELAY

    @property
    def defeated(self) -> bool:
        """Kept as a name because it reads better than ``ending.outcome``."""
        return self.ending.outcome == ending_rules.LOST

    @property
    def won(self) -> bool:
        return self.ending.outcome == ending_rules.WON

    @property
    def is_last_stand(self) -> bool:
        """The one night after the fifth sigil comes home."""
        return self.ending.standing

    @property
    def is_raid(self) -> bool:
        """Whether the ward is open tonight.

        Only ever at night. A raid is a night the wall comes down, and one
        running through the afternoon would make the word meaningless.
        """
        if self.ending.standing:
            return True  # the last night is a raid whether the calendar says so or not
        return self.clock.is_night and raids.is_raid_night(self.clock.day, self.core.bosses_killed)

    @property
    def days_to_raid(self) -> int:
        return raids.days_until(self.clock.day, self.core.bosses_killed)

    @property
    def ward_colour(self) -> tuple[int, int, int]:
        """Red on a raid night. The wall being down has to read from inside."""
        return config.WARD_BROKEN_COLOR if self.is_raid else config.WARD_COLOR

    def _update_living(self, dt: float, dodge: bool, sync: bool) -> None:
        """The half of a step that only happens while the player is on their feet."""
        move = self._move_dir()
        self.player.update(dt, move, self.world, dodge, self.sprinting, slippery=self.on_ice)
        self.facing = aim.face(move, self.facing)

        tool = self.hotbar.active_tool
        _, mined, self._dig_timer = mining.update_mining(
            dt,
            active_tool=tool,
            held=self._action_held,
            facing=self.facing,
            player_pos=self.player.pos,
            fragments=self.fragments,
            backpack=self.backpack,
            hotbar=self.hotbar,
            player=self.player,
            swing_timer=self._dig_timer,
        )
        for kind in mined:
            self._wear_if_pack(kind)
        # Magic is drawn, not pressed, so the action key always means the
        # weapon -- and the staff always cools, slung or in hand: put away to
        # swing something else, it should not come back out as hot as it went in.
        self._cast_drawn(dt)
        self._swing(dt, tool)
        survival.update_regen(dt, self.player, self.core)
        survival.update_mire(
            dt, self.player, self.mires, moving=self._move_dir().length_squared() > 0
        )
        if falling.update_fall(dt, self.player, self.chasms):
            self._say("발을 헛디뎠다")
        survival.update_stamina(dt, self.player, regen_mult=weather.regen_mult(self.sandstorm))
        survival.update_lava(dt, self.player, self.lava)
        status.update_burn(dt, self.player, at_source=self.in_lava)

        self._visit_temples()
        if sync:
            self._open_structure()
            self._open_chest()
            self._wake_boss()
        if sync and self.core.is_in_sync_range(self.player.pos):
            if self.core.ignited:
                # Mending first. The same key already means "deal with the
                # core", and after a raid the urgent business is the cracks.
                self._spend(STONE, self.core.repair(self._carried(STONE)))
                # A boss's sigil, if one is being carried. The cap opens HERE
                # rather than where the boss died, which is what turns a win
                # five biomes out into a walk home.
                if self._carried(CORE_SIGIL) and self.core.offer_sigil():
                    self._spend(CORE_SIGIL, 1)
                    self._say(f"코어가 인장을 받았다 · 한계 {self.core.level_cap}")
            elif self._carried(CORE_SHARD) >= config.CORE_SHARDS_TO_IGNITE:
                self._spend(CORE_SHARD, config.CORE_SHARDS_TO_IGNITE)
                self.core.ignite()

        self._recover_underfoot()
        self._collect_stations()
        self._gather_underfoot()

    # --- rendering -------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        # About once a second, look for art saved since it was read (the
        # asset library exports a PNG the moment its Aseprite file is saved),
        # so an edit shows up in the running game without a restart.
        self._art_frames += 1
        if self._art_frames >= config.FPS:
            self._art_frames = 0
            art.refresh()
        # The world is drawn onto a FIELD the size the zoom asks for, then
        # scaled down onto the window. Drawing it straight at screen size and
        # scaling each shape instead would mean a zoom factor at every radius,
        # every rect and every line in this file; this way the whole field
        # keeps drawing in world pixels and knows nothing about the wheel.
        #
        # At 1.0 there is no second surface and no scale -- the ordinary case
        # pays nothing.
        field = self._field_surface(surface)
        self._draw_field(field)
        if field is not surface:
            # Nearest-neighbour. Every zoom step lands a 32-pixel tile on a
            # whole number of pixels, so this stays sharp; smoothscale would
            # blur pixel art that was drawn to be read.
            pygame.transform.scale(field, surface.get_size(), surface)
        # Screen effects, not world ones: the raid border has to hug the real
        # edge of the window, not the edge of a field that may be twice its
        # size.
        self._draw_sandstorm(surface)
        self._draw_burning(surface)
        self._draw_raid_edge(surface)
        self._draw_boss_bar(surface)
        self._draw_spellbook(surface)
        self._draw_drawing(surface)
        self._draw_hud(surface)
        # Markers last, so one is never lost behind the gauges. A ruin you
        # cannot see is a ruin you walk past. Each label carries its own
        # backing so both stay readable.
        self._draw_compass(surface)
        self._draw_detector(surface)
        self._draw_grid(surface)
        self._draw_craft(surface)
        self._draw_pause(surface)
        self._draw_settings(surface)
        # Over everything, including the open screens: once a run is over
        # there is nothing left to read behind it.
        self._draw_ending(surface)

    def _draw_ending(self, surface: pygame.Surface) -> None:
        """What a finished run looks like: the world dimmed, and one line.

        Deliberately plain. The screen's job is to say which of the two things
        happened and let the player stop looking at it -- a results table would
        be asking them to study a run they can no longer change.
        """
        if not self.ending.over:
            return
        scale = config.UI_SCALE
        width, height = surface.get_size()

        wash = pygame.Surface((width, height), pygame.SRCALPHA)
        wash.fill((*config.ENDING_WASH, config.ENDING_ALPHA))
        surface.blit(wash, (0, 0))

        won = self.won
        title = "버텼다" if won else "코어가 꺼졌다"
        under = (
            f"{self.clock.day}일째 아침 · 인장 {self.core.sigils_taken}개"
            if won
            else f"{self.clock.day}일째 · 보스 {self.core.bosses_killed}마리"
        )
        colour = config.ENDING_WON_COLOR if won else config.ENDING_LOST_COLOR

        head = _font(26 * scale).render(title, True, colour)
        surface.blit(head, head.get_rect(center=(width // 2, height // 2 - 14 * scale)))
        tail = _font(10 * scale).render(under, True, config.WHITE)
        surface.blit(tail, tail.get_rect(center=(width // 2, height // 2 + 16 * scale)))

    def _field_surface(self, surface: pygame.Surface) -> pygame.Surface:
        """The surface the world is drawn onto, kept between frames.

        At zoom 1.0 that is the window itself. Otherwise it is one surface of
        the field's size, reused -- a fresh 1920x1080 allocation every frame
        would cost more than the drawing does.
        """
        wanted = self.camera.field_size
        if wanted == surface.get_size():
            return surface
        if self._field is None or self._field.get_size() != wanted:
            self._field = pygame.Surface(wanted)
        return self._field

    def _draw_field(self, surface: pygame.Surface) -> None:
        """Everything that lives in the world, in world pixels."""
        self._draw_world(surface)
        self._draw_lava(surface)  # ground, so under everything that stands on it
        self._draw_mires(surface)
        self._draw_chasms(surface)
        self._draw_ice(surface)
        self._draw_ward(surface)
        self._draw_temples(surface)
        self._draw_structures(surface)
        self._draw_stations(surface)
        self._draw_nodes(surface)
        # Night falls on the GROUND. Everything alive, everything in flight and
        # everything on a clock is drawn over it, because a wolf you cannot
        # tell from yourself is not atmosphere, it is a lost fight -- and a
        # loot pile with five minutes left should not be hidden by the hour.
        self._draw_patches(surface)  # ground, so under what stands on it
        self._draw_night(surface)
        self._draw_loot(surface)
        self._draw_dropped(surface)
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
        self._draw_charge_lane(surface)  # a promise, so under what is real
        self._draw_tricks(surface)  # over the floor, under everything alive
        self._draw_boss(surface)  # under the player, who must never be hidden
        self._draw_hitboxes(surface)
        self._draw_node_bars(surface)  # over the reach-fan that is denting them
        at = self.camera.world_to_screen(self.player.pos)
        pygame.draw.circle(surface, config.PLAYER_COLOR, at, self.player.radius)
        self._draw_facing(surface, at)
        if self.player.shocked:
            # Shown on the body rather than in the corner: what it takes away
            # is the dodge, and the dodge is pressed while looking here.
            pygame.draw.circle(surface, config.SHOCK_COLOR, at, self.player.radius + 5, 2)

    def _draw_facing(self, surface: pygame.Surface, at: pygame.Vector2) -> None:
        """A small wedge on the body's rim, pointing where a swing will go."""
        if self.facing.length_squared() == 0:
            return
        ahead = self.facing.normalize()
        side = pygame.Vector2(-ahead.y, ahead.x)
        tip = at + ahead * (self.player.radius + 7)
        base = at + ahead * (self.player.radius + 1)
        pygame.draw.polygon(surface, config.WHITE, [tip, base + side * 5, base - side * 5])

    def _draw_hitboxes(self, surface: pygame.Surface) -> None:
        """Every box that is about to decide something, in red.

        Two different questions, drawn the same way on purpose: what is about
        to hit the player, and what the player is about to hit. Neither was
        drawn before -- a golem simply drained you for standing near it, and
        the reach of a pick was something you learned by failing to dig.

        A golem's ring CLOSES as its wind-up runs out, so the shape says when
        as well as where. A flat ring would be a warning light.
        """
        layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        shade = (*config.HITBOX_COLOR, config.HITBOX_FILL)
        edge = (*config.HITBOX_COLOR, 255)

        for enemy in self.enemies:
            if enemy.phase is enemy_swing.WALK and enemy.flash <= 0:
                continue
            at = self.camera.world_to_screen(enemy.pos)
            span = int(enemy.reach + self.player.radius)
            if enemy.flash > 0:
                pygame.draw.circle(layer, shade, at, span)
            pygame.draw.circle(layer, edge, at, span, config.HITBOX_EDGE)
            if enemy.wound:
                pygame.draw.circle(layer, edge, at, int(span * enemy.wound), 2)

        self._draw_player_box(layer, shade, edge)
        surface.blit(layer, (0, 0))

    def _draw_player_box(
        self,
        layer: pygame.Surface,
        shade: tuple[int, int, int, int],
        edge: tuple[int, int, int, int],
    ) -> None:
        """The fan the held tool would land in, while it is being used.

        Only while the key is down. A red wedge permanently stuck to the
        player would be the first thing on screen at every moment and the
        last thing anybody still reads after five minutes.
        """
        tool = self.hotbar.active_tool
        if tool is None or not (self._action_held or self._swing_left > 0):
            return
        reach = getattr(tool, "reach", None) or getattr(tool, "range", None)
        if not reach or self.facing.length_squared() == 0:
            return
        at = self.camera.world_to_screen(self.player.pos)
        heading = math.atan2(self.facing.y, self.facing.x)
        half = math.radians(config.AIM_HALF_ANGLE)
        points = [pygame.Vector2(at)]
        for n in range(13):
            angle = heading - half + 2 * half * n / 12
            points.append(at + pygame.Vector2(math.cos(angle), math.sin(angle)) * reach)
        pygame.draw.polygon(layer, shade, points)
        pygame.draw.lines(layer, edge, True, points, 2)

    def _draw_pause(self, surface: pygame.Surface) -> None:
        """The Esc menu: a short list over the dimmed, waiting world."""
        if not self.pause_open or self.settings_open:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))
        row_h = 34
        panel = pygame.Rect(0, 0, 280, len(_PAUSE_ROWS) * row_h + 84)
        panel.center = (surface.get_width() // 2, surface.get_height() // 2)
        pygame.draw.rect(surface, config.GRID_PANEL, panel, border_radius=6)
        title = _font(18).render("설정", True, config.WHITE)
        surface.blit(title, title.get_rect(midtop=(panel.centerx, panel.top + 14)))
        top = panel.top + 50
        for index, (_, name) in enumerate(_PAUSE_ROWS):
            rect = pygame.Rect(panel.left + 16, top + index * row_h, panel.width - 32, row_h - 4)
            chosen = index == self.pause_cursor
            fill = (64, 64, 84) if chosen else (48, 48, 62)
            pygame.draw.rect(surface, fill, rect, border_radius=4)
            if chosen:
                pygame.draw.rect(surface, config.WHITE, rect, 2, border_radius=4)
            label = _font(15).render(name, True, config.WHITE)
            surface.blit(label, label.get_rect(center=rect.center))
        hint = _font(12).render("↑↓ 고르기 · Enter 선택 · Esc 닫기", True, (170, 170, 185))
        surface.blit(hint, hint.get_rect(midbottom=(panel.centerx, panel.bottom - 8)))

    def _draw_settings(self, surface: pygame.Surface) -> None:
        """The key list: what each does, and what it is bound to now."""
        if not self.settings_open:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))
        row_h = 20
        rows = len(ctl.ACTIONS) + 1
        panel = pygame.Rect(0, 0, 440, rows * row_h + 64)
        panel.center = (surface.get_width() // 2, surface.get_height() // 2)
        pygame.draw.rect(surface, config.GRID_PANEL, panel, border_radius=6)
        title = _font(15).render("키 설정", True, config.WHITE)
        surface.blit(title, (panel.left + 14, panel.top + 10))
        hint = (
            "새 키를 누르세요 · Esc 취소"
            if self.settings_waiting
            else "↑↓ 고르기 · Enter 바꾸기 · Esc 닫기"
        )
        tip = _font(12).render(hint, True, (170, 170, 185))
        surface.blit(tip, (panel.right - tip.get_width() - 14, panel.top + 13))
        top = panel.top + 40
        for index in range(rows):
            rect = pygame.Rect(panel.left + 10, top + index * row_h, panel.width - 20, row_h - 2)
            chosen = index == self.settings_cursor
            if chosen:
                pygame.draw.rect(surface, (64, 64, 84), rect, border_radius=3)
            if index == len(ctl.ACTIONS):
                label = _font(13).render("기본값으로 되돌리기", True, config.WHITE)
                surface.blit(label, (rect.left + 6, rect.top + 2))
                continue
            action = ctl.ACTIONS[index]
            label = _font(13).render(ctl.LABELS[action], True, config.WHITE)
            surface.blit(label, (rect.left + 6, rect.top + 2))
            if chosen and self.settings_waiting:
                bound, ink = "...", config.LOOT_COLOR
            else:
                bound = " / ".join(ctl.key_label(k) for k in self.controls.keys_for(action))
                ink = (200, 200, 215)
            keys = _font(13).render(bound, True, ink)
            surface.blit(keys, (rect.right - keys.get_width() - 6, rect.top + 2))

    # --- the belongings screen -------------------------------------------
    def _toggle_grid(self) -> None:
        self.grid_open = not self.grid_open
        if self.grid_open:
            self.craft_open = False  # one screen at a time
            self.grid_cursor = (grid.HOTBAR, self.hotbar.selected)
        else:
            self.grid.close(self.backpack, self.hotbar)

    # --- the crafting menu ------------------------------------------------
    def _toggle_craft(self) -> None:
        self.craft_open = not self.craft_open
        if self.craft_open:
            self.craft_cursor = 0
            if self.grid_open:
                self.grid.close(self.backpack, self.hotbar)
            self.grid_open = False

    # --- the carving screen -----------------------------------------------
    def flagged_ruins(self) -> list[Structure]:
        """Unopened ruins close enough to be worth pointing at."""
        return [
            site
            for site in self.structures
            if not site.opened and self.player.pos.distance_to(site.pos) <= config.RUIN_SIGHTING
        ]

    @property
    def holding_staff(self) -> bool:
        held = self.hotbar.active_stack
        return held is not None and held.kind in STAFF_ITEMS

    def _cast_drawn(self, dt: float) -> None:
        """Finish a shape, and throw it if it can be thrown.

        Everything can fail quietly except the last line. A shape nobody knows
        and a shape drawn bare-handed are both just nothing happening; a shape
        the player HAS learned, drawn with a staff in hand that is locked out,
        is the one case worth a word -- otherwise an overload reads as the
        drawing having failed.
        """
        self.staff.update(dt)
        glyph = self.drawing.update(dt)
        if glyph is None:
            return
        if not self.holding_staff:
            return
        if not self.grimoire.knows(glyph):
            self._say("모르는 모양이다")
            return
        if self.staff.overloaded:
            self._say(f"지팡이가 식는 중 · {self.staff.lockout:.1f}초")
            return
        thrown = self.staff.fire(glyph)
        if thrown is None:
            return
        if self.facing.length_squared() == 0:
            return
        self.projectiles.append(
            Projectile(
                pos=pygame.Vector2(self.player.pos),
                vel=self.facing.normalize() * config.PROJECTILE_SPEED,
                damage=self.staff.power_of(thrown),
                radius=config.PROJECTILE_RADIUS,
                ttl=self.staff.range_of(),
                gimmick=thrown.gimmick if thrown.tier == glyph_table.SUPREME else None,
            )
        )

    def _swing(self, dt: float, tool: object | None) -> None:
        """Sweep the weapon through the fan in front, on its own beat."""
        targets: list[combat.Hurtable] = [*self.enemies, *self.beasts, *self._breakables()]
        if self.boss is not None:
            targets.insert(0, self.boss)
        before = self._fire_timer
        self._fire_timer, hit = combat.swing_weapon(
            dt,
            weapon=tool,
            held=self._action_held,
            facing=self.facing,
            player_pos=self.player.pos,
            fire_timer=self._fire_timer,
            targets=targets,
        )
        if self._fire_timer > before:  # a swing went round, hit or miss
            self._swing_left = config.SWING_FLASH
        if any(target.is_dead for target in hit):
            # Beasts are cleared (and drop their makings) by update_beasts.
            self.enemies[:] = [e for e in self.enemies if not e.is_dead]

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

    def _step_craft(self, dy: int) -> None:
        shown = min(len(self._craft_rows()), config.CRAFT_ROWS_VISIBLE)
        if shown:
            self.craft_cursor = (self.craft_cursor + dy) % shown

    def _confirm_craft(self) -> None:
        """Make the recipe under the cursor, if it can be afforded."""
        rows = self._craft_rows()[: config.CRAFT_ROWS_VISIBLE]
        if not rows:
            return
        self.craft_cursor = min(self.craft_cursor, len(rows) - 1)
        recipe, afford = rows[self.craft_cursor]
        if not afford:
            return
        if recipe.seconds > 0:
            self._start_job(recipe)
        else:
            crafting.craft(recipe, self.backpack, self.hotbar)

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
            if index == self.craft_cursor:
                pygame.draw.rect(surface, config.WHITE, rect, 2, border_radius=3)
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

    def _confirm_grid(self) -> None:
        """Pick up or put down at the cursor -- the pure Grid does the rest.

        A drop the hotbar turns away is told, not merely ignored. A cursor
        that stops working with no word for it reads as the key being broken.
        """
        where, index = self.grid_cursor
        self.grid.click(where, index, self.backpack, self.hotbar)
        if self.grid.refused:
            self.grid.refused = False
            self._say("핫바에는 쓸 수 있는 것만")

    def _step_grid(self, dx: int, dy: int) -> None:
        """Move the cursor a cell, stepping between the pack and the hotbar.

        The pack sits above the hotbar, so walking off the bottom of the pack
        lands on the hotbar and walking off its top climbs back into the pack.
        Left and right wrap round within a row.
        """
        where, index = self.grid_cursor
        cols = config.GRID_COLS
        size = self.backpack.size if self.backpack is not None else 0
        belt = len(self.hotbar.slots)
        if where == grid.HOTBAR:
            if dx:
                self.grid_cursor = (grid.HOTBAR, (index + dx) % belt)
            elif dy < 0 and size:
                last_row = (size - 1) // cols
                self.grid_cursor = (grid.PACK, min(last_row * cols + index, size - 1))
            return
        row, col = divmod(index, cols)
        if dx:
            row_len = min(cols, size - row * cols)
            self.grid_cursor = (grid.PACK, row * cols + (col + dx) % row_len)
        elif dy > 0:
            below = index + cols
            if below < size:
                self.grid_cursor = (grid.PACK, below)
            else:
                self.grid_cursor = (grid.HOTBAR, min(col, belt - 1))
        elif dy < 0 and row > 0:
            self.grid_cursor = (grid.PACK, index - cols)

    def _cursor_rect(self) -> pygame.Rect:
        where, index = self.grid_cursor
        if where == grid.HOTBAR:
            return self._cell_rect(self._pack_rows() + 1, index)  # +1 leaves a gap
        return self._cell_rect(*divmod(index, config.GRID_COLS))

    def _draw_grid(self, surface: pygame.Surface) -> None:
        """The pack above, the hotbar below, and whatever is in hand on top."""
        if not self.grid_open:
            return
        rows = self._pack_rows()
        grid_x, grid_y = self._grid_origin()
        step = config.GRID_CELL + config.GRID_GAP
        grid_width = config.GRID_COLS * step - config.GRID_GAP
        grid_bottom = grid_y + (rows + 1) * step + config.GRID_CELL
        panel = pygame.Rect(
            grid_x - 24,
            grid_y - 52,
            grid_width + 48,
            grid_bottom - grid_y + 64,
        )
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))
        _draw_frame(surface, panel)
        header = pygame.Rect(panel.left + 8, panel.top + 8, panel.width - 16, 36)
        _draw_frame(surface, header)
        _draw_pixel_icon(
            surface, _BAG_ICON, (header.left + 24, header.centery), _BAG_COLOR, config.UI_SCALE * 2
        )
        title = _font(14 * config.UI_SCALE).render("인벤토리", True, config.WHITE)
        surface.blit(title, (header.left + 48, header.centery - title.get_height() // 2))
        hovered: object | None = None

        for row in range(rows):
            for col in range(config.GRID_COLS):
                index = row * config.GRID_COLS + col
                if self.backpack is None or index >= self.backpack.size:
                    break
                rect = self._cell_rect(row, col)
                slot = self.backpack.slots[index]
                self._draw_cell(surface, rect, slot)
                if self.grid_cursor == (grid.PACK, index):
                    hovered = slot
        # The hotbar holds tools as well as stacks, so its slots are wider than
        # the pack's. Named apart rather than reusing the loop above's, which
        # mypy had already pinned to the narrower one.
        for col, belt_slot in enumerate(self.hotbar.slots):
            rect = self._cell_rect(rows + 1, col)
            self._draw_cell(surface, rect, belt_slot, selected=col == self.hotbar.selected)
            if self.grid_cursor == (grid.HOTBAR, col):
                hovered = belt_slot

        cursor = self._cursor_rect()
        pygame.draw.rect(surface, config.WHITE, cursor.inflate(6, 6), 2, border_radius=4)
        held = self.grid.held
        if held is not None:
            # Lifted up and to the side of the cursor, so what is under it
            # still shows.
            at = pygame.Rect(0, 0, config.GRID_CELL - 10, config.GRID_CELL - 10)
            at.center = (cursor.right - 6, cursor.top + 6)
            self._draw_contents(surface, at, held)
        elif hovered is not None:
            self._draw_item_tooltip(surface, hovered, cursor)

    def _draw_item_tooltip(self, surface: pygame.Surface, slot: object, cell: pygame.Rect) -> None:
        name = slot.kind.name if isinstance(slot, Stack) else getattr(slot, "name", "")
        if not name:
            return
        label = name if not isinstance(slot, Stack) else f"{name}  x{slot.count}"
        text = _font(11 * config.UI_SCALE).render(label, True, config.WHITE)
        pad = 12 * config.UI_SCALE
        # As wide as its words (never narrower than the old fixed box), so a
        # long name is not cut off.
        width = max(160 * config.UI_SCALE, text.get_width() + 2 * pad)
        height = 24 * config.UI_SCALE
        left = min(cell.centerx + 18, surface.get_width() - width - 8)
        top = min(cell.bottom + 6, surface.get_height() - height - 8)
        box = pygame.Rect(max(8, left), max(8, top), width, height)
        _draw_frame(surface, box)
        surface.blit(text, (box.left + pad, box.top + (height - text.get_height()) // 2))

    def _draw_cell(
        self, surface: pygame.Surface, rect: pygame.Rect, slot: object, *, selected: bool = False
    ) -> None:
        _draw_frame(surface, rect, selected=selected)
        if slot is not None:
            self._draw_contents(surface, rect.inflate(-10, -10), slot)

    def _draw_contents(self, surface: pygame.Surface, rect: pygame.Rect, slot: object) -> None:
        """Resource icons with stack meters, or colour blocks for other items."""
        if isinstance(slot, Stack):
            art = resource_image(slot.kind, min(rect.size))
            if art is None:
                pygame.draw.rect(surface, slot.kind.color, rect, border_radius=2)
            else:
                surface.blit(art, art.get_rect(center=rect.center))
            filled = max(1, int(rect.width * slot.count / slot.kind.stack_max))
            pygame.draw.rect(
                surface, config.WHITE, pygame.Rect(rect.left, rect.bottom - 3, filled, 3)
            )
        else:
            pygame.draw.rect(surface, (200, 200, 215), rect, border_radius=2)

    def _draw_world(self, surface: pygame.Surface) -> None:
        """Paint the map's floor from each biome's own tiles.

        The flat-colour wedges this replaced drew the sectors exactly, which was
        the right placeholder and the wrong floor: a biome you walk across for
        twenty screens needs texture to read as ground at all. ``Biome.color``
        stays -- the map pointer, the glyph list and the locator all still speak
        in it.
        """
        self.floor.draw(surface, self.camera)

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

    def _place_spot(self) -> pygame.Vector2:
        """Where a station would go: just clear of the player, in front."""
        gap = self.player.radius + config.STATION_RADIUS + 4
        return aim.ahead(self.player.pos, self.facing, gap)

    def _try_place(self) -> bool:
        """Put down the selected station item in front, if that is what is held.

        Returns True when the press was spent on building, so the same press
        does not also start swinging a tool at whatever is underneath.
        """
        held = self.hotbar.active_stack
        if held is None or held.kind not in STATION_OF:
            return False
        if not place(held.kind, self._place_spot(), self.stations, self.core):
            self._say("여기에는 놓을 수 없다")
            return True  # the press was a build attempt; it simply failed
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
        """Resource sprites or coloured nodes, and nothing drawn around them.

        Nodes in reach used to get a ring (red when the tool could not take
        them). With the ground evenly wooded it lit up around the player
        everywhere they walked, so it went. That ring was also the only sign
        a node refuses the tool in hand; nothing replaces it yet.

        A node that yields something OTHER than itself is drawn with a fleck of
        what is in it. Only the obsidian stone by the lava does that today, and
        without the fleck it reads as an ordinary dark pebble -- a poor look for
        the one thing that opens the whole second ladder.
        """
        for node in sorted(self.fragments, key=lambda fragment: fragment.pos.y):
            at = self.camera.world_to_screen(node.pos)
            tree = tree_image(node.kind, node.pos)
            art = tree if tree is not None else world_resource_image(node.kind)
            if tree is not None:
                # The harvest target stays at the trunk, below the canopy.
                if not has_own_shadow(node.kind):  # painted ones need no second
                    shadow = tree_shadow()
                    surface.blit(shadow, shadow.get_rect(center=(round(at.x + 4), round(at.y + 5))))
                surface.blit(
                    tree,
                    tree.get_rect(midbottom=(round(at.x), round(at.y + config.FRAGMENT_RADIUS))),
                )
            elif art is None:
                pygame.draw.circle(surface, node.kind.color, at, config.FRAGMENT_RADIUS)
            else:
                surface.blit(art, art.get_rect(center=(round(at.x), round(at.y))))
            held = yield_of(node.kind)
            if held is not node.kind:
                pygame.draw.circle(surface, held.color, at, config.FRAGMENT_RADIUS * 0.45)
                pygame.draw.circle(surface, config.OBSIDIAN_GLINT, at, config.FRAGMENT_RADIUS * 0.2)

    def _draw_node_bars(self, surface: pygame.Surface) -> None:
        """Every node being worked on, over the top of everything in the world.

        A second pass, and a late one. Drawn with the node it belongs to, a
        bar was swallowed twice over: by the canopy of whatever tree stood
        further down the screen, and by the red reach-fan of the very tool
        that was putting the dent in it.
        """
        for node in self.fragments:
            if node.worked > 0:
                self._draw_worked(surface, node, self.camera.world_to_screen(node.pos))

    def _draw_worked(self, surface: pygame.Surface, node: Fragment, at: pygame.Vector2) -> None:
        """How far through a node is, while it is being worked on.

        A tree takes two and a half seconds of swinging and showed nothing at
        all for them: no chips, no bar, no change. Holding the key at a tree
        that was in fact coming down was indistinguishable from holding it at
        one the axe could not touch, and the honest conclusion to draw from
        that is that the game is broken.
        """
        share = node.worked
        if share <= 0:
            return
        wide = config.NODE_BAR_WIDTH
        top = at.y - config.FRAGMENT_RADIUS - config.NODE_BAR_LIFT
        back = pygame.Rect(round(at.x - wide / 2), round(top), wide, config.NODE_BAR_HEIGHT)
        pygame.draw.rect(surface, config.NODE_BAR_BACK, back)
        done = pygame.Rect(back.left, back.top, round(wide * (1 - share)), back.height)
        pygame.draw.rect(surface, config.NODE_BAR_COLOR, done)

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

    # --- the building behind the door --------------------------------------
    def _visit_temples(self) -> None:
        """Notice the player walking into a temple, and put them inside it.

        Crossing the circle on the map is the door. What is behind it is the
        building -- ``world/dungeon`` -- and from then on the player is in a
        room rather than on the map, until they walk back out of the one they
        came in by.
        """
        if self.inside is not None:
            self._walk_rooms()
            return
        for temple in self.temples:
            if temple.contains(self.player.pos):
                self._enter(temple)
                return

    def _enter(self, temple: Temple) -> None:
        """Step into a temple, at the door of whichever room they left off in."""
        self.inside = temple
        temple.inside = True
        place = temple.interior()
        self.player.pos.update(rooms.arrival(temple.pos, dungeon.SOUTH))
        self._stock_room()
        here = place.room
        self._say(
            f"{temple.biome.name} 사원 · {len(place.rooms)}개의 방"
            if here.kind is dungeon.START
            else f"{temple.biome.name} 사원"
        )

    def _leave_building(self) -> None:
        """Back out onto the map, through the door that was walked in by."""
        temple = self.inside
        if temple is None:
            return
        temple.inside = False
        self.inside = None
        self.enemies = [e for e in self.enemies if not e.guarding]
        # Put down outside the circle, or the next step would walk straight
        # back in.
        away = self.player.pos - temple.pos
        if away.length_squared() == 0:
            away = pygame.Vector2(0, 1)
        self.player.pos.update(temple.pos + away.normalize() * (temple.radius + 40))

    @property
    def standing_in(self) -> Temple | None:
        return self.inside

    @property
    def here(self) -> dungeon.Room | None:
        """The room the player is standing in, if they are inside anything."""
        return self.inside.interior().room if self.inside is not None else None

    def _walk_rooms(self) -> None:
        """Hold the player in the room, and move them on when they take a door."""
        temple = self.inside
        if temple is None:
            return
        place = temple.interior()
        # Whatever is left standing is what the door answers to.
        place.room.standing = sum(1 for e in self.enemies if e.guarding)

        if self.arena.sealed:
            arena.hold(self.player.pos, temple.pos, rooms.arena_radius(), self.arena)
            return

        for way in (dungeon.NORTH, dungeon.EAST, dungeon.WEST, dungeon.SOUTH):
            if not rooms.in_doorway(self.player.pos, temple.pos, way):
                continue
            if way is dungeon.SOUTH and place.room.back is None:
                if place.room.cleared:
                    self._leave_building()
                    return
                break
            if place.through(way) is None:
                continue
            refused = place.locked(way)
            if refused is not None:
                self._say(refused)
                break
            place.walk(way)
            self.player.pos.update(rooms.arrival(temple.pos, place.opposite(way)))
            self._stock_room()
            return
        rooms.hold(self.player.pos, temple.pos, self.player.radius)

    def _stock_room(self) -> None:
        """Stand up whatever is in the room the player just walked into."""
        temple = self.inside
        if temple is None:
            return
        self.enemies = [e for e in self.enemies if not e.guarding]
        here = temple.interior().room
        for spot in rooms.scatter(temple.pos, here.standing, self.rng):
            self.enemies.append(
                Golem(
                    pos=pygame.Vector2(spot),
                    kind=golem_of(temple.biome),
                    scale=config.GUARD_SCALE,
                    guarding=True,
                )
            )

    def _open_chest(self) -> None:
        """Take what this room's chest holds.

        Mostly what the biome is made of, and once in a while one of its
        drawings. The key to the boss's door is in one of them, and which one
        is the only reason to open every chest in the place.
        """
        temple = self.inside
        if temple is None:
            return
        place = temple.interior()
        here = place.room
        if not here.has_chest or here.chest_opened:
            return
        if temple.pos.distance_to(self.player.pos) > config.ALTAR_REACH:
            return
        if not here.cleared:
            self._say("골렘이 아직 서 있다")
            return
        had_key = here.has_key
        if not place.open_chest():
            return
        if self.rng.random() < config.CHEST_GLYPH_CHANCE:
            self._take_glyph(temple)
        else:
            self._take_spoil(temple)
        if had_key:
            self._say("보스 방의 열쇠를 찾았다")

    def _take_glyph(self, temple: Temple) -> None:
        drawings = glyph_table.glyphs_of(temple.biome)
        if not drawings:  # pragma: no cover - every ring biome has them
            return
        glyph = self.rng.choice(list(drawings))
        fresh = self.grimoire.learn(glyph)
        said = "배웠다" if fresh else "— 이미 아는 그림"
        self._say(f"{glyph.name}{_object_particle(glyph.name)} {said}")

    def _take_spoil(self, temple: Temple) -> None:
        """What the biome is made of, by the handful."""
        kinds = [k for k in (temple.biome.material, temple.biome.timber) if k is not None]
        if not kinds:  # pragma: no cover - every ring biome yields something
            return
        kind = self.rng.choice(kinds)
        count = self.rng.randint(config.CHEST_SPOIL_MIN, config.CHEST_SPOIL_MAX)
        carrying.store(kind, count, self.backpack, self.hotbar)
        self._say(f"{kind.name} x{count}")

    def _wake_boss(self) -> None:
        """Lay a hand on the sleeping thing in the middle of the last room."""
        temple = self.inside
        if temple is None or self.boss is not None:
            return
        place = temple.interior()
        here = place.room
        if here.kind is not dungeon.BOSS or here.boss_woken:
            return
        if temple.pos.distance_to(self.player.pos) > config.ALTAR_REACH:
            return
        here.boss_woken = True
        arena.seal(self.arena)
        kind = BOSS_KINDS[biomes.RING_BIOMES.index(temple.biome)]
        self.boss = Boss(pos=pygame.Vector2(temple.pos), kind=kind)
        self.boss_temple = temple
        self.brawl = boss_moves.Brawl(rng=self.rng)
        self._say(f"{kind.name}{_subject_particle(kind.name)} 눈을 뜬다")

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
            self._say(
                f"{glyph.name}{_object_particle(glyph.name)} 배웠다"
                if fresh
                else f"{glyph.name} — 이미 아는 그림"
            )
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

    @property
    def in_lava(self) -> bool:
        return lava.burns(self.player.pos, self.lava)

    @property
    def sinking(self) -> bool:
        """In a mire with nothing left, which is when it starts on blood."""
        return self.in_mire and self.player.winded

    def _draw_burning(self, surface: pygame.Surface) -> None:
        """A wash over the screen while the ground itself is costing health.

        Hot for lava, dark for going under in a mire, and a fainter hot while
        still alight after walking out of one. All three are moments when the
        ground, or something it left on you, is taking health -- and a health
        bar falling with no cause on screen is the kind of thing a player
        blames on the game.
        """
        if self.in_lava:
            colour, alpha = config.LAVA_COLOR, config.LAVA_WASH
        elif self.sinking:
            colour, alpha = config.MIRE_COLOR, config.MIRE_WASH
        elif self.player.burning:
            # Fainter than the lava's: still alight, no longer standing in it.
            colour, alpha = config.LAVA_COLOR, config.BURN_WASH
        else:
            return
        glow = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        glow.fill((*colour, alpha))
        surface.blit(glow, (0, 0))

    def _draw_sandstorm(self, surface: pygame.Surface) -> None:
        """A wash of grit while it is blowing out on the wasteland.

        It hides nothing -- the wasteland's whole point is that there is
        nothing to hide behind -- so this only has to say that the breath is
        coming back slowly, which is otherwise a gauge moving at a speed
        nobody can account for.
        """
        strength = self.sandstorm
        if strength <= 0.01:
            return
        grit = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        grit.fill((*config.SAND_COLOR, int(config.SAND_ALPHA * strength)))
        surface.blit(grit, (0, 0))

    def _draw_ice(self, surface: pygame.Surface) -> None:
        """Sheets of bare ice, paler than the drifts and ringed in blue.

        The snowfield is already white, so the sheet has to be lighter still
        and its rim has to carry the colour -- committing to a run across one
        is a decision made at the edge.
        """
        for sheet in self.ice:
            at = self.camera.world_to_screen(sheet.pos)
            pygame.draw.circle(surface, config.ICE_COLOR, at, sheet.radius)
            pygame.draw.circle(surface, config.ICE_RIM_COLOR, at, sheet.radius, 4)

    def _draw_chasms(self, surface: pygame.Surface) -> None:
        """Holes, drawn dark with a lit rim.

        Darker than anything else on the plateau and ringed in pale stone: the
        rim is the whole of what a player reads here, and it has to be read
        from across a ridge rather than at the edge of it.
        """
        for hole in self.chasms:
            at = self.camera.world_to_screen(hole.pos)
            pygame.draw.circle(surface, config.CHASM_COLOR, at, hole.radius)
            pygame.draw.circle(surface, config.CHASM_RIM_COLOR, at, hole.radius, 5)

    def _draw_mires(self, surface: pygame.Surface) -> None:
        """Patches of mire, drawn like the lava: a fill and a lit rim.

        The edge is what matters -- crossing one is the whole decision -- and
        it has to read against the bog's own dark green before a player is
        already in it.
        """
        for mire in self.mires:
            at = self.camera.world_to_screen(mire.pos)
            pygame.draw.circle(surface, config.MIRE_COLOR, at, mire.radius)
            pygame.draw.circle(surface, config.MIRE_RIM_COLOR, at, mire.radius, 4)

    def _draw_lava(self, surface: pygame.Surface) -> None:
        """Pools, bright enough to read before they are stepped in.

        A lighter rim inside a hot fill: the edge is the only part that
        matters, since the whole decision is whether to cross it.
        """
        for pool in self.lava:
            at = self.camera.world_to_screen(pool.pos)
            pygame.draw.circle(surface, config.LAVA_COLOR, at, pool.radius)
            pygame.draw.circle(surface, config.LAVA_RIM_COLOR, at, pool.radius, 4)

    def _breakables(self) -> list[Pillar | Rod]:
        """What the boss has left standing that a shot can be spent on.

        Columns and rods. Clearing them is the answer to two of the fifteen
        tricks, so they have to be shootable -- and they are listed here
        rather than held as one list on the field, because what each of them
        does while it stands has nothing in common with the other.
        """
        if self.brawl is None:
            return []
        return [*self.brawl.tricks.pillars, *self.brawl.tricks.rods]

    def _update_boss(self, dt: float) -> None:
        """Walk it at the player, bruise whoever stands in it, and bury it.

        It never leaves the room, so the room's own circle is its leash -- the
        same one the sealed door holds the player with.
        """
        boss = self.boss
        if boss is None or self.boss_temple is None:
            return
        temple = self.boss_temple
        # It walks only between blows. Stepping forward through its own
        # wind-up would move the telegraph out from under itself.
        reach = rooms.arena_radius()
        if self.brawl is None or not self.brawl.busy:
            boss.update(dt, self.player.pos, temple.pos, reach)
        if self.brawl is not None:
            self.brawl.update(dt, boss, self.player, temple.pos, reach, patches=self.patches)
        reach = boss.radius + self.player.radius
        if boss.pos.distance_to(self.player.pos) <= reach and self.player.iframe_timer <= 0:
            self.player.hp -= boss.contact_dps * dt
        if boss.is_dead:
            self._bury_boss(boss, temple)

    def _bury_boss(self, boss: Boss, temple: Temple) -> None:
        """Three things open, and one of them has to be carried home.

        The glyph is learned where it fell, the door opens, and the sigil goes
        in the bag -- the cap it buys is granted at the core, which is what
        makes a win five biomes out into a walk back.
        """
        glyph = spoils.glyph_of(boss.kind)
        self.grimoire.learn(glyph)
        temple.boss_killed = True
        self.core.bosses_killed += 1
        arena.release(self.arena)
        self.boss = None
        self.boss_temple = None
        self.brawl = None
        carrying.store(spoils.drop_of(boss.kind), 1, self.backpack, self.hotbar)
        self._say(
            f"{boss.kind.name}{_object_particle(boss.kind.name)} 쓰러뜨렸다"
            f" · {glyph.name}{_object_particle(glyph.name)} 배웠다"
        )

    def _draw_charge_lane(self, surface: pygame.Surface) -> None:
        """The rectangle a charge is about to run down, while it winds.

        Drawn as an outline in the warning colour, like every other telegraph:
        it has not happened yet. It is a PATH rather than a place, which is
        why it is the one blow whose aim keeps turning -- you step out of this
        one sideways rather than leaving a circle.
        """
        brawl = self.brawl
        if brawl is None or self.boss is None:
            return
        if brawl.move != "charge" or brawl.phase != boss_moves.WIND:
            return
        toward = brawl.aim - self.boss.pos
        facing = toward.normalize() if toward.length_squared() else pygame.Vector2(1, 0)
        across = pygame.Vector2(-facing.y, facing.x) * self.boss.radius
        near = self.camera.world_to_screen(self.boss.pos)
        far = self.camera.world_to_screen(self.boss.pos + facing * config.CHARGE_REACH)
        pygame.draw.polygon(
            surface,
            config.WARNING_COLOR,
            [near + across, far + across, far - across, near - across],
            3,
        )

    def _draw_tricks(self, surface: pygame.Surface) -> None:
        """What a boss has in the air: announced circles, fronts, and edges.

        Over the floor and under everything alive. An announced circle is the
        only one drawn as an outline -- it has not happened yet, and a filled
        one would read as a thing already on the ground.
        """
        if self.brawl is None:
            return
        field = self.brawl.tricks
        for spot in field.falling:
            at = self.camera.world_to_screen(spot.pos)
            # Closing in as the warning runs out, so how long is left is read
            # from the shape rather than counted.
            left = max(0.0, spot.left / config.FALL_WARNING)
            pygame.draw.circle(surface, config.WARNING_COLOR, at, int(spot.radius), 3)
            pygame.draw.circle(surface, config.WARNING_COLOR, at, int(spot.radius * (1 - left)), 2)
        for wall in field.walls:
            facing = wall.vel.normalize() if wall.vel.length_squared() else pygame.Vector2(1, 0)
            across = pygame.Vector2(-facing.y, facing.x) * (wall.width / 2)
            at = self.camera.world_to_screen(wall.pos)
            pygame.draw.line(surface, config.FLAME_COLOR, at - across, at + across, int(wall.reach))
        for ring in field.rings:
            if ring.radius >= 1:
                at = self.camera.world_to_screen(ring.pos)
                pygame.draw.circle(surface, config.FLAME_COLOR, at, int(ring.radius), 6)
        for ball in field.balls:
            # A ring around a thrown one, so that the ones which still have a
            # wall to break on are told apart from the shards which do not.
            at = self.camera.world_to_screen(ball.pos)
            pygame.draw.circle(surface, config.FROST_COLOR, at, int(ball.radius))
            if ball.splits:
                pygame.draw.circle(surface, config.WHITE, at, int(ball.radius) + 4, 2)
        for zone in field.zones:
            # Filled faintly rather than outlined: it is a place you are in,
            # not a blow about to land, and an outline would read as a warning
            # for something that has already started.
            at = self.camera.world_to_screen(zone.pos)
            wide = max(1, int(zone.radius))
            skin = pygame.Surface((wide * 2, wide * 2), pygame.SRCALPHA)
            colour = config.SHOCK_COLOR if zone.shock else config.WIND_COLOR
            pygame.draw.circle(skin, (*colour, config.PATCH_ALPHA), (wide, wide), wide)
            surface.blit(skin, (at.x - wide, at.y - wide))
            pygame.draw.circle(surface, colour, at, wide, 3)
        for lob in field.lobs:
            # The mark on the ground is where it is going; the dot above it is
            # the thing itself, drawn higher the further it is from landing.
            down = self.camera.world_to_screen(lob.to)
            pygame.draw.circle(surface, config.SLUDGE_COLOR, down, int(lob.radius), 3)
            at = self.camera.world_to_screen(lob.pos) - pygame.Vector2(0, lob.height)
            pygame.draw.circle(surface, config.SLUDGE_COLOR, at, 10)
            pygame.draw.circle(surface, config.WHITE, at, 10, 2)
        for beam in field.beams:
            at = self.camera.world_to_screen(beam.a)
            to = self.camera.world_to_screen(beam.b)
            if beam.live:
                pygame.draw.line(surface, config.SHOCK_COLOR, at, to, int(beam.width))
                pygame.draw.line(surface, config.WHITE, at, to, 3)
            else:
                # A thread while the warning runs. Thin on purpose: a line
                # drawn at full width before it fires cannot be told from one
                # that already has.
                pygame.draw.line(surface, config.WARNING_COLOR, at, to, 2)
        for rod in field.rods:
            at = self.camera.world_to_screen(rod.pos)
            pygame.draw.circle(surface, config.SHOCK_COLOR, at, int(rod.radius))
            pygame.draw.circle(surface, config.WHITE, at, int(rod.radius), 2)
            if rod.fires:
                # The ones that throw lines are the ones worth breaking, so
                # they are the ones marked.
                pygame.draw.circle(surface, config.WHITE, at, int(rod.radius) + 6, 2)
        for pillar in field.pillars:
            # Thinning as it melts, because a column standing in the way is
            # worth going round only while it is still going to be there.
            at = self.camera.world_to_screen(pillar.pos)
            left = max(0.0, pillar.left / config.PILLAR_SECONDS)
            pygame.draw.circle(surface, config.FROST_COLOR, at, int(pillar.radius))
            pygame.draw.circle(surface, config.WHITE, at, int(pillar.radius), 3)
            pygame.draw.circle(surface, config.WHITE, at, int(pillar.radius * left), 2)

    def _draw_boss(self, surface: pygame.Surface) -> None:
        """The thing itself, in its biome's colour and far bigger than a golem.

        A second ring once it has turned, so the phase reads on the creature
        as well as on the bar -- the bar is at the top of the screen and the
        fight is not.
        """
        boss = self.boss
        if boss is None:
            return
        at = self.camera.world_to_screen(boss.pos)
        pygame.draw.circle(surface, boss.color, at, boss.radius)
        pygame.draw.circle(surface, config.WHITE, at, boss.radius, 3)
        if boss.phase == 2:
            pygame.draw.circle(surface, config.BOSS_PHASE2_COLOR, at, boss.radius + 7, 3)

    def _draw_spellbook(self, surface: pygame.Surface) -> None:
        """Every shape the player has found, down the right-hand edge.

        Only while a staff is held, because only then is a shape worth
        anything -- and a list that is always up is a list nobody reads.

        The shapes are drawn rather than spelled out in arrows. A player
        copying a picture is doing the same thing their hand will do; a player
        reading "오른쪽 아래 왼쪽" is translating first.
        """
        if not self.holding_staff:
            return
        known = [g for g in glyph_table.GLYPHS if self.grimoire.knows(g)]
        if not known:
            return
        scale = config.UI_SCALE
        step = config.SPELLBOOK_ROW * scale
        width = config.SPELLBOOK_WIDTH * scale
        top = config.BOSS_BAR_Y + config.BOSS_BAR_H + 10 * scale
        left = surface.get_width() - width - 10 * scale

        backing = pygame.Surface((width, step * len(known) + 8 * scale), pygame.SRCALPHA)
        backing.fill((0, 0, 0, config.HUD_BACKING))
        surface.blit(backing, (left, top))

        for row, glyph in enumerate(known):
            at = top + 4 * scale + row * step
            name = _font(8 * scale).render(glyph.name, True, config.WHITE)
            surface.blit(name, (left + 5 * scale, at + (step - name.get_height()) // 2))
            self._draw_shape(
                surface,
                strokes.SHAPES[glyph.key],
                pygame.Rect(
                    left + 40 * scale, at + 2 * scale, width - 45 * scale, step - 4 * scale
                ),
                glyph.biome.color if glyph.biome is not None else config.WHITE,
            )

    def _draw_shape(
        self,
        surface: pygame.Surface,
        shape: tuple[str, ...],
        box: pygame.Rect,
        colour: tuple[int, int, int],
    ) -> None:
        """One shape, drawn as the line it is.

        Scaled to fit its box rather than drawn at a fixed stroke length, so a
        five-stroke figure and a three-stroke one take the same room and the
        list stays a list.
        """
        ways = {
            strokes.UP: (0, -1),
            strokes.DOWN: (0, 1),
            strokes.LEFT: (-1, 0),
            strokes.RIGHT: (1, 0),
        }
        points = [pygame.Vector2(0, 0)]
        for way in shape:
            step = pygame.Vector2(ways[way])
            points.append(points[-1] + step)
        xs = [p.x for p in points]
        ys = [p.y for p in points]
        span_x = max(1.0, max(xs) - min(xs))
        span_y = max(1.0, max(ys) - min(ys))
        unit = min(box.width / span_x, box.height / span_y)
        origin = pygame.Vector2(
            box.centerx - (min(xs) + max(xs)) / 2 * unit,
            box.centery - (min(ys) + max(ys)) / 2 * unit,
        )
        drawn = [origin + p * unit for p in points]
        pygame.draw.lines(surface, colour, False, drawn, 2 * config.UI_SCALE)
        # A dot where the hand starts, so a shape and its mirror are not the
        # same picture.
        pygame.draw.circle(surface, config.WHITE, drawn[0], 2 * config.UI_SCALE)

    def _draw_drawing(self, surface: pygame.Surface) -> None:
        """What is being drawn right now, under the book it is being copied from."""
        if not self.drawing.drawn:
            return
        scale = config.UI_SCALE
        box = pygame.Rect(0, 0, 70 * scale, 70 * scale)
        box.bottomright = (
            surface.get_width() - 10 * scale,
            surface.get_height() - 10 * scale,
        )
        backing = pygame.Surface(box.size, pygame.SRCALPHA)
        backing.fill((0, 0, 0, config.HUD_BACKING))
        surface.blit(backing, box.topleft)
        self._draw_shape(
            surface, self.drawing.drawn, box.inflate(-12 * scale, -12 * scale), config.WARNING_COLOR
        )

    def _draw_boss_bar(self, surface: pygame.Surface) -> None:
        """One bar across the top, only while a boss is up.

        Away from the corner the player's own health lives in: hunting for
        your own health and finding the boss's is the worst possible moment
        for that mistake. It changes colour on the turn, so the second phase
        announces itself without a line of text.
        """
        boss = self.boss
        if boss is None:
            return
        margin = config.BOSS_BAR_MARGIN
        width = surface.get_width() - margin * 2
        left, top = margin, config.BOSS_BAR_Y
        height = config.BOSS_BAR_H
        bar_rect = pygame.Rect(left, top, width, height)
        _draw_frame(surface, bar_rect)
        left_over = min(1.0, max(0.0, boss.hp / boss.kind.hp))
        colour = config.BOSS_PHASE2_COLOR if boss.phase == 2 else config.BOSS_BAR_COLOR
        fill = pygame.Rect(left + 8, top + 6, int((width - 16) * left_over), height - 12)
        if fill.width > 0:
            _draw_pixel_round_right(surface, fill, colour, config.UI_SCALE, 1)
        # Inside the bar rather than under it: under it the name sat exactly
        # where the notes come up, and the two overlapped the moment a boss
        # was called -- which is when a note is most likely to be on screen.
        name = _font(11 * config.UI_SCALE).render(boss.kind.name, True, config.WHITE)
        surface.blit(name, name.get_rect(center=(surface.get_width() // 2, top + height // 2)))

    def _draw_patches(self, surface: pygame.Surface) -> None:
        """What the tricks left on the floor, under everything that stands on it.

        Translucent, because it is ground rather than a thing: solid, a burnt
        patch would read as an enemy the player has to shoot.
        """
        for patch in self.patches:
            colour = _PATCH_COLORS.get(patch.kind)
            if colour is None:
                continue
            at = self.camera.world_to_screen(patch.pos)
            size = int(patch.radius * 2)
            tint = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(
                tint, (*colour, config.PATCH_ALPHA), (size // 2, size // 2), int(patch.radius)
            )
            surface.blit(tint, (at.x - patch.radius, at.y - patch.radius))
            # A solid rim. The fill alone is a wash of colour whose edge is
            # guesswork, and where the edge is is the whole question.
            pygame.draw.circle(surface, colour, at, int(patch.radius), 3)
        for spot in self.marks:
            at = self.camera.world_to_screen(spot)
            pygame.draw.circle(surface, config.MARK_COLOR, at, 10, 3)

    def _draw_temples(self, surface: pygame.Surface) -> None:
        """The doors on the map, or the room the player is standing in.

        Never both. From outside a temple is a circle with a way in; from
        inside there is no map, only the room -- which is the whole of what
        "one room, one screen" means.
        """
        if self.inside is not None:
            self._draw_room(surface, self.inside)
            return
        for temple in self.temples:
            at = self.camera.world_to_screen(temple.pos)
            pygame.draw.circle(surface, config.TEMPLE_FLOOR, at, temple.radius)
            pygame.draw.circle(surface, config.TEMPLE_WALL, at, temple.radius, 6)
            lit = config.ALTAR_SPENT if temple.boss_killed else config.TEMPLE_DOOR
            pygame.draw.circle(surface, lit, at, 22)

    def _draw_room(self, surface: pygame.Surface, temple: Temple) -> None:
        """One room: its floor, its walls, its doors, and what is in it."""
        place = temple.interior()
        here = place.room
        box = rooms.rect(temple.pos)
        at = self.camera.world_to_screen(pygame.Vector2(box.topleft))
        floor = pygame.Rect(at.x, at.y, box.width, box.height)
        pygame.draw.rect(surface, config.TEMPLE_FLOOR, floor)
        wall = config.TEMPLE_SEALED if self.arena.sealed else config.TEMPLE_WALL
        pygame.draw.rect(surface, wall, floor, int(config.ROOM_WALL))

        for way in (dungeon.NORTH, dungeon.EAST, dungeon.WEST, dungeon.SOUTH):
            target = place.through(way)
            if target is None:
                continue
            gap = rooms.doorway(temple.pos, way)
            spot = self.camera.world_to_screen(pygame.Vector2(gap.topleft))
            # Shut while anything is standing, and shut again at the boss's
            # door until the key is found. The colour is the only warning the
            # player gets before walking into it.
            colour = (
                config.DOOR_SHUT
                if place.locked(way) is not None
                else (
                    config.DOOR_BOSS
                    if place.rooms[target].kind is dungeon.BOSS
                    else config.TEMPLE_DOOR
                )
            )
            pygame.draw.rect(surface, colour, pygame.Rect(spot.x, spot.y, gap.width, gap.height))

        middle = self.camera.world_to_screen(temple.pos)
        if here.has_chest and not here.chest_opened:
            pygame.draw.rect(surface, config.CHEST_COLOR, (middle.x - 24, middle.y - 18, 48, 36))
            pygame.draw.rect(surface, config.WHITE, (middle.x - 24, middle.y - 18, 48, 36), 3)
        if here.kind is dungeon.BOSS and not here.boss_woken:
            # Asleep: the same circle the boss will be, drawn dim and ringed,
            # so what wakes up is plainly the thing that was lying there.
            kind = BOSS_KINDS[biomes.RING_BIOMES.index(temple.biome)]
            pygame.draw.circle(surface, config.ALTAR_SPENT, middle, kind.radius)
            pygame.draw.circle(surface, kind.color, middle, kind.radius, 4)

    def detector_reading(self) -> tuple[float, str, Biome] | None:
        """Bearing, distance word and biome for the detector in hand.

        Only while it is actually held. A reading that stayed on screen after
        the thing was put away would be a map, which is the one thing a
        detector is deliberately not.
        """
        held = self.hotbar.active_stack
        if held is None:
            return None
        biome = detector.biome_of(held.kind)
        if biome is None:
            return None
        site = detector.temple_for(held.kind, self.world, self.temple_sites)
        if site is None:
            return None
        return (
            detector.bearing(self.player.pos, site),
            detector.rough_distance(self.player.pos, site),
            biome,
        )

    def _draw_detector(self, surface: pygame.Surface) -> None:
        """A needle and a word, low on the screen, away from the gauges."""
        reading = self.detector_reading()
        if reading is None:
            return
        degrees, word, biome = reading
        middle = pygame.Vector2(surface.get_width() - 70, surface.get_height() - 70)
        pygame.draw.circle(surface, (30, 30, 40), middle, 30)
        pygame.draw.circle(surface, biome.color, middle, 30, 2)
        way = pygame.Vector2(math.cos(math.radians(degrees)), math.sin(math.radians(degrees)))
        pygame.draw.line(surface, biome.color, middle, middle + way * 24, 3)
        said = _font(12).render(f"{biome.name} · {word}", True, config.WHITE)
        surface.blit(said, said.get_rect(midtop=(int(middle.x), int(middle.y) + 34)))

    def _draw_compass(self, surface: pygame.Surface) -> None:
        """Point at the core when it is off screen, and say how far.

        The grassland alone is seventy-five screens across, so home is out of
        sight almost all the time. Without this it is not merely far, it is
        lost -- there is nothing on an empty field to steer by.

        Distance is given in walking time, because that is the unit every other
        decision is made in: a day is twelve minutes and the biomes are three.
        The core is the exception and carries no label at all: it is the one
        marker that is always up, its colour is unmistakable, and the direction
        is the whole answer. The piles and the ruins keep their words, because
        a pile is on a clock and a ruin has to be told from a vault.
        """
        self._point_at(surface, self.core.pos, config.CORE_COLOR)
        for pile in self.loot:
            self._point_at(surface, pile.pos, config.LOOT_COLOR, "짐")
        # Ruins, but only ones within sight of. Twelve of them scattered over a
        # map seventy-two thousand units across would be unfindable by walking
        # and tedious to find with every one flagged from anywhere; a short
        # leash makes exploring pay without handing over the map.
        for site in self.flagged_ruins():
            colour = config.VAULT_COLOR if site.guarded else config.RUIN_COLOR
            self._point_at(surface, site.pos, colour, "유적")

    def _point_at(
        self,
        surface: pygame.Surface,
        target: pygame.Vector2,
        colour: tuple[int, int, int],
        label: str | None = None,
    ) -> None:
        at = edge_marker(
            self.camera.world_to_view(target), config.SCREEN_SIZE, config.COMPASS_MARGIN
        )
        if at is None:
            return  # it is on screen; the thing itself is the marker
        pygame.draw.circle(surface, colour, at, 7 * config.UI_SCALE)
        pygame.draw.circle(surface, (20, 20, 28), at, 7 * config.UI_SCALE, 2 * config.UI_SCALE)
        if label is None:
            return  # the dot alone; see the note in _draw_compass
        seconds = self.player.pos.distance_to(target) / config.PLAYER_SPEED
        far = f"{seconds / 60:.1f}분" if seconds >= 60 else f"{seconds:.0f}초"
        text = _font(12 * config.UI_SCALE).render(f"{label} {far}", True, colour)
        box = text.get_rect(center=(int(at.x), int(at.y) + 16 * config.UI_SCALE))
        box.clamp_ip(surface.get_rect())
        backing = pygame.Surface(
            (box.width + 6 * config.UI_SCALE, box.height + 2 * config.UI_SCALE), pygame.SRCALPHA
        )
        backing.fill((0, 0, 0, 150))
        surface.blit(backing, (box.left - 3 * config.UI_SCALE, box.top - 1 * config.UI_SCALE))
        surface.blit(text, box)

    def _draw_hud(self, surface: pygame.Surface) -> None:
        # A dim backing first. Compass markers are pinned to the screen's edge
        # and can land anywhere along it, including on top of these gauges --
        # when that happened the marker's label and the gauge under it became
        # unreadable at once.
        backing_width = _BAR_X + _BAR_W + 20 * config.UI_SCALE + 8 * config.UI_SCALE
        backing = pygame.Surface((backing_width, 68 * config.UI_SCALE), pygame.SRCALPHA)
        backing.fill((0, 0, 0, config.HUD_BACKING))
        surface.blit(backing, (0, 4 * config.UI_SCALE))
        # hp first, at the top of the stack
        hp_frac = max(0.0, self.player.hp / self.player.max_hp) if self.player.max_hp else 0.0
        _draw_health_bar(surface, 10 * config.UI_SCALE, hp_frac)
        # stamina, directly under health: the two things a body runs out of
        wind = self.player.stamina / self.player.max_stamina
        _draw_gauge(
            surface,
            28 * config.UI_SCALE,
            9,
            wind,
            self.wind_colour,
            icon=_STAMINA_ICON,
        )
        # dodge cooldown strip (full = ready)
        ready = 1 - self.player.dodge_cooldown_timer / config.DODGE_COOLDOWN
        _draw_gauge(
            surface,
            40 * config.UI_SCALE,
            5,
            ready,
            (120, 160, 220),
        )
        # the core's own health, at the foot of the stack -- only once it can
        # be hurt
        if self.core.ignited:
            _draw_bar(
                surface,
                52 * config.UI_SCALE,
                8 * config.UI_SCALE,
                self.core.hp / self.core.max_hp,
                config.CORE_COLOR,
            )
        # No pack gauge. How full the bag is matters when deciding what to pick
        # up, and that decision is made with the bag open, where the grid shows
        # it exactly; in the corner it was a bar that never moved during the
        # minute it would have had to be read.
        # The clock and the staff's strain are both off the HUD entirely --
        # gauge and written line alike. The hour is going to be a watch the
        # player carries, which is worth nothing if the corner tells them
        # anyway, and the strain gauge comes back when the staff itself is
        # built out. Seven near-identical bars in one corner meant hunting for
        # health by colour, which is the one thing that has to be instant.
        if self.note_left > 0:
            # Fades out rather than vanishing, so a glance that catches the
            # tail of it still reads as "something just happened".
            said = _font(16 * config.UI_SCALE).render(self.note, True, config.WHITE)
            said.set_alpha(int(255 * min(1.0, self.note_left / config.NOTE_FADE)))
            surface.blit(
                said, said.get_rect(midtop=(surface.get_width() // 2, 24 * config.UI_SCALE))
            )
        # hotbar (bottom-left). Hidden while the belongings screen is open,
        # which draws its own -- two hotbars on screen reads as two hotbars.
        if self.grid_open:
            return
        # Centred along the bottom. In the corner it fought the gauges for the
        # same eye and left the middle of the screen empty; the belt is the one
        # thing the hand is always on, so it belongs under the thumb.
        step = 44 * config.UI_SCALE
        slot_size = 40 * config.UI_SCALE
        group_width = (len(self.hotbar.slots) - 1) * step + slot_size
        start_x = (surface.get_width() - group_width) // 2
        for i, slot in enumerate(self.hotbar.slots):
            x, y = start_x + i * step, surface.get_height() - 50 * config.UI_SCALE
            is_selected = i == self.hotbar.selected
            _draw_frame(surface, pygame.Rect(x, y, slot_size, slot_size), selected=is_selected)
            number_color = (143, 134, 106) if is_selected else (105, 111, 106)
            _draw_hotbar_digit(
                surface,
                i + 1,
                x + 17 * config.UI_SCALE,
                # Just above the slot, clear of its edge.
                y - 12 * config.UI_SCALE,
                number_color,
            )
            if slot is not None:
                self._draw_contents(
                    surface,
                    pygame.Rect(
                        x + 8 * config.UI_SCALE,
                        y + 8 * config.UI_SCALE,
                        24 * config.UI_SCALE,
                        24 * config.UI_SCALE,
                    ),
                    slot,
                )
