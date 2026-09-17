"""Global configuration constants.

Kept free of any ``pygame`` import so it can be imported in any test without a
display. Colours are plain RGB tuples for the same reason.
"""

from __future__ import annotations

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

# --- Colours (RGB) ----------------------------------------------------------
BLACK: Final[tuple[int, int, int]] = (0, 0, 0)
WHITE: Final[tuple[int, int, int]] = (255, 255, 255)
BACKGROUND: Final[tuple[int, int, int]] = (30, 30, 46)

# --- World ------------------------------------------------------------------
WORLD_WIDTH: Final[int] = 2400
WORLD_HEIGHT: Final[int] = 1600
WORLD_SIZE: Final[tuple[int, int]] = (WORLD_WIDTH, WORLD_HEIGHT)
TILE_SIZE: Final[int] = 32  # visual floor rendering only, not a data grid

# --- Player -----------------------------------------------------------------
PLAYER_SPEED: Final[float] = 220.0  # px/s
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

# --- Core -------------------------------------------------------------------
CORE_RADIUS: Final[float] = 40.0
CORE_SYNC_RADIUS: Final[float] = 120.0  # auto-transfer when player within this

# --- Hotbar -----------------------------------------------------------------
# Fixed at five. Dying keeps the hotbar and drops half of everything else, so
# "is this worth a hotbar slot?" is the protection decision every trip.
HOTBAR_SLOTS: Final[int] = 5

# --- Additional colours (RGB) -----------------------------------------------
FLOOR_A: Final[tuple[int, int, int]] = (26, 26, 40)
FLOOR_B: Final[tuple[int, int, int]] = (32, 32, 48)
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
