"""Global configuration constants.

Kept free of any ``pygame`` import so it can be imported in any test without a
display. Colours are plain RGB tuples for the same reason.
"""

from __future__ import annotations

import math
from typing import Final

# --- Window -----------------------------------------------------------------
TITLE: Final[str] = "Golem"
SCREEN_WIDTH: Final[int] = 960
SCREEN_HEIGHT: Final[int] = 540
SCREEN_SIZE: Final[tuple[int, int]] = (SCREEN_WIDTH, SCREEN_HEIGHT)

# --- Timing -----------------------------------------------------------------
# The simulation advances in fixed steps for deterministic, testable logic.
FPS: Final[int] = 60
FIXED_DT: Final[float] = 1.0 / FPS  # seconds per logic step
MAX_FRAME_TIME: Final[float] = 0.25  # clamp to avoid the "spiral of death"

# --- Day / night --------------------------------------------------------------
# A day is long enough to reach the biomes and back only just; the night is long
# enough to matter but not to dominate, since the raid cadence shortens to every
# two days late on and the player would otherwise only ever see darkness.
DAY_LENGTH: Final[float] = 300.0  # seconds of daylight
NIGHT_LENGTH: Final[float] = 180.0  # seconds of night
DAY_TOTAL: Final[float] = DAY_LENGTH + NIGHT_LENGTH

# --- Colours (RGB) ----------------------------------------------------------
BLACK: Final[tuple[int, int, int]] = (0, 0, 0)
WHITE: Final[tuple[int, int, int]] = (255, 255, 255)
BACKGROUND: Final[tuple[int, int, int]] = (30, 30, 46)
VOID_COLOR: Final[tuple[int, int, int]] = (18, 18, 26)  # outside the map circle

# --- World ------------------------------------------------------------------
# The playable map is a CIRCLE inscribed in a square world box. The box is what
# the camera clamps against; the circle is what the player can stand on, so the
# box corners are void. A central grassland fills about a third of the circle
# and the remaining ring is split into BIOME_COUNT equal sectors.
# The grassland's rim is a three-minute walk from the core at PLAYER_SPEED.
# That single number sets the map's scale; the outer radius then follows from
# keeping the grassland at a third of the total area.
GRASSLAND_RADIUS: Final[float] = 36_000.0  # 180s * 200px/s
MAP_RADIUS: Final[float] = 62_400.0  # (36000/62400)^2 = 1/3 of the area
BIOME_COUNT: Final[int] = 5

WORLD_WIDTH: Final[int] = int(2 * MAP_RADIUS)
WORLD_HEIGHT: Final[int] = int(2 * MAP_RADIUS)
WORLD_SIZE: Final[tuple[int, int]] = (WORLD_WIDTH, WORLD_HEIGHT)
TILE_SIZE: Final[int] = 32  # the size biome tile art is authored for; not a data grid

# Where a boss temple may stand inside its sector, as a FRACTION of the ring's
# width -- an absolute radius silently lands in the wrong place the moment the
# map is rescaled. The angular inset keeps it off the seams, where it would read
# as belonging to the neighbouring biome.
TEMPLE_BAND_INNER_FRAC: Final[float] = 0.20
TEMPLE_BAND_OUTER_FRAC: Final[float] = 0.80
TEMPLE_ANGLE_INSET: Final[float] = 12.0  # degrees trimmed from each sector edge

# --- Player -----------------------------------------------------------------
PLAYER_SPEED: Final[float] = 200.0  # px/s
PLAYER_RADIUS: Final[float] = 14.0

# --- Mining / fragments -----------------------------------------------------
FRAGMENT_HP: Final[float] = 60.0
FRAGMENT_RADIUS: Final[float] = 10.0
MINING_DPS: Final[float] = 40.0  # hp per second while channelling
MINING_RANGE: Final[float] = 96.0  # player-to-fragment distance

# --- Storage ----------------------------------------------------------------
# Slots, not weight. One slot holds up to a kind's stack_max of that kind, so
# the limit is how many DIFFERENT things you can carry, not how heavy they are.
STACK_MAX_DEFAULT: Final[int] = 64
INVENTORY_SLOTS: Final[int] = 10  # carried by default
BACKPACK_SLOTS: Final[int] = 10  # added by wearing a backpack -> doubles the carry
CORE_STORE_SLOTS: Final[int] = 40  # the store at the core, never carried

# --- Camera -----------------------------------------------------------------
CAMERA_PAN_SPEED: Final[float] = 400.0  # px/s free-pan speed
CAMERA_EDGE_MARGIN: Final[int] = 40  # px band at screen edge that pans

