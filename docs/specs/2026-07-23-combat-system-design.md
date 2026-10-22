# Combat System — Design Spec

_Date: 2026-07-23 · Project: Defrag (pygame-ce)_

## Goal

Add a basic combat system to the existing mine-and-haul core loop: the player
receives both a mining tool and a weapon from the start, fires projectiles at
enemies, and can dodge with Space. The weapon is data-driven so it can be
upgraded or swapped later without new systems.

Combat reuses existing patterns: logic lives in pure `update(dt, ...)` functions
(headless-testable), tools are frozen dataclasses held in the hotbar, and the
selected hotbar slot drives the left mouse button (slot 1 = mine, slot 2 = shoot).

## Scope (in / out)

**In:** one enemy type (Virus), player projectile weapon, dodge with i-frames,
player HP + contact damage, death penalty + respawn, Trojan fragments that spawn
a Virus when mined, HUD (HP bar, dodge cooldown), enemy/projectile rendering,
unit tests for all new logic.

**Out (YAGNI, future work):** weapon upgrade UI/economy, multiple enemy types,
enemy ranged attacks, ammo, game-over/menu flow, sound.

## New entities

### `entities/enemy.py` — `Virus`
- Fields: `pos`, `hp`, `speed`, `radius`.
- `update(dt, target_pos, bounds)`: move toward `target_pos` at `speed`,
  clamped to world bounds. Pure — no rendering, no globals.
- `is_dead` property (`hp <= 0`).
- `damage(amount)`: reduce hp.

### `entities/projectile.py` — `Projectile`
- Fields: `pos`, `vel` (Vector2), `damage`, `radius`, `ttl` (seconds).
- `update(dt)`: advance `pos += vel*dt`, `ttl -= dt`.
- `is_expired` property (`ttl <= 0`).

## Weapon (item)

### `items/tools.py` — add `WeaponTool` (frozen dataclass)
- Fields: `damage`, `fire_rate` (shots/sec), `projectile_speed`,
  `projectile_ttl`, `projectile_radius`, `name`.
- Upgrades/new weapons = new `WeaponTool` values placed into a hotbar slot.
  No upgrade system is built now; the data shape is the extension point.

Startup wiring (`PlayScene.__init__`): slot 0 = `MiningTool` (existing),
slot 1 = `WeaponTool()` (default gun). Both unlocked (`HOTBAR_START_UNLOCKED = 2`).

## New system — `systems/combat.py` (pure functions)

- `fire_weapon(dt, *, weapon, held, aim_world, player_pos, fire_timer) -> (new_fire_timer, list[Projectile])`
  - When `weapon` is a `WeaponTool` and `held`, emit a projectile toward
    `aim_world` every `1/fire_rate` seconds (accumulator via `fire_timer`).
  - Degenerate aim (`aim_world == player_pos`) emits nothing.
- `update_projectiles(dt, projectiles, enemies, bounds) -> None`
  - Advance each projectile; on circle-overlap with an enemy, apply
    `projectile.damage`, remove the projectile. Remove expired/out-of-bounds
    projectiles and dead enemies (mutates the passed lists).
- `update_enemies(dt, enemies, player, bounds) -> None`
  - Move each enemy toward `player.pos`; on overlap with the player, apply
    `VIRUS_CONTACT_DPS * dt` to `player.hp` **only if** `not player.invulnerable`.

## Enemy appearance (2 sources, 1 enemy type)

1. **Periodic spawn** — `systems/enemy_spawner.py` `EnemySpawner`, mirroring the
   fragment `Spawner`: interval, max cap, injected `random.Random`, spot chosen
   away from the core and the player. Returns the new `Virus` (or `None`).
2. **Trojan fragment** — a normal-looking fragment whose `on_depleted` spawns a
   Virus at its position. Assigned in `PlayScene`: when the fragment `Spawner`
   returns a new fragment, roll `TROJAN_CHANCE` on the scene's injected RNG and,
   if hit, set `fragment.on_depleted = lambda f: enemies.append(Virus(pos=Vector2(f.pos)))`.
   The fragment `Spawner` itself is **not modified** (keeps its tests green).
   Mining a Trojan still banks its data (it is disguised); the punishment is the
   spawned enemy. A full backpack blocks mining before damage, so no free enemy.

## Player changes (`entities/player.py`)

- New fields: `hp`, `max_hp`, plus dodge state `dodge_timer`, `iframe_timer`,
  `dodge_cooldown_timer`.
