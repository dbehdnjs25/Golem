# Combat System Implementation Plan

> 작업 단위마다 실패하는 테스트 → 구현 → 검증 4종 → 커밋. 진행은 체크박스(`- [ ]`)로 표시한다.

**Goal:** Add a projectile weapon, dodge, and a Virus enemy (spawned periodically and by Trojan fragments) with HP, contact damage, a death penalty, and core respawn — reusing the existing pure-`update(dt)` + hotbar-tool patterns.

**Architecture:** New logic-only entities (`Virus`, `Projectile`) and pure system functions in `systems/combat.py` and `systems/enemy_spawner.py`. The weapon is a frozen `WeaponTool` in hotbar slot 1; the selected slot drives the left mouse button (slot 0 mines, slot 1 shoots). `PlayScene` wires everything and owns all rendering.

**Tech Stack:** pygame-ce (imported as `pygame`), Python ≥ 3.10, pytest, ruff, mypy (strict).

## Global Constraints

- **pygame-ce** only (imported as `pygame`); never touch `pygame.display`/events/`pygame.quit` outside `core/app.py`.
- All game logic is a pure `update(dt, ...)` taking the timestep explicitly — no wall-clock, no `pygame.key.get_pressed()`, no globals. Deterministic and unit-testable headlessly.
- `game/config.py` must **not** import pygame; colours are plain RGB tuples.
- Randomness comes from an injected `random.Random` so tests are deterministic.
- The fixed step is `config.FIXED_DT = 1/60`; tests pass explicit `dt`.
- Rendering (SDL surfaces) lives only in `draw(surface)`.
- Keep `systems/spawner.py`, `systems/mining.py`, `inventory/*`, `entities/fragment.py`, `entities/core.py` **unmodified**.
- Run `pytest`, `ruff check . && ruff format --check .`, and `mypy` before considering a task done.

---

### Task 1: Combat config constants

**Files:**
- Modify: `src/game/config.py` (append a combat section)
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `PLAYER_MAX_HP`, `DODGE_SPEED_MULT`, `DODGE_DURATION`, `DODGE_IFRAMES`, `DODGE_COOLDOWN`, `RESPAWN_DELAY`, `RESPAWN_IFRAMES`, `VIRUS_HP`, `VIRUS_SPEED`, `VIRUS_RADIUS`, `VIRUS_CONTACT_DPS`, `VIRUS_SPAWN_INTERVAL`, `VIRUS_SPAWN_MAX`, `WEAPON_DAMAGE`, `WEAPON_FIRE_RATE`, `PROJECTILE_SPEED`, `PROJECTILE_TTL`, `PROJECTILE_RADIUS`, `TROJAN_CHANCE`, `VIRUS_COLOR`, `PROJECTILE_COLOR`, `HP_COLOR` — all `Final`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_config.py`:

```python
def test_combat_constants_are_sane():
    from game import config

    assert config.PLAYER_MAX_HP > 0
    assert config.WEAPON_FIRE_RATE > 0
    assert config.PROJECTILE_SPEED > 0
    assert 0.0 <= config.TROJAN_CHANCE <= 1.0
    assert config.DODGE_IFRAMES >= config.DODGE_DURATION
    assert len(config.VIRUS_COLOR) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest.exe tests/test_config.py::test_combat_constants_are_sane -v`
Expected: FAIL with `AttributeError: module 'game.config' has no attribute 'PLAYER_MAX_HP'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/game/config.py`:

```python
# --- Combat: player -----------------------------------------------------------
PLAYER_MAX_HP: Final[float] = 100.0

# --- Combat: dodge ------------------------------------------------------------
DODGE_SPEED_MULT: Final[float] = 2.6  # speed multiplier during a dash
DODGE_DURATION: Final[float] = 0.18  # seconds of dash movement
DODGE_IFRAMES: Final[float] = 0.30  # seconds of invulnerability
DODGE_COOLDOWN: Final[float] = 0.80  # seconds before dodging again
RESPAWN_DELAY: Final[float] = 2.0  # seconds dead before respawn
RESPAWN_IFRAMES: Final[float] = 1.5  # invulnerability granted on respawn

# --- Combat: virus enemy ------------------------------------------------------
VIRUS_HP: Final[float] = 30.0
VIRUS_SPEED: Final[float] = 140.0  # px/s toward the player
VIRUS_RADIUS: Final[float] = 11.0
VIRUS_CONTACT_DPS: Final[float] = 20.0  # hp/s while touching the player
VIRUS_SPAWN_INTERVAL: Final[float] = 3.0
VIRUS_SPAWN_MAX: Final[int] = 15

# --- Combat: weapon / projectile ----------------------------------------------
WEAPON_DAMAGE: Final[float] = 12.0
WEAPON_FIRE_RATE: Final[float] = 4.0  # shots per second while held
PROJECTILE_SPEED: Final[float] = 520.0  # px/s
PROJECTILE_TTL: Final[float] = 1.2  # seconds before a shot despawns
PROJECTILE_RADIUS: Final[float] = 4.0

# --- Combat: trojan -----------------------------------------------------------
TROJAN_CHANCE: Final[float] = 0.15  # chance a spawned fragment is a trap

