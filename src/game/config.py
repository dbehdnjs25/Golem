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

# --- Day / night --------------------------------------------------------------
# Six and six. Daylight is exactly two walks to the grassland's rim, so a trip
# out and back fills the day; the night is just as long, which makes surviving it
# a phase of its own rather than a pause between days.
DAY_LENGTH: Final[float] = 360.0  # seconds of daylight
NIGHT_LENGTH: Final[float] = 360.0  # seconds of night
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
# Two three-minute walks at PLAYER_SPEED: one from the core to the grassland's
# rim, another from there to the map's edge. That makes the grassland a quarter
# of the total area -- the ring is thin in radius but wide in ground, since a
# far-out band holds far more of it than a near one.
GRASSLAND_RADIUS: Final[float] = 36_000.0  # 180s * 200px/s
RING_WIDTH: Final[float] = 36_000.0  # another 180s to cross the biomes
MAP_RADIUS: Final[float] = GRASSLAND_RADIUS + RING_WIDTH
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
# Slots, not weight. One slot holds up to a kind's stack_max of that kind. The
# backpack is the ONLY place items go: there is no base inventory, so a player
# without one has the hotbar and nothing else.
STACK_MAX_DEFAULT: Final[int] = 64
BACKPACK_SLOTS: Final[int] = 20  # the basic pack; better ones hold more
CORE_STORE_SLOTS: Final[int] = 40  # the store at the core, never carried

# --- Camera -----------------------------------------------------------------
CAMERA_PAN_SPEED: Final[float] = 400.0  # px/s free-pan speed
CAMERA_EDGE_MARGIN: Final[int] = 40  # px band at screen edge that pans

# --- Spawner ----------------------------------------------------------------
SPAWN_INTERVAL: Final[float] = 2.0  # seconds between spawn attempts
SPAWN_MAX: Final[int] = 30  # max simultaneous fragments
SPAWN_RADIUS: Final[float] = 2_000.0  # spawns follow the player, not the whole map
# Loose things on the ground come up by walking over them. Swinging at a twig
# is busywork; swinging at a tree is not.
PICKUP_RADIUS: Final[float] = 70.0
# Trees are a flat share of what spawns, at every distance. Ore quality is what
# distance decides; wood is wood wherever it grows.
TREE_SHARE: Final[float] = 0.35
# Litter -- twigs, pebbles, grass -- keeps turning up, so a run that loses its
# tools can always start over from the ground.
LITTER_SHARE: Final[float] = 0.15

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
# growth makes an early level invisible and a late one enormous. It starts at a
# third of the full radius and finishes growing at WARD_MAX_LEVEL, well short of
# the level cap -- the last stretch of the core ladder buys something other than
# ground.
WARD_RADIUS_MAX: Final[float] = 12_000.0  # a ninth of the grassland's area
WARD_RADIUS_BASE: Final[float] = WARD_RADIUS_MAX / 3.0
WARD_MAX_LEVEL: Final[int] = 35  # the ward is full here and never grows again
WARD_GROWTH: Final[float] = (WARD_RADIUS_MAX / WARD_RADIUS_BASE) ** (1 / (WARD_MAX_LEVEL - 1))

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
WARD_COLOR: Final[tuple[int, int, int]] = (120, 220, 255)
PEDESTAL_COLOR: Final[tuple[int, int, int]] = (150, 150, 165)
NIGHT_DARKNESS: Final[int] = 150  # alpha of the night overlay, 0-255
LOOT_COLOR: Final[tuple[int, int, int]] = (245, 200, 90)
BLOCKED_COLOR: Final[tuple[int, int, int]] = (230, 90, 90)  # ringed when out of reach
# How far in from the edge an off-screen pointer sits.
COMPASS_MARGIN: Final[float] = 34.0
LOOT_RADIUS: Final[float] = 16.0
LOOT_PICKUP_RADIUS: Final[float] = 60.0  # walk onto it to take it back
# A pile waits five minutes. Short of a full day, so the deadline bites inside
# the day it happened; long enough to cross most of the grassland and back.
LOOT_LIFETIME: Final[float] = 300.0