- `update(dt, move_dir, bounds, dodge_pressed)`:
  - If `dodge_pressed` and `dodge_cooldown_timer <= 0`: start dodge
    (`dodge_timer = DODGE_DURATION`, `iframe_timer = DODGE_IFRAMES`,
    `dodge_cooldown_timer = DODGE_COOLDOWN`). Grants i-frames even if standing
    still; adds a dash only when moving.
  - Effective speed = `speed * DODGE_SPEED_MULT` while `dodge_timer > 0`, else
    `speed`. Move along `move_dir` (normalized), clamp to bounds.
  - Decrement all three timers by `dt`.
- `invulnerable` property = `iframe_timer > 0`.
- The player never applies damage to itself; combat systems read
  `player.invulnerable` and write `player.hp`.

## Death & respawn

- `systems/combat.py` `apply_death_penalty(backpack) -> None`:
  `backpack.count = (backpack.count + 1) // 2` (halve, round up). Backpack only;
  Documents untouched.
- In `PlayScene`: when `player.hp <= 0` and not already respawning, call
  `apply_death_penalty(backpack)`, start `_respawn_timer = RESPAWN_DELAY`, and
  stop processing player movement/tools while respawning. When the timer
  elapses: teleport player to the core center, restore `hp = max_hp`, grant
  `iframe_timer = RESPAWN_IFRAMES` (1.5 s). Enemies persist; no game over.

## HUD / rendering (`PlayScene.draw`)

- HP bar top-left next to the existing backpack gauge (red→drained).
- Dodge cooldown indicator (small bar or dimmed icon while on cooldown).
- Draw enemies as `VIRUS_COLOR` circles, projectiles as small `PROJECTILE_COLOR`
  circles, all via `camera.world_to_screen`.

## Config additions (`game/config.py`, no pygame import)

Player: `PLAYER_MAX_HP=100`. Dodge: `DODGE_SPEED_MULT=2.6`, `DODGE_DURATION=0.18`,
`DODGE_IFRAMES=0.3`, `DODGE_COOLDOWN=0.8`, `RESPAWN_DELAY=2.0`,
`RESPAWN_IFRAMES=1.5`. Virus: `VIRUS_HP=30`, `VIRUS_SPEED=140`, `VIRUS_RADIUS=11`,
`VIRUS_CONTACT_DPS=20`, `VIRUS_SPAWN_INTERVAL=3.0`, `VIRUS_SPAWN_MAX=15`.
Weapon/projectile: `WEAPON_DAMAGE=12`, `WEAPON_FIRE_RATE=4`, `PROJECTILE_SPEED=520`,
`PROJECTILE_TTL=1.2`, `PROJECTILE_RADIUS=4`. Trojan: `TROJAN_CHANCE=0.15`.
Colors: `VIRUS_COLOR`, `PROJECTILE_COLOR`, `HP_COLOR`.

All numbers are tunable defaults.

## Input (`PlayScene.handle_event`)

- Existing: WASD move, 1/2 hotbar select, Y camera lock, Esc pop, mouse.
- Add: `K_SPACE` KEYDOWN → set a one-shot `_dodge_pressed` flag consumed by the
  next `update` (then cleared). Weapon fires via the existing left-mouse
  `_mouse_held` when slot 1 (weapon) is active — no new key.

## Testing (TDD, all headless / pure)

1. Virus moves toward target; stops within bounds.
2. Projectile advances by `vel*dt`; expires when `ttl<=0`.
3. Projectile–enemy overlap applies damage and removes the projectile; enemy
   dies at 0 hp.
4. Weapon fire cadence: N seconds of held fire at `fire_rate` → expected shot
   count; no shot on degenerate aim.
5. Enemy contact applies `CONTACT_DPS*dt` to player hp; **zero** while
   `player.invulnerable`.
6. Dodge sets i-frames and cooldown; `invulnerable` true during the window,
   false after; cooldown blocks re-dodge.
7. `apply_death_penalty`: 5→3, 4→2, 1→1, 0→0.
8. Respawn: after delay, player at core, hp restored, i-frames set.

## File impact

- New: `entities/enemy.py`, `entities/projectile.py`, `systems/combat.py`,
  `systems/enemy_spawner.py`, matching test files.
- Modified: `items/tools.py` (+WeaponTool), `entities/player.py` (hp+dodge),
  `config.py` (constants), `scenes/play.py` (wiring + HUD).
- Untouched: `systems/spawner.py`, `systems/mining.py`, `inventory/*`,
  `entities/fragment.py` (uses existing `on_depleted` hook), `entities/core.py`.