# --- Combat: colours (RGB) ----------------------------------------------------
VIRUS_COLOR: Final[tuple[int, int, int]] = (230, 80, 90)
PROJECTILE_COLOR: Final[tuple[int, int, int]] = (255, 240, 150)
HP_COLOR: Final[tuple[int, int, int]] = (220, 70, 80)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest.exe tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/game/config.py tests/test_config.py
git commit -m "feat(config): add combat constants"
```

---

### Task 2: Projectile entity

**Files:**
- Create: `src/game/entities/projectile.py`
- Test: `tests/test_projectile.py`

**Interfaces:**
- Consumes: `config` constants.
- Produces: `Projectile(pos, vel, damage, radius=..., ttl=...)` dataclass with
  `update(dt: float) -> None` and `is_expired: bool`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_projectile.py`:

```python
import pygame

from game.entities.projectile import Projectile


def test_moves_along_velocity():
    p = Projectile(pos=pygame.Vector2(0, 0), vel=pygame.Vector2(100, 0), damage=5)
    p.update(0.5)
    assert p.pos == pygame.Vector2(50, 0)


def test_ttl_decreases_and_expires():
    p = Projectile(pos=pygame.Vector2(0, 0), vel=pygame.Vector2(0, 0), damage=5, ttl=0.3)
    assert p.is_expired is False
    p.update(0.3)
    assert p.is_expired is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest.exe tests/test_projectile.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'game.entities.projectile'`

- [ ] **Step 3: Write minimal implementation**

Create `src/game/entities/projectile.py`:

```python
"""A weapon projectile. Logic-only: straight-line travel with a lifetime, so it
is unit-testable headlessly."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config


@dataclass
class Projectile:
    pos: pygame.Vector2
    vel: pygame.Vector2
    damage: float
    radius: float = config.PROJECTILE_RADIUS
    ttl: float = config.PROJECTILE_TTL

    @property
    def is_expired(self) -> bool:
        return self.ttl <= 0

    def update(self, dt: float) -> None:
        self.pos += self.vel * dt
        self.ttl -= dt
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest.exe tests/test_projectile.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/game/entities/projectile.py tests/test_projectile.py
git commit -m "feat(entities): add Projectile"
```

---

### Task 3: Virus enemy entity

**Files:**
- Create: `src/game/entities/enemy.py`
- Test: `tests/test_enemy.py`

**Interfaces:**
- Consumes: `config` constants.
- Produces: `Virus(pos, hp=..., speed=..., radius=...)` dataclass with
  `update(dt: float, target: pygame.Vector2, bounds: tuple[int, int]) -> None`,
  `damage(amount: float) -> None`, and `is_dead: bool`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_enemy.py`:

```python
import pygame

from game import config
from game.entities.enemy import Virus


def test_moves_toward_target():
    v = Virus(pos=pygame.Vector2(0, 0))
    v.update(1.0, pygame.Vector2(100, 0), (2400, 1600))
    assert v.pos.x == config.VIRUS_SPEED
    assert v.pos.y == 0


def test_does_not_move_when_on_target():
    v = Virus(pos=pygame.Vector2(50, 50))
    v.update(1.0, pygame.Vector2(50, 50), (2400, 1600))
    assert v.pos == pygame.Vector2(50, 50)


