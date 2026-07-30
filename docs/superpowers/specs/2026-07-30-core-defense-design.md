# Core Defense — Design Spec

_Date: 2026-07-30 · Project: Defrag (pygame-ce)_

## Goal

Give the game a losing condition and the tension that comes with it. The Core
gains HP, enemies split into kinds that either march on the Core or hunt the
player, and the player must decide, moment to moment, whether to mine or to
defend.

Today the game has no failure state: dying costs half a backpack and time, so
enough patience always wins. This spec makes *leaving the Core unattended* the
real cost, and makes the same resource pay for both survival (repair) and — in
a later spec — victory (summoning the boss).

Everything follows existing patterns: logic lives in pure `update(dt, ...)`
functions (headless-testable), enemy stats are frozen dataclasses the way tools
already are, and rendering stays in the scene.

## Position in the roadmap

The larger win/lose structure was decomposed into four specs. This is **A**.

| Spec | Content | Depends on |
|---|---|---|
| **A. Core defense** (this) | Core HP, enemy kinds, aggro, repair, defeat signal | — |
| B. Boss | Resource threshold → summon → boss fight → victory signal | A |
| C. Scene flow | Title / pause / victory / game-over screens | A, B |
| D. Save | Multiple save slots, what and when to persist | C |

## Scope (in / out)

**In:** Core HP and destruction, the `EnemyKind` catalogue (2×3 axes designed,
4 kinds implemented), target policy with aggro hysteresis, melee and suicide
attacks with per-kind attack speed, resource-funded repair, screen-edge pulse
on Core damage, Core HP bar, world simulation continuing while the player is
dead, defeat **signal**, unit tests for all new logic.

**Out (deferred, not rejected):** the two ranged kinds (they pull in enemy
projectiles — own spec), the boss, the game-over **screen** (spec C), save.

Defeat stops at a signal on purpose: `PlayScene` sets a `defeated` flag and
halts updates. Spec C reads that flag and pushes a screen. Cutting here is what
keeps A finishable now and leaves C a stable contract to build against.

## Enemy taxonomy

Two orthogonal axes. An enemy kind is a point in that grid, not a bespoke class.

- **Target policy** — who it walks toward: `TARGET_CORE`, `TARGET_HUNTER`
- **Attack** — what it does on arrival: `ATTACK_MELEE`, `ATTACK_SUICIDE`,
  `ATTACK_RANGED` (designed, not implemented here)

### `entities/enemy_kinds.py` (new) — `EnemyKind` (frozen dataclass)

```
name: str
target: str          # TARGET_CORE | TARGET_HUNTER
attack: str          # ATTACK_MELEE | ATTACK_SUICIDE | ATTACK_RANGED
hp: float
speed: float
radius: float
damage: float        # per hit (melee) or per blast (suicide)
attack_interval: float
spawn_weight: int
color: tuple[int, int, int]
```

`attack_interval` reads consistently across all three attacks: it is the time
the kind needs to deliver one attack. For melee it is the swing period, for
suicide the fuse, for ranged (later) the reload.

### The four implemented kinds

| Name | Target | Attack | HP | Speed | Radius | Damage | Interval | Weight |
|---|---|---|---|---|---|---|---|---|
| **Virus** | Hunter | Melee | 30 | 140 | 11 | 12 | 0.6 s | 50 % |
| **Ransomware** | Hunter | Suicide | 20 | 190 | 10 | 25 | 0.7 s | 38 % |
| **Worm** | Core | Melee | 45 | 110 | 12 | 20 | 1.2 s | 8 % |
| **Logic Bomb** | Core | Suicide | 25 | 160 | 12 | 40 | 1.2 s | 4 % |

Virus deals 12 ÷ 0.6 s = 20 dps, exactly today's `VIRUS_CONTACT_DPS`, so the
existing feel is preserved.

The roles are deliberately non-overlapping. **Worm** is slow and tough: ignore
it and it piles up on the Core — the price of neglect. **Logic Bomb** is fast
and fragile: easy to intercept, expensive to miss — the price of inattention.
**Ransomware** threatens the player specifically, so mining trips stay tense.

**Why the dedicated Core-seekers are rare (12 %):** hunters also walk to the
Core whenever the player is out of range. So Core pressure is not 12 % — it is
12 % baseline plus *everything else* whenever the player is away. The dedicated
kinds are the constant drip; the real threat scales with time spent away from
home. That is the intended tension, and it is why this share must stay low.

**Why the fuses are long:** a fuse makes suicide enemies interceptable. Logic
Bomb (25 hp) dies in ~0.52 s to the 48 dps weapon, comfortably inside its 1.2 s
fuse, so a Core hit is preventable by reacting. Ransomware's 0.7 s fuse leaves
room to time the 0.3 s dodge i-frames. Both numbers exist to create a reaction
window, not to tune damage.