# --- Spawner ----------------------------------------------------------------
SPAWN_INTERVAL: Final[float] = 2.0  # seconds between spawn attempts
SPAWN_MAX: Final[int] = 30  # max simultaneous fragments
SPAWN_RADIUS: Final[float] = 2_000.0  # spawns follow the player, not the whole map

# --- Core -------------------------------------------------------------------
CORE_RADIUS: Final[float] = 40.0
CORE_SYNC_RADIUS: Final[float] = 120.0  # auto-transfer when player within this
CORE_SHARDS_TO_IGNITE: Final[int] = 5

# Level 0 is an unlit core with no ward. Each cap is opened by one boss's drop,
# so the five temples are what actually gate the ladder; clearing the fifth
# unlocks the final upgrade rather than another cap.
CORE_MAX_LEVEL: Final[int] = 50
CORE_LEVEL_CAPS: Final[tuple[int, ...]] = (10, 20, 30, 40, 50)

# The ward grows by a constant RATIO per level, not a constant amount: absolute
# growth makes an early level invisible and a late one enormous. At full level it
# covers a tenth of the grassland's area, hence the sqrt(10).
WARD_RADIUS_BASE: Final[float] = 1_000.0
WARD_RADIUS_MAX: Final[float] = GRASSLAND_RADIUS / math.sqrt(10.0)
WARD_GROWTH: Final[float] = (WARD_RADIUS_MAX / WARD_RADIUS_BASE) ** (1 / (CORE_MAX_LEVEL - 1))

# --- Survival ----------------------------------------------------------------
# Regen ramps up the longer the player stays inside the ward and resets the
# moment they leave, so tagging the edge between fights banks nothing. Free but
# slow to start, which leaves potions their job: healing RIGHT NOW.
WARD_REGEN_BASE: Final[float] = 1.0  # hp/s on arrival
WARD_REGEN_RAMP: Final[float] = 0.5  # hp/s added per second spent inside
WARD_REGEN_MAX: Final[float] = 8.0  # hp/s ceiling, reached after 14s

# --- Hotbar -----------------------------------------------------------------
# Fixed at five. Dying keeps the hotbar and drops half of everything else, so
# "is this worth a hotbar slot?" is the protection decision every trip.
HOTBAR_SLOTS: Final[int] = 5

# --- Additional colours (RGB) -----------------------------------------------
FRAGMENT_COLOR: Final[tuple[int, int, int]] = (90, 200, 255)
CORE_COLOR: Final[tuple[int, int, int]] = (120, 255, 180)
PLAYER_COLOR: Final[tuple[int, int, int]] = (240, 240, 255)

# --- Combat: player -----------------------------------------------------------
PLAYER_MAX_HP: Final[float] = 100.0

# --- Combat: dodge ------------------------------------------------------------
DODGE_SPEED_MULT: Final[float] = 2.6  # speed multiplier during a dash
DODGE_DURATION: Final[float] = 0.18  # seconds of dash movement
DODGE_IFRAMES: Final[float] = 0.30  # seconds of invulnerability
DODGE_COOLDOWN: Final[float] = 0.80  # seconds before dodging again
RESPAWN_DELAY: Final[float] = 2.0  # seconds dead before respawn
RESPAWN_IFRAMES: Final[float] = 1.5  # invulnerability granted on respawn

# --- Combat: golem enemy ------------------------------------------------------
GOLEM_HP: Final[float] = 30.0
GOLEM_SPEED: Final[float] = 140.0  # px/s toward the player
GOLEM_RADIUS: Final[float] = 11.0
GOLEM_CONTACT_DPS: Final[float] = 20.0  # hp/s while touching the player
GOLEM_SPAWN_INTERVAL: Final[float] = 3.0
GOLEM_SPAWN_MAX: Final[int] = 15

# --- Combat: weapon / projectile ----------------------------------------------
WEAPON_DAMAGE: Final[float] = 12.0
WEAPON_FIRE_RATE: Final[float] = 4.0  # shots per second while held
PROJECTILE_SPEED: Final[float] = 520.0  # px/s
PROJECTILE_TTL: Final[float] = 1.2  # seconds before a shot despawns
PROJECTILE_RADIUS: Final[float] = 4.0

# --- Combat: colours (RGB) ----------------------------------------------------
GOLEM_COLOR: Final[tuple[int, int, int]] = (230, 80, 90)
PROJECTILE_COLOR: Final[tuple[int, int, int]] = (255, 240, 150)
HP_COLOR: Final[tuple[int, int, int]] = (220, 70, 80)