def test_damage_and_death():
    v = Virus(pos=pygame.Vector2(0, 0), hp=10)
    assert v.is_dead is False
    v.damage(10)
    assert v.is_dead is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest.exe tests/test_enemy.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'game.entities.enemy'`

- [ ] **Step 3: Write minimal implementation**

Create `src/game/entities/enemy.py`:

```python
"""A virus enemy. Logic-only: chases a target point each step, so it is
unit-testable headlessly. Contact damage is applied by systems/combat, not here."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config


@dataclass
class Virus:
    pos: pygame.Vector2
    hp: float = config.VIRUS_HP
    speed: float = config.VIRUS_SPEED
    radius: float = config.VIRUS_RADIUS

    @property
    def is_dead(self) -> bool:
        return self.hp <= 0

    def damage(self, amount: float) -> None:
        self.hp -= amount

    def update(self, dt: float, target: pygame.Vector2, bounds: tuple[int, int]) -> None:
        to_target = target - self.pos
        if to_target.length_squared() > 0:
            self.pos += to_target.normalize() * self.speed * dt
        width, height = bounds
        self.pos.x = max(self.radius, min(width - self.radius, self.pos.x))
        self.pos.y = max(self.radius, min(height - self.radius, self.pos.y))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest.exe tests/test_enemy.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/game/entities/enemy.py tests/test_enemy.py
git commit -m "feat(entities): add Virus enemy"
```

---

### Task 4: WeaponTool item

**Files:**
- Modify: `src/game/items/tools.py`
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: `config` constants.
- Produces: `WeaponTool(damage=..., fire_rate=..., projectile_speed=..., projectile_ttl=..., projectile_radius=..., name=...)` frozen dataclass.

- [ ] **Step 1: Write the failing test**

Create `tests/test_tools.py`:

```python
from game import config
from game.items.tools import MiningTool, WeaponTool


def test_weapon_defaults():
    w = WeaponTool()
    assert w.damage == config.WEAPON_DAMAGE
    assert w.fire_rate == config.WEAPON_FIRE_RATE
    assert w.projectile_speed == config.PROJECTILE_SPEED
    assert isinstance(w.name, str)


def test_weapon_is_immutable_and_upgradable():
    strong = WeaponTool(damage=99, fire_rate=8, name="Overclocked")
    assert strong.damage == 99
    assert MiningTool().name != strong.name
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest.exe tests/test_tools.py -v`
Expected: FAIL with `ImportError: cannot import name 'WeaponTool'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/game/items/tools.py` (below `MiningTool`):

```python
@dataclass(frozen=True)
class WeaponTool:
    damage: float = config.WEAPON_DAMAGE
    fire_rate: float = config.WEAPON_FIRE_RATE  # shots per second
    projectile_speed: float = config.PROJECTILE_SPEED
    projectile_ttl: float = config.PROJECTILE_TTL
    projectile_radius: float = config.PROJECTILE_RADIUS
    name: str = "Pulse Gun"
```

Also update the module docstring's second sentence to: `"The weapon tool fires projectiles; upgrades are new WeaponTool values."`

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest.exe tests/test_tools.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/game/items/tools.py tests/test_tools.py
git commit -m "feat(items): add WeaponTool"
```

---

### Task 5: combat.fire_weapon

**Files:**
- Create: `src/game/systems/combat.py`
- Test: `tests/test_combat.py`

**Interfaces:**
- Consumes: `WeaponTool` (Task 4), `Projectile` (Task 2).
- Produces: `fire_weapon(dt, *, weapon, held, aim_world, player_pos, fire_timer) -> tuple[float, list[Projectile]]`.
  Decrements `fire_timer` by `dt`; when `weapon` is a `WeaponTool`, `held` is
  true, aim is non-degenerate, and `fire_timer <= 0`, emits one `Projectile`
  toward `aim_world` and resets `fire_timer` to `1 / weapon.fire_rate`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_combat.py`:

```python
import pygame

from game.entities.projectile import Projectile
from game.items.tools import MiningTool, WeaponTool
from game.systems import combat


def _fire(steps, dt, *, held=True, weapon=None):
    weapon = weapon or WeaponTool(fire_rate=2.0)  # interval 0.5s
    timer = 0.0
    shots = []
    for _ in range(steps):
        timer, new = combat.fire_weapon(
            dt,
            weapon=weapon,
            held=held,
            aim_world=pygame.Vector2(100, 0),
            player_pos=pygame.Vector2(0, 0),
            fire_timer=timer,
        )
        shots.extend(new)
    return shots


def test_fires_at_fire_rate_when_held():
    shots = _fire(steps=4, dt=0.5)  # dt == interval -> one shot per step
    assert len(shots) == 4
    assert all(isinstance(s, Projectile) for s in shots)


def test_projectile_aims_at_target():
    shots = _fire(steps=1, dt=0.5)
    assert shots[0].vel.x > 0 and shots[0].vel.y == 0


def test_no_fire_when_not_held():
    assert _fire(steps=4, dt=0.5, held=False) == []


def test_no_fire_with_non_weapon_tool():
    assert _fire(steps=4, dt=0.5, weapon=MiningTool()) == []


def test_no_fire_on_degenerate_aim():
    timer, shots = combat.fire_weapon(
        0.5,
        weapon=WeaponTool(fire_rate=2.0),
        held=True,
        aim_world=pygame.Vector2(0, 0),
        player_pos=pygame.Vector2(0, 0),
        fire_timer=0.0,
    )
    assert shots == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest.exe tests/test_combat.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'game.systems.combat'`

- [ ] **Step 3: Write minimal implementation**

Create `src/game/systems/combat.py`:

```python
"""Combat systems: firing, projectile/enemy resolution, contact damage, and the
death penalty. All pure functions operating on injected state, so they are
unit-testable headlessly. Rendering lives in the scene, never here."""

from __future__ import annotations

import pygame

from game import config
from game.entities.enemy import Virus
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.inventory.storage import Folder
from game.items.tools import WeaponTool


def fire_weapon(
    dt: float,
    *,
    weapon: object | None,
    held: bool,
    aim_world: pygame.Vector2,
    player_pos: pygame.Vector2,
    fire_timer: float,
) -> tuple[float, list[Projectile]]:
    fire_timer -= dt
    if not held or not isinstance(weapon, WeaponTool):
        return fire_timer, []
    if fire_timer > 0:
        return fire_timer, []
    aim = aim_world - player_pos
    if aim.length_squared() == 0:
        return fire_timer, []
    velocity = aim.normalize() * weapon.projectile_speed
    shot = Projectile(
        pos=pygame.Vector2(player_pos),
        vel=velocity,
        damage=weapon.damage,
        radius=weapon.projectile_radius,
        ttl=weapon.projectile_ttl,
    )
    return 1.0 / weapon.fire_rate, [shot]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest.exe tests/test_combat.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/game/systems/combat.py tests/test_combat.py
git commit -m "feat(combat): add fire_weapon"
```

---

### Task 6: combat.update_projectiles

**Files:**
- Modify: `src/game/systems/combat.py`
- Test: `tests/test_combat.py`

**Interfaces:**
- Consumes: `Projectile`, `Virus`.
- Produces: `update_projectiles(dt, projectiles, enemies, bounds) -> None`.
  Advances each projectile; a projectile overlapping an enemy (circle test)
  damages that enemy and is removed; expired or out-of-bounds projectiles are
  removed; dead enemies are removed. Mutates both lists in place.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_combat.py`:

```python
from game.entities.enemy import Virus


def test_projectile_hits_and_kills_enemy():
    enemy = Virus(pos=pygame.Vector2(100, 100), hp=5)
    shot = Projectile(pos=pygame.Vector2(100, 100), vel=pygame.Vector2(0, 0), damage=5)
    projectiles = [shot]
    enemies = [enemy]
    combat.update_projectiles(0.016, projectiles, enemies, (2400, 1600))
    assert projectiles == []  # consumed on hit
    assert enemies == []  # died at 0 hp


def test_projectile_misses_and_survives():
    enemy = Virus(pos=pygame.Vector2(1000, 1000), hp=5)
    shot = Projectile(pos=pygame.Vector2(0, 0), vel=pygame.Vector2(10, 0), damage=5, ttl=1.0)
    projectiles = [shot]
    enemies = [enemy]
    combat.update_projectiles(0.016, projectiles, enemies, (2400, 1600))
    assert len(projectiles) == 1
    assert len(enemies) == 1


def test_expired_projectile_removed():
    shot = Projectile(pos=pygame.Vector2(0, 0), vel=pygame.Vector2(0, 0), damage=5, ttl=0.01)
    projectiles = [shot]
    combat.update_projectiles(0.02, projectiles, [], (2400, 1600))
    assert projectiles == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest.exe tests/test_combat.py -k projectile -v`
Expected: FAIL with `AttributeError: module 'game.systems.combat' has no attribute 'update_projectiles'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/game/systems/combat.py`:

```python
def _in_bounds(pos: pygame.Vector2, bounds: tuple[int, int]) -> bool:
    width, height = bounds
    return 0 <= pos.x <= width and 0 <= pos.y <= height


def update_projectiles(
    dt: float,
    projectiles: list[Projectile],
    enemies: list[Virus],
    bounds: tuple[int, int],
) -> None:
    surviving: list[Projectile] = []
    for shot in projectiles:
        shot.update(dt)
        if shot.is_expired or not _in_bounds(shot.pos, bounds):
            continue
        hit = next(
            (
                e
                for e in enemies
                if not e.is_dead and shot.pos.distance_to(e.pos) <= shot.radius + e.radius
            ),
            None,
        )
        if hit is not None:
            hit.damage(shot.damage)
            continue  # projectile consumed
        surviving.append(shot)
    projectiles[:] = surviving
    enemies[:] = [e for e in enemies if not e.is_dead]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest.exe tests/test_combat.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/game/systems/combat.py tests/test_combat.py
git commit -m "feat(combat): add update_projectiles with enemy collision"
```

---

### Task 7: Player HP + dodge

**Files:**
- Modify: `src/game/entities/player.py`
- Test: `tests/test_player.py`

**Interfaces:**
- Consumes: `config` constants.
- Produces: `Player` gains `hp`, `max_hp`, `dodge_timer`, `iframe_timer`,
  `dodge_cooldown_timer` fields; `update` gains a 4th parameter
  `dodge_pressed: bool = False`; and an `invulnerable: bool` property.
  Backward compatible with existing 3-arg `update` calls (default keeps old behaviour).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_player.py`:

```python
def test_dodge_grants_iframes_and_cooldown():
    p = Player(pos=pygame.Vector2(500, 500))
    assert p.invulnerable is False
    p.update(0.0, pygame.Vector2(0, 0), (2400, 1600), dodge_pressed=True)
    assert p.invulnerable is True
    assert p.dodge_cooldown_timer == config.DODGE_COOLDOWN


def test_dodge_iframes_expire():
    p = Player(pos=pygame.Vector2(500, 500))
    p.update(0.0, pygame.Vector2(0, 0), (2400, 1600), dodge_pressed=True)
    p.update(config.DODGE_IFRAMES, pygame.Vector2(0, 0), (2400, 1600))
    assert p.invulnerable is False


def test_dodge_dashes_faster_when_moving():
    normal = Player(pos=pygame.Vector2(500, 500))
    normal.update(config.DODGE_DURATION, pygame.Vector2(1, 0), (2400, 1600))
    dashed = Player(pos=pygame.Vector2(500, 500))
    dashed.update(config.DODGE_DURATION, pygame.Vector2(1, 0), (2400, 1600), dodge_pressed=True)
    assert dashed.pos.x > normal.pos.x


def test_dodge_blocked_during_cooldown():
    p = Player(pos=pygame.Vector2(500, 500))
    p.update(0.0, pygame.Vector2(0, 0), (2400, 1600), dodge_pressed=True)
    p.update(config.DODGE_IFRAMES, pygame.Vector2(0, 0), (2400, 1600))  # iframes end, still cooling
    assert p.invulnerable is False
    p.update(0.0, pygame.Vector2(0, 0), (2400, 1600), dodge_pressed=True)  # re-press mid-cooldown
    assert p.invulnerable is False  # blocked
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest.exe tests/test_player.py -k dodge -v`
Expected: FAIL with `TypeError: update() got an unexpected keyword argument 'dodge_pressed'`

- [ ] **Step 3: Write minimal implementation**

Replace the body of `src/game/entities/player.py` with:

```python
"""Top-down player. Logic-only: movement (and the dodge dash) is a pure function
of dt and input, so it is unit-testable headlessly. Damage is applied by
systems/combat, which reads ``invulnerable`` and writes ``hp``."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config