## Damage rules

Three rules, chosen so that each reads correctly to the player:

1. **Melee damages the current target only.** A Core-bound Worm walks through
   the player without hurting them. This makes "that one is ignoring me"
   legible, and stops incidental brushes from being punishing.
2. **A blast damages everything in its radius.** When a suicide enemy
   detonates, both the player and the Core take damage if they are inside.
   An explosion that spares a bystander standing in it reads as a bug.
3. **A projectile hits the first valid target it touches** (ranged, later spec).
   A shot aimed at the Core does not pass through the player.

Rule 2 has two intended consequences. Repairing means standing where Logic
Bombs detonate, so repair is not a safe action. And a Ransomware chasing the
player into the Core's vicinity splashes the Core, so camping on top of the
Core is not strictly optimal — where to stand becomes a live decision.

Blast radius is `radius * SUICIDE_BLAST_MULT` (2.5), slightly wider than the
contact check. No extra `EnemyKind` field: a field only one attack type uses is
the first step toward a table that no longer describes its rows.

## Target policy

`TARGET_CORE` is stateless — always the Core.

`TARGET_HUNTER` carries two per-instance fields:

```
aggro_timer: float      # forced player-aggro remaining
proximity_aggro: bool
```

Per step, in order:

1. Compute `d` = distance to the player.
2. `d <= AGGRO_DETECT_RADIUS` (300) → `proximity_aggro = True`;
   `d > AGGRO_RELEASE_RADIUS` (450) → `False`; between the two, **unchanged**.
3. `aggro_timer = max(0, aggro_timer - dt)`.
4. Target = player if `aggro_timer > 0 or proximity_aggro`, else the Core.

Taking damage sets `aggro_timer = AGGRO_LOCK_DURATION` (4 s), refreshed on every
hit. This lives in `Enemy.damage()`; Core-seekers run the same code and their
target policy ignores the field, which is harmless.

The two radii differ on purpose. With a single radius, a player moving along the
boundary makes the enemy flip target every frame and visibly jitter. Entering at
300 and only releasing past 450 removes that.

The rules compose without ambiguity: if the lock expires while the player sits
at 400 px, `proximity_aggro` was never set (400 > 300) and never cleared
(400 < 450), so it is still `False` and the enemy returns to the Core.

## Attack execution

Every enemy carries `attack_timer: float`, starting at 0 and decremented every
step **regardless of contact**. That single choice removes an abuse
(detach/reattach to reset the swing) and, because it starts at 0, makes the
first hit land the instant contact begins.

**Melee** — in contact with the current target and `attack_timer <= 0`: apply
`damage`, set `attack_timer = attack_interval`.

**Suicide** — on first contact with the current target, light the fuse
(`fuse_timer = attack_interval`); further contact does not restart it. When the
fuse expires, damage everything within the blast radius and remove the enemy.
Ignition cannot be cancelled, so all three counters stay live: run out of the
blast, soak it with dodge i-frames, or kill it before it goes off. A blast with
nothing in range is simply wasted.

A lit fuse is independent of targeting. If a hunter re-aggros mid-fuse and turns
around, the fuse keeps running and detonates on schedule; because a blast hits
everything in radius (rule 2), the target it was lit against no longer matters.

## Core

### `entities/core.py` (modified)

Add `hp`, `max_hp`, `damage(amount)`, `is_destroyed` (`hp <= 0`). The entity
stays pure data plus predicates, matching its current shape.

`CORE_MAX_HP = 2000`. It is high because an unattended Core can face the entire
spawn cap at once — smaller values evaporate in seconds when the player is away.

### Defeat signal

`PlayScene` checks `core.is_destroyed` each step and, on first true, sets
`self.defeated = True` and stops updating the world. That flag is the whole of
A's contract with spec C.

## Repair

Held `R` inside the Core's sync range (`core.is_in_sync_range(player.pos)`),
matching the hold-to-act pattern already used by mining and firing.

Healing is continuous at `REPAIR_HP_PER_SEC` (100). Each time accumulated
healing crosses `REPAIR_HP_PER_ITEM` (25), one item is removed from
`/Documents` — the same shape as mining, which damages a fragment continuously
and banks one item at depletion. Healing stops immediately when `/Documents` is
empty or the Core is full.

Healing a Core back from near-zero costs 80 items against a 500 MB (100 item)
store, so one bad breach eats most of the boss-summon fund. That weight is the
point, and it is also **the least confident number in this spec** — first thing
to retune after playing.