# --- Belongings screen --------------------------------------------------------
GRID_COLS: Final[int] = 5  # the hotbar's width, so the two grids line up
GRID_CELL: Final[int] = 44
GRID_GAP: Final[int] = 4
GRID_PANEL: Final[tuple[int, int, int]] = (26, 26, 36)

# --- Stations -----------------------------------------------------------------
STATION_RADIUS: Final[float] = 28.0  # footprint; two cannot overlap
STATION_REACH: Final[float] = 90.0  # stand within this and its recipes open
# The blast furnace takes up room, so it waits on the ward being wide enough --
# which is what puts steel behind levelling the core rather than behind grinding.
# Sits inside the ladder (4,000 -> 12,000) rather than at either end: reachable
# around level 20, so one boss at least has to fall first.
BLAST_FURNACE_MIN_WARD: Final[float] = 7_000.0
STATION_OUTPUT_SLOTS: Final[int] = 4  # what a station can hold before it stalls

# --- Crafting menu ------------------------------------------------------------
CRAFT_ROW_HEIGHT: Final[int] = 26
CRAFT_ROWS_VISIBLE: Final[int] = 14

# --- Combat: player -----------------------------------------------------------
PLAYER_MAX_HP: Final[float] = 100.0

# --- Stamina --------------------------------------------------------------
# Spent on dodging, running and digging; bought back with meat. There is no
# hunger system -- the spec rules one out -- so this is purely a limit on how
# much a body can do at once, never a clock counting down.
PLAYER_MAX_STAMINA: Final[float] = 100.0
STAMINA_REGEN: Final[float] = 14.0  # per second, once the hold has run out
STAMINA_DELAY: Final[float] = 1.1  # seconds of no recovery after spending
# Running. Below the dodge's multiplier on purpose -- a sprint that outran a
# dash would make the dodge a worse sprint and nobody would dodge.
PLAYER_SPRINT_MULT: Final[float] = 1.7
SPRINT_DRAIN: Final[float] = 5.0  # per second, while actually moving
DODGE_COST: Final[float] = 15.0  # six and a half dodges from full
MINING_DRAIN: Final[float] = 5.0  # per second of digging
# Digging on empty. Slower, never stopped -- see systems/mining.
WINDED_MINING_RATE: Final[float] = 0.45

# --- Food -----------------------------------------------------------------
# Meat buys back wind. Raw gives the same breath as cooked and takes it out of
# your health, which is what makes the walk to a hearth worth making -- and
# hearths only stand inside the ward.
MEAT_STAMINA: Final[float] = 55.0
RAW_MEAT_HP_COST: Final[float] = 16.0
# The scarce answer to an empty health bar, where the ward's slow healing is
# the free one. Brewed from a frost crystal: the spec puts the bog fourth
# because its drain is unfair "before cooking and potions exist", so a
# potion gated behind bog moss would be a circle.
POTION_HEAL: Final[float] = 45.0
# --- Mires ----------------------------------------------------------------
# Patches of standing mire, lying in the bog the way lava lies in the burnt
# forest. The biome around them is ordinary walking; these are what the spec's
# drain actually means.
#
# Breath, never blood, and only from someone MOVING. A still player pays
# nothing and starts recovering, which makes a mire somewhere to stop rather
# than somewhere to flee: the cost is the wading, not the being there.
MIRES_MIN: Final[int] = 8
MIRES_MAX: Final[int] = 14
MIRE_RADIUS_MIN: Final[float] = 320.0
MIRE_RADIUS_MAX: Final[float] = 780.0
MIRE_DRAIN: Final[float] = 10.0  # per second of wading
# Against the bog's own dark green, so the edge reads before a player is in it.
MIRE_COLOR: Final[tuple[int, int, int]] = (40, 52, 40)
MIRE_RIM_COLOR: Final[tuple[int, int, int]] = (118, 142, 88)
WIND_COLOR: Final[tuple[int, int, int]] = (120, 205, 150)
WIND_BOG_COLOR: Final[tuple[int, int, int]] = (138, 160, 92)
# Empty reads differently again: a bar merely sitting at zero does not
# say WHY the dodge key has stopped working.
WIND_EMPTY_COLOR: Final[tuple[int, int, int]] = (196, 120, 92)

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
# Health scales with distance in full; speed only partly. A golem twice as
# tough that also moves twice as fast is not harder, it is unfightable.
GOLEM_SPEED_SCALING: Final[float] = 0.25
# What a golem at the map's edge is worth against one beside the ward. The
# ore out there is better for exactly this reason: distance is the danger.
GOLEM_SCALE_AT_EDGE: Final[float] = 4.0