@dataclass
class Player:
    pos: pygame.Vector2
    radius: float = config.PLAYER_RADIUS
    speed: float = config.PLAYER_SPEED
    hp: float = config.PLAYER_MAX_HP
    max_hp: float = config.PLAYER_MAX_HP
    dodge_timer: float = 0.0  # dash movement remaining
    iframe_timer: float = 0.0  # invulnerability remaining
    dodge_cooldown_timer: float = 0.0  # time until dodge is available again

    @property
    def invulnerable(self) -> bool:
        return self.iframe_timer > 0

    def update(
        self,
        dt: float,
        move_dir: pygame.Vector2,
        bounds: tuple[int, int],
        dodge_pressed: bool = False,
    ) -> None:
        """Advance by ``dt`` along ``move_dir`` (unnormalized), clamped to bounds.
        A dodge grants i-frames immediately (even when standing still) and a
        speed boost while the dash lasts."""
        if dodge_pressed and self.dodge_cooldown_timer <= 0:
            self.dodge_timer = config.DODGE_DURATION
            self.iframe_timer = config.DODGE_IFRAMES
            self.dodge_cooldown_timer = config.DODGE_COOLDOWN

        speed = self.speed * (config.DODGE_SPEED_MULT if self.dodge_timer > 0 else 1.0)
        if move_dir.length_squared() > 0:
            self.pos += move_dir.normalize() * speed * dt
        width, height = bounds
        self.pos.x = max(self.radius, min(width - self.radius, self.pos.x))
        self.pos.y = max(self.radius, min(height - self.radius, self.pos.y))

        self.dodge_timer = max(0.0, self.dodge_timer - dt)
        self.iframe_timer = max(0.0, self.iframe_timer - dt)
        self.dodge_cooldown_timer = max(0.0, self.dodge_cooldown_timer - dt)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest.exe tests/test_player.py -v`
Expected: PASS (existing movement tests still pass — the new param defaults to `False`)

- [ ] **Step 5: Commit**

```bash
git add src/game/entities/player.py tests/test_player.py
git commit -m "feat(player): add hp and dodge with i-frames"
```

---

### Task 8: combat.update_enemies (contact damage)

**Files:**
- Modify: `src/game/systems/combat.py`
- Test: `tests/test_combat.py`

**Interfaces:**
- Consumes: `Virus`, `Player`, `config.VIRUS_CONTACT_DPS`.
- Produces: `update_enemies(dt, enemies, player, bounds) -> None`. Moves each
  enemy toward `player.pos`; while an enemy overlaps the player and the player
  is not invulnerable, subtracts `VIRUS_CONTACT_DPS * dt` from `player.hp`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_combat.py`:

```python
from game.entities.player import Player


def test_enemy_contact_damages_player():
    player = Player(pos=pygame.Vector2(500, 500))
    enemy = Virus(pos=pygame.Vector2(500, 500))
    combat.update_enemies(0.5, [enemy], player, (2400, 1600))
    assert player.hp == config.PLAYER_MAX_HP - config.VIRUS_CONTACT_DPS * 0.5


def test_invulnerable_player_takes_no_contact_damage():
    player = Player(pos=pygame.Vector2(500, 500), iframe_timer=1.0)
    enemy = Virus(pos=pygame.Vector2(500, 500))
    combat.update_enemies(0.5, [enemy], player, (2400, 1600))
    assert player.hp == config.PLAYER_MAX_HP


def test_distant_enemy_deals_no_damage():
    player = Player(pos=pygame.Vector2(0, 0))
    enemy = Virus(pos=pygame.Vector2(2000, 1500))
    combat.update_enemies(0.5, [enemy], player, (2400, 1600))
    assert player.hp == config.PLAYER_MAX_HP
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest.exe tests/test_combat.py -k enemy -v`
Expected: FAIL with `AttributeError: module 'game.systems.combat' has no attribute 'update_enemies'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/game/systems/combat.py`:

```python
def update_enemies(
    dt: float,
    enemies: list[Virus],
    player: Player,
    bounds: tuple[int, int],
) -> None:
    for enemy in enemies:
        enemy.update(dt, player.pos, bounds)
        if player.invulnerable:
            continue
        if enemy.pos.distance_to(player.pos) <= enemy.radius + player.radius:
            player.hp -= config.VIRUS_CONTACT_DPS * dt
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest.exe tests/test_combat.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/game/systems/combat.py tests/test_combat.py
git commit -m "feat(combat): add update_enemies contact damage"
```