**Repair and sync coexist.** Sync is automatic (range-based, no input) and
repair is a held key; neither blocks the other, and `Folder.add`/`remove` are
both bounded, so draining and filling `/Documents` in the same step is safe.
Within a step the order is fixed: **sync, then repair**, so items that arrive
this frame are immediately spendable and the order is deterministic.

## The world runs while the player is dead

`PlayScene.update` currently early-returns during the respawn wait, freezing
enemies, spawners and projectiles. That must change: only the player goes
inactive, the world keeps simulating.

`Player` gains `is_dead`. Hunters treat a dead player as absent — proximity and
lock aggro are both skipped, so every hunter converges on the Core.

This turns death's real cost from "half a backpack" into "the Core is
undefended for `RESPAWN_DELAY` seconds", which is the cheapest meaningful
tension this spec adds.

## Presentation

### Screen-edge pulse

`PlayScene` holds `_core_hit_timer`, reset to `CORE_HIT_FLASH_TIME` (0.6 s)
on any frame the Core takes damage. While it is alive the screen edge pulses
red.

The pulse phase accumulates in `update(dt)`, never from a wall clock, so the
project's determinism rule holds and the value is testable. `draw` only reads it.

The border is a per-alpha `SRCALPHA` surface built **once in `__init__`**: a few
nested rects with decreasing alpha to fade inward. Per frame only `set_alpha`
changes before the blit. The shape is fixed, so recomputing a gradient every
frame would be pure waste.

### Core HP bar

Drawn under the Core, horizontally centred, **only when the Core's screen
position is on-screen and `hp < max_hp`**. A healthy Core draws nothing, so the
view stays clean and the bar's presence is itself information.

Away from the Core the player still gets only the edge pulse — deliberately no
numbers. Reading the Core's condition requires being able to see it.

`_draw_bar` is currently anchored to `_BAR_X` / `_BAR_W`. Generalise it to take
`x` and `width`; the three HUD gauges pass the existing constants. One helper
then covers both HUD and world-space bars.

## File layout

| File | Change |
|---|---|
| `entities/enemy_kinds.py` | **new** — `EnemyKind` + the 4-kind catalogue |
| `entities/enemy.py` | `Virus` → `Enemy` referencing a `kind`, plus aggro/attack timers |
| `entities/core.py` | `hp`, `max_hp`, `damage()`, `is_destroyed` |
| `entities/player.py` | `is_dead` |
| `systems/enemy_ai.py` | **new** — target resolution, attack execution, blasts |
| `systems/combat.py` | `update_enemies` moves to `enemy_ai` |
| `systems/enemy_spawner.py` | weighted kind selection |
| `scenes/play.py` | repair input, pulse, Core bar, world runs while dead |
| `config.py` | Core HP, aggro radii, lock duration, blast multiplier, repair numbers |

**Why the catalogue is not in `config.py`:** `config.py` is a flat list of
name-to-value constants; the catalogue is a table that grows by rows. Flattening
4 kinds × 8 fields into 32 loose constants scatters exactly the numbers that
need to be compared side by side. System-wide scalars stay in `config.py` as the
project rule requires.

## Ripples through existing code

- Every `Virus` reference changes: `play.py` (Trojan hatch), `combat.py`,
  `enemy_spawner.py`, and four test files.
- `update_enemies`' "damage on contact with the player" generalises to
  "damage on contact with the current target".
- The respawn early-return in `PlayScene.update` is removed.
- `_draw_bar` gains `x` and `width` parameters.

## Testing

TDD as usual: pure logic first, headless. The cases that matter:

**Aggro** — acquires inside 300; does not release until past 450; holds its
previous state in between (hysteresis); a hit locks for 4 s regardless of
distance; after the lock expires at 400 px the enemy returns to the Core.

**Attacks** — melee hits exactly once per interval; detaching and reattaching
does not reset the swing timer; a suicide enemy detonates after its fuse; a
target that left the blast radius takes nothing; melee does not damage
non-targets.

**Blast** — a detonation damages both the player and the Core when both are in
radius.

**Core** — `is_destroyed` at 0 hp; repair consumes exactly one item per 25 hp;
healing stops when `/Documents` empties; a full Core consumes nothing.

**While dead** — hunters all target the Core; spawners and enemies keep
updating.

**Spawning** — weighted kind selection is deterministic under an injected
`random.Random`, like the existing spawner tests.

Rendering (pulse, Core bar) is verified only as "draws without raising", the
same level as the existing `test_draw_runs_without_error`.

## Balance numbers are first guesses

Every number in this spec is a starting value. None of them has been played.
`CORE_MAX_HP`, the repair cost, and the spawn interval are the three most
likely to be wrong, and the catalogue exists precisely so that retuning happens
in one table rather than across six files.