# --- Wild animals ---------------------------------------------------------
# They press around the ward at night and are the only thing abroad before the
# core is lit -- with nowhere to heal, a night out is what makes lighting it
# worth doing.
BEAST_SPAWN_INTERVAL: Final[float] = 4.0
BEAST_SPAWN_MAX: Final[int] = 12
BEAST_RING: Final[float] = 900.0  # how far from the player they turn up
# How close you have to get before a rabbit bolts. Fleeing at any distance
# would pin every rabbit against the map's rim, uncatchable.
BEAST_FLEE_RANGE: Final[float] = 320.0

# --- Raids ----------------------------------------------------------------
# Days between raids, indexed by how many bosses are down. The calendar is
# tied to progress rather than to a difficulty dial: every boss takes a day off
# the gap, so the nights crowd in as the player gets stronger and it reads as
# "you are paying for this" rather than as the game turning a knob.
RAID_INTERVALS: Final[tuple[int, ...]] = (7, 6, 5, 4, 3, 2)

# The core's own health. It grows per level, which is what the last stretch of
# the ladder buys: the ward finishes at WARD_MAX_LEVEL, so levels past that
# would otherwise purchase nothing at all.
CORE_BASE_HP: Final[float] = 400.0
CORE_HP_PER_LEVEL: Final[float] = 120.0
CORE_REPAIR_PER_ITEM: Final[float] = 25.0  # hp mended per stone spent
# A raid night pours them in faster and lets more stand at once. A quicker
# trickle into the same small cap would hardly read as a raid at all.
RAID_SPAWN_INTERVAL: Final[float] = 2.0
RAID_SPAWN_MAX: Final[int] = 20
# Clawing a person and clawing a stone monolith are not the same work, so the
# core takes its hits far more slowly than the player does. Without this every
# raider piles onto one point and even a level-50 core falls inside two
# minutes of a six-minute night, which leaves no raid to fight.
CORE_CONTACT_DPS: Final[float] = 5.0
# The ward's rim on a night it is not holding anything out.
WARD_BROKEN_COLOR: Final[tuple[int, int, int]] = (214, 92, 84)
# The screen-edge pulse that says a raid is on. The ward is thousands of units
# across and the view is hundreds, so the broken rim is off screen; this is the
# one sign that does not depend on where the camera is pointed.
RAID_EDGE_WIDTH: Final[int] = 28
RAID_PULSE_SPEED: Final[float] = 2.2  # radians/s
RAID_PULSE_MIN: Final[int] = 40
RAID_PULSE_MAX: Final[int] = 120

# --- Glyphs ---------------------------------------------------------------
# What a carved glyph is worth, by tier. Power is damage added to a weapon or
# thrown by a staff; strain is what a staff pays for it, which is why the best
# cut is not simply the right answer -- it empties the staff fastest.
GLYPH_POWER_BASIC: Final[float] = 6.0
GLYPH_POWER_GREATER: Final[float] = 14.0
GLYPH_POWER_SUPREME: Final[float] = 30.0
GLYPH_STRAIN_PER_POWER: Final[float] = 1.6
# How often a node in a ring biome is that biome's own material. The only
# source of any of it, and scarce on purpose: it gates the second ladder,
# so it should be worth the trip rather than picked up on the way past.
BIOME_MATERIAL_SHARE: Final[float] = 0.12