---

### Task 9: combat.apply_death_penalty

**Files:**
- Modify: `src/game/systems/combat.py`
- Test: `tests/test_combat.py`

**Interfaces:**
- Consumes: `Folder`.
- Produces: `apply_death_penalty(backpack: Folder) -> None`, setting
  `backpack.count = (backpack.count + 1) // 2` (halve, round up).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_combat.py`:

```python
import pytest

from game.inventory.storage import Folder


@pytest.mark.parametrize("start,expected", [(5, 3), (4, 2), (1, 1), (0, 0)])
def test_death_penalty_halves_round_up(start, expected):
    backpack = Folder(cap_mb=1000, count=start)
    combat.apply_death_penalty(backpack)
    assert backpack.count == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest.exe tests/test_combat.py -k death -v`
Expected: FAIL with `AttributeError: module 'game.systems.combat' has no attribute 'apply_death_penalty'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/game/systems/combat.py`:

```python
def apply_death_penalty(backpack: Folder) -> None:
    """Halve the backpack's item count, rounding up. Documents are untouched."""
    backpack.count = (backpack.count + 1) // 2
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest.exe tests/test_combat.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/game/systems/combat.py tests/test_combat.py
git commit -m "feat(combat): add apply_death_penalty"
```

---

### Task 10: EnemySpawner

**Files:**
- Create: `src/game/systems/enemy_spawner.py`
- Test: `tests/test_enemy_spawner.py`

**Interfaces:**
- Consumes: `Virus`, `Core`, `config` constants.
- Produces: `EnemySpawner(interval=..., max_enemies=...)` dataclass with
  `update(dt, enemies, player_pos, core, rng) -> Virus | None`. Mirrors the
  fragment `Spawner`: accumulates time, spawns at most `max_enemies`, picks a
  spot away from the core sync zone and from the player, appends and returns the
  new `Virus` (or `None`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_enemy_spawner.py`:

```python
import random

import pygame

from game import config
from game.entities.core import Core
from game.entities.enemy import Virus
from game.systems.enemy_spawner import EnemySpawner


def _core():
    return Core(pos=pygame.Vector2(config.WORLD_WIDTH / 2, config.WORLD_HEIGHT / 2))


def test_no_spawn_before_interval():
    spawner = EnemySpawner()
    enemies: list[Virus] = []
    assert spawner.update(0.1, enemies, pygame.Vector2(10, 10), _core(), random.Random(1)) is None
    assert enemies == []


def test_spawns_after_interval():
    spawner = EnemySpawner()
    enemies: list[Virus] = []
    result = spawner.update(
        config.VIRUS_SPAWN_INTERVAL, enemies, pygame.Vector2(10, 10), _core(), random.Random(1)
    )
    assert isinstance(result, Virus)
    assert len(enemies) == 1


def test_respects_max_cap():
    spawner = EnemySpawner(max_enemies=1)
    enemies = [Virus(pos=pygame.Vector2(10, 10))]
    result = spawner.update(
        config.VIRUS_SPAWN_INTERVAL, enemies, pygame.Vector2(10, 10), _core(), random.Random(1)
    )
    assert result is None
    assert len(enemies) == 1


def test_spawn_avoids_core_sync_zone_and_player():
    spawner = EnemySpawner()
    enemies: list[Virus] = []
    core = _core()
    player_pos = pygame.Vector2(100, 100)
    v = spawner.update(config.VIRUS_SPAWN_INTERVAL, enemies, player_pos, core, random.Random(7))
    assert v is not None
    assert core.pos.distance_to(v.pos) >= core.sync_radius
    assert player_pos.distance_to(v.pos) >= 300
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest.exe tests/test_enemy_spawner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'game.systems.enemy_spawner'`

- [ ] **Step 3: Write minimal implementation**

Create `src/game/systems/enemy_spawner.py`:

```python
"""Time-based virus spawner. Randomness comes from an injected ``random.Random``
so tests are deterministic. Spawn spots avoid the core's sync zone and a radius
around the player; a capped retry count prevents an infinite loop."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import pygame

from game import config
from game.entities.core import Core
from game.entities.enemy import Virus

_MARGIN = 64
_SPAWN_ATTEMPTS = 20
_MIN_PLAYER_DIST = 300.0


@dataclass
class EnemySpawner:
    interval: float = config.VIRUS_SPAWN_INTERVAL
    max_enemies: int = config.VIRUS_SPAWN_MAX
    _accumulator: float = field(default=0.0, init=False)

    def update(
        self,
        dt: float,
        enemies: list[Virus],
        player_pos: pygame.Vector2,
        core: Core,
        rng: random.Random,
    ) -> Virus | None:
        self._accumulator += dt
        if self._accumulator < self.interval:
            return None
        self._accumulator -= self.interval
        if len(enemies) >= self.max_enemies:
            return None
        spot = self._find_spot(player_pos, core, rng)
        if spot is None:
            return None
        virus = Virus(pos=spot)
        enemies.append(virus)
        return virus

    def _find_spot(
        self,
        player_pos: pygame.Vector2,
        core: Core,
        rng: random.Random,
    ) -> pygame.Vector2 | None:
        for _ in range(_SPAWN_ATTEMPTS):
            point = pygame.Vector2(
                rng.uniform(_MARGIN, config.WORLD_WIDTH - _MARGIN),
                rng.uniform(_MARGIN, config.WORLD_HEIGHT - _MARGIN),
            )
            if core.pos.distance_to(point) < core.sync_radius + config.VIRUS_RADIUS:
                continue
            if player_pos.distance_to(point) < _MIN_PLAYER_DIST:
                continue
            return point
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest.exe tests/test_enemy_spawner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/game/systems/enemy_spawner.py tests/test_enemy_spawner.py
git commit -m "feat(systems): add EnemySpawner"
```

---

### Task 11: Wire combat into PlayScene (input, update, death/respawn, HUD)

**Files:**
- Modify: `src/game/scenes/play.py`
- Test: `tests/test_play_scene.py`

**Interfaces:**
- Consumes: everything above — `WeaponTool`, `Virus`, `Projectile`, `EnemySpawner`,
  `combat.fire_weapon`, `combat.update_projectiles`, `combat.update_enemies`,
  `combat.apply_death_penalty`, `Player.invulnerable`, `Player.update(..., dodge_pressed=)`.
- Produces: a fully playable scene. New scene attributes for tests:
  `scene.enemies: list[Virus]`, `scene.projectiles: list[Projectile]`,
  `scene._respawn_timer: float`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_play_scene.py`:

```python
from game.entities.enemy import Virus
from game.entities.projectile import Projectile
from game.items.tools import WeaponTool


def test_weapon_in_slot_one_on_start():
    scene = PlayScene()
    assert isinstance(scene.hotbar.slots[1], WeaponTool)


def test_firing_weapon_spawns_projectile():
    scene = PlayScene()
    scene.hotbar.select(1)  # weapon
    scene._mouse_held = True
    scene._mouse_screen = pygame.Vector2(0, 0)  # aim off to a side
    scene.update(config.FIXED_DT)
    assert len(scene.projectiles) >= 1
    assert isinstance(scene.projectiles[0], Projectile)


def test_space_triggers_dodge():
    scene = PlayScene()
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    scene.update(config.FIXED_DT)
    assert scene.player.invulnerable is True


def test_death_applies_penalty_and_starts_respawn():
    scene = PlayScene()
    scene.backpack.add(5)
    scene.player.hp = 0
    scene.update(config.FIXED_DT)
    assert scene.backpack.count == 3  # halved, round up
    assert scene._respawn_timer > 0


def test_respawn_returns_player_to_core():
    scene = PlayScene()
    scene.player.hp = 0
    scene.update(config.FIXED_DT)  # triggers death
    scene._respawn_timer = config.FIXED_DT  # fast-forward to the respawn frame
    scene.update(config.FIXED_DT)
    assert scene.player.pos == scene.core.pos
    assert scene.player.hp == scene.player.max_hp


def test_draw_runs_with_enemies_and_projectiles(surface):
    scene = PlayScene()
    scene.enemies.append(Virus(pos=pygame.Vector2(scene.player.pos)))
    scene.projectiles.append(
        Projectile(pos=pygame.Vector2(scene.player.pos), vel=pygame.Vector2(1, 0), damage=1)
    )
    scene.draw(surface)  # must not raise
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/pytest.exe tests/test_play_scene.py -v`
Expected: FAIL (e.g. `AttributeError: 'PlayScene' object has no attribute 'projectiles'`)

- [ ] **Step 3: Write the implementation**

Edit `src/game/scenes/play.py`.

3a. Extend the imports block:

```python
from game.entities.enemy import Virus
from game.entities.projectile import Projectile
from game.items.tools import MiningTool, WeaponTool
from game.systems import combat, mining
from game.systems.camera import LOCKED, Camera
from game.systems.enemy_spawner import EnemySpawner
from game.systems.spawner import Spawner
```

(Replace the existing `from game.items.tools import MiningTool` and
`from game.systems import mining` lines; keep the others.)

3b. In `__init__`, after `self.hotbar.slots[0] = MiningTool()`, add the weapon
and combat state (replace the old comment about the reserved slot):

```python
        self.hotbar.slots[0] = MiningTool()
        self.hotbar.slots[1] = WeaponTool()
        self.enemies: list[Virus] = []
        self.projectiles: list[Projectile] = []
        self.enemy_spawner = EnemySpawner()
        self._fire_timer = 0.0
        self._dodge_pressed = False
        self._respawn_timer = 0.0
```

3c. In `handle_event`, add a Space case inside the `KEYDOWN` branch (next to the
existing `K_y` case):

```python
            elif event.key == pygame.K_SPACE:
                self._dodge_pressed = True