# --- Lava -----------------------------------------------------------------
# Pools standing in the burnt forest. Terrain, not a creature: they never move
# and the ward has no opinion about them, which is why the spec put this biome
# at the easy end -- a danger you can see and decide about is the kindest kind.
LAVA_POOLS_MIN: Final[int] = 6
LAVA_POOLS_MAX: Final[int] = 10
LAVA_RADIUS_MIN: Final[float] = 260.0
LAVA_RADIUS_MAX: Final[float] = 620.0
# Hot enough that wading is a real cost, slow enough that a dash across the
# narrow end is a choice. Instant death would make it a wall, and a wall is not
# a decision.
LAVA_DPS: Final[float] = 26.0
OBSIDIAN_BELT: Final[float] = 420.0  # how far the studded stone reaches out
OBSIDIAN_PER_POOL_MIN: Final[int] = 3  # never a pool worth no walk
OBSIDIAN_PER_POOL_MAX: Final[int] = 6
# The sheen on the glass showing through the rock. Volcanic glass is black,
# and black on black would be the same as no fleck at all.
OBSIDIAN_GLINT: Final[tuple[int, int, int]] = (176, 150, 205)
LAVA_COLOR: Final[tuple[int, int, int]] = (214, 92, 38)
LAVA_RIM_COLOR: Final[tuple[int, int, int]] = (255, 186, 92)
# How strongly the screen washes while standing in it. A health bar falling
# with no cause on screen is the kind of thing a player blames on the game.
LAVA_WASH: Final[int] = 70
# Cuts per chisel. Learning is free and forever, so this is the only price
# carving has -- and it is what makes "is this the right glyph for this
# weapon" a question every time instead of a formality.
CHISEL_USES: Final[int] = 3

# --- Structures -----------------------------------------------------------
# The ruins that hold the drawings. Placement walks the glyph list rather than
# a count, so every basic glyph is guaranteed a home -- a count-first world
# would eventually roll with no frost glyph in it and nothing would show it.
STRUCTURE_RADIUS: Final[float] = 26.0
STRUCTURE_REACH: Final[float] = 90.0  # how close to stand to open one
STRUCTURE_MIN_FROM_CORE: Final[float] = 2200.0  # never right on the doorstep
STRUCTURE_SPACING: Final[float] = 1500.0  # never stacked on each other
STRUCTURES_PER_BIOME: Final[int] = 2  # two chances, so one bad sector is not fatal
RUIN_COLOR: Final[tuple[int, int, int]] = (178, 160, 196)
VAULT_COLOR: Final[tuple[int, int, int]] = (206, 170, 110)
RUIN_SPENT_COLOR: Final[tuple[int, int, int]] = (96, 92, 104)
# How long a line stays on screen. Learning a glyph is otherwise invisible --
# the ruin dims and nothing else happens, which reads as a bug, not a reward.
NOTE_SECONDS: Final[float] = 3.5
NOTE_FADE: Final[float] = 1.2  # seconds of fade at the end
# Room on the weapon. Flat, because weapon types are an open question in the
# spec -- the staff is where "more slots by upgrading" actually shows.
WEAPON_SLOTS: Final[int] = 2

# --- The staff ------------------------------------------------------------
# A staff is a budget rather than a number. Strain climbs with power, so the
# supreme cut empties it fastest and the basic cut is the only one that can be
# thrown all night. Cooling is set so the cheapest glyph at the staff's own
# fire rate breaks even -- something has to be sustainable or the staff is a
# novelty.
STAFF_FIRE_RATE: Final[float] = 2.0  # throws per second
STAFF_STRAIN_MAX: Final[float] = 100.0
STAFF_COOLING: Final[float] = 22.0  # strain shed per second
STAFF_LOCKOUT: Final[float] = 4.0  # seconds out of action after an overload

# --- Detectors ------------------------------------------------------------
# A detector gives a bearing and a WORD, never a number. A number would make
# the random placement pointless: the player would walk the bearing watching a
# counter, which is a puzzle with one move in it.
DISTANCE_WORDS: Final[tuple[str, ...]] = ("바로 앞", "가까움", "멂", "아주 멂")
# Upper bound of each word, in world units; the last catches everything else.
DISTANCE_BANDS: Final[tuple[float, ...]] = (900.0, 9000.0, 28000.0)

# How close to a ruin before the compass flags it. Twelve scattered over a map
# this size are unfindable by walking and tedious with every one flagged from
# anywhere; a short leash makes exploring pay without handing over the map.
RUIN_SIGHTING: Final[float] = 3000.0
STRAIN_COLOR: Final[tuple[int, int, int]] = (150, 120, 215)
STRAIN_LOCKED_COLOR: Final[tuple[int, int, int]] = (214, 92, 84)
# How far out they walk in from, as a share of the ward's reach beyond its rim.
GOLEM_APPROACH: Final[float] = 0.45

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