```

3d. Replace the whole `update` method with:

```python
    def update(self, dt: float) -> None:
        if self._respawn_timer > 0:
            self._respawn_timer -= dt
            if self._respawn_timer <= 0:
                self.player.pos = pygame.Vector2(self.core.pos)
                self.player.hp = self.player.max_hp
                self.player.iframe_timer = config.RESPAWN_IFRAMES
            self._dodge_pressed = False
            return

        self.player.update(dt, self._move_dir(), config.WORLD_SIZE, self._dodge_pressed)
        self._dodge_pressed = False
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
            new_fragment.on_depleted = lambda f: self.enemies.append(
                Virus(pos=pygame.Vector2(f.pos))
            )
        self.enemy_spawner.update(dt, self.enemies, self.player.pos, self.core, self.rng)

        if self.core.is_in_sync_range(self.player.pos):
            transfer(self.backpack, self.documents)

        if self.player.hp <= 0:
            combat.apply_death_penalty(self.backpack)
            self._respawn_timer = config.RESPAWN_DELAY
```

3e. In `draw`, after the fragment loop and before drawing the core, add enemy
and projectile rendering:

```python
        for enemy in self.enemies:
            pygame.draw.circle(
                surface,
                config.VIRUS_COLOR,
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
```

3f. Replace `_draw_hud` with a version that adds an HP bar and a dodge-cooldown
strip below the backpack gauge:

```python
    def _draw_hud(self, surface: pygame.Surface) -> None:
        # backpack fill gauge (top-left)
        pygame.draw.rect(surface, (60, 60, 80), pygame.Rect(10, 10, 120, 14))
        frac = self.backpack.used_mb / self.backpack.cap_mb if self.backpack.cap_mb else 0.0
        pygame.draw.rect(surface, (90, 200, 120), pygame.Rect(10, 10, int(120 * frac), 14))
        # hp bar
        pygame.draw.rect(surface, (60, 60, 80), pygame.Rect(10, 30, 120, 14))
        hp_frac = max(0.0, self.player.hp / self.player.max_hp) if self.player.max_hp else 0.0
        pygame.draw.rect(surface, config.HP_COLOR, pygame.Rect(10, 30, int(120 * hp_frac), 14))
        # dodge cooldown strip (empty = ready)
        cd = self.player.dodge_cooldown_timer / config.DODGE_COOLDOWN
        pygame.draw.rect(surface, (40, 40, 55), pygame.Rect(10, 48, 120, 5))
        pygame.draw.rect(surface, (120, 160, 220), pygame.Rect(10, 48, int(120 * (1 - cd)), 5))
        # hotbar (bottom-left), only unlocked slots
        for i in range(self.hotbar.unlocked):
            x = 10 + i * 44
            color = config.WHITE if i == self.hotbar.selected else (120, 120, 140)
            pygame.draw.rect(surface, color, pygame.Rect(x, surface.get_height() - 50, 40, 40), 2)
```

- [ ] **Step 4: Run the full suite**

Run: `.venv/Scripts/pytest.exe -q`
Expected: PASS (all existing + new tests)

- [ ] **Step 5: Lint, format, and type-check**

Run: `.venv/Scripts/ruff.exe check . && .venv/Scripts/ruff.exe format --check . && .venv/Scripts/mypy.exe`
Expected: no errors. Fix any issues (e.g. add type annotations) and re-run.

- [ ] **Step 6: Manual smoke test (real window)**

Run: `python -m game`
Verify by hand:
- Press `2` → left-click-hold fires yellow projectiles toward the mouse.
- Red viruses appear over time and chase the player; projectiles kill them.
- Space dashes and briefly makes the HP bar untouchable (i-frames).
- Getting swarmed drains the HP bar; at 0 the backpack gauge halves and, after
  ~2 s, the player reappears on the core.
- Mining occasionally spawns a virus (Trojan fragment).

- [ ] **Step 7: Commit**

```bash
git add src/game/scenes/play.py tests/test_play_scene.py
git commit -m "feat(play): wire combat, dodge, and death/respawn into PlayScene"
```

---

## Self-Review

**Spec coverage:**
- Virus entity → Task 3; Projectile → Task 2; WeaponTool (extensible) → Task 4;
  fire/projectiles/contact → Tasks 5, 6, 8; enemy spawn (periodic) → Task 10;
  Trojan spawn → Task 11 (3d); player HP + dodge/i-frames → Task 7; death
  penalty (backpack, round up) → Task 9; respawn at core → Task 11 (3d); HUD
  (HP + dodge) and enemy/projectile rendering → Task 11 (3e, 3f); config →
  Task 1; startup dual tools → Task 11 (3b); Space input → Task 11 (3c). All
  spec sections map to a task.
- Untouched files (spawner, mining, fragment, inventory, core) honoured: Trojan
  is attached via the existing `on_depleted` hook from the scene; the fragment
  `Spawner` is called, not edited.

**Placeholder scan:** No TBD/TODO; every code step shows complete code and every
run step shows an exact command and expected result.

**Type consistency:** `fire_weapon` returns `tuple[float, list[Projectile]]` and
is consumed as `self._fire_timer, shots = ...` (Task 11). `update_projectiles`/
`update_enemies`/`apply_death_penalty` all return `None` and mutate inputs,
matching their call sites. `Player.update` 4th param `dodge_pressed: bool = False`
matches both the scene call (positional) and the tests (keyword). `Virus.update`
signature `(dt, target, bounds)` matches its use in `update_enemies`.
`EnemySpawner.update(dt, enemies, player_pos, core, rng)` matches the scene call.
