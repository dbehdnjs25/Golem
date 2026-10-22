# 핵심 루프 & 데이터 기반 Implementation Plan

> 작업 단위마다 실패하는 테스트 → 구현 → 검증 4종 → 커밋. 진행은 체크박스(`- [ ]`)로 표시한다.

**Goal:** 채굴 → 배낭 적재 → 코어 귀환 → 창고 자동 입고로 이어지는 게임의 핵심 루프와 그 데이터 기반을 헤드리스 테스트가 되는 형태로 구현한다.

**Architecture:** 기존 스캐폴딩 관례(A안)를 따른다. 로직은 `entities/`·`systems/`·`inventory/`·`items/`의 `pygame` 최소 의존 클래스/함수에 넣어 `update(dt, ...)`를 순수하게 유지하고, 렌더링과 이벤트 축적만 `scenes/play.py`가 담당한다. 벡터 수학은 `pygame.math.Vector2`(헤드리스 지원)를 쓴다.

**Tech Stack:** Python ≥3.10, pygame-ce, pytest + pytest-cov, ruff, mypy(strict).

## Global Constraints

- `config.py`는 `pygame`을 **import하지 않는다**(색상은 RGB 튜플, 상수는 스칼라/튜플).
- 로직은 `update(dt, ...)`에 두고 **명시 인자**로 입력을 받는다. `update` 내부에서 `pygame.key.get_pressed()` 등 **폴링 금지**.
- `pygame.display`/이벤트 펌프/`pygame.quit`은 `core/app.py`에만. 씬·엔티티·시스템은 건드리지 않는다.
- 항상 `FIXED_DT = 1/60`을 `update`에 넘긴다(테스트에서도 고정 dt 사용).
- 단일 자원(데이터 파편). 파편 1개 = `FRAGMENT_MB`.
- 새 패키지(`inventory/`, `items/`)에는 `__init__.py`를 만든다.
- 각 태스크는 실패 테스트 → 실패 확인 → 최소 구현 → 통과 확인 → 커밋 순서(TDD).
- 커밋 메시지 컨벤션: `feat:`, `test:`, `refactor:`.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `src/game/config.py` (수정) | 월드/플레이어/채굴/저장/카메라/스폰/코어/핫바 상수 + 색상 |
| `src/game/entities/player.py` (생성) | 플레이어 위치·이동(`update`), 경계 클램프 |
| `src/game/entities/fragment.py` (생성) | 데이터 파편 hp·`damage`·"고갈 시" 훅 |
| `src/game/entities/core.py` (생성) | 중앙 코어 위치·동기화 반경 |
| `src/game/inventory/__init__.py` (생성) | 패키지 마커 |
| `src/game/inventory/storage.py` (생성) | `Folder`(용량) + `transfer` 이체 |
| `src/game/inventory/hotbar.py` (생성) | `Hotbar` 슬롯·선택·활성 도구 |
| `src/game/items/__init__.py` (생성) | 패키지 마커 |
| `src/game/items/tools.py` (생성) | `MiningTool` 데이터 |
| `src/game/systems/camera.py` (생성) | 월드↔화면 변환, 자유팬 + 잠금 |
| `src/game/systems/mining.py` (생성) | 채굴 1스텝 처리 함수 |
| `src/game/systems/spawner.py` (생성) | 결정론적 파편 스폰 |
| `src/game/scenes/play.py` (교체) | 입력 축적 + `update` 오케스트레이션 + `draw` |
| `tests/test_*.py` (생성) | 각 유닛의 헤드리스 로직 테스트 |

`world/tilemap.py`는 이번 계획에서 **만들지 않는다**(바닥은 시각적 렌더만; 타일 데이터 구조는 적/오염 spec).

---

### Task 1: Config 상수 추가

**Files:**
- Modify: `src/game/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: 없음
- Produces: 아래 상수들(다른 모든 태스크가 참조):
  `WORLD_WIDTH, WORLD_HEIGHT, WORLD_SIZE, TILE_SIZE, PLAYER_SPEED, PLAYER_RADIUS, FRAGMENT_HP, FRAGMENT_RADIUS, MINING_DPS, MINING_RANGE, FRAGMENT_MB, BACKPACK_CAP_MB, DOCUMENTS_CAP_MB, CAMERA_PAN_SPEED, CAMERA_EDGE_MARGIN, SPAWN_INTERVAL, SPAWN_MAX, CORE_RADIUS, CORE_SYNC_RADIUS, HOTBAR_MAX_SLOTS, HOTBAR_START_UNLOCKED`
  색상: `FLOOR_A, FLOOR_B, FRAGMENT_COLOR, CORE_COLOR, PLAYER_COLOR`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from game import config


def test_world_is_larger_than_screen():
    assert config.WORLD_WIDTH > config.SCREEN_WIDTH
    assert config.WORLD_HEIGHT > config.SCREEN_HEIGHT


def test_capacities_are_positive_multiples_of_fragment_mb():
    assert config.FRAGMENT_MB > 0
    assert config.BACKPACK_CAP_MB >= config.FRAGMENT_MB
    assert config.DOCUMENTS_CAP_MB > config.BACKPACK_CAP_MB


def test_sync_radius_exceeds_core_radius():
    assert config.CORE_SYNC_RADIUS > config.CORE_RADIUS


def test_hotbar_start_within_max():
    assert 0 < config.HOTBAR_START_UNLOCKED <= config.HOTBAR_MAX_SLOTS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `AttributeError: module 'game.config' has no attribute 'WORLD_WIDTH'`

- [ ] **Step 3: Add constants**

`src/game/config.py` 끝에 추가:

```python
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
FRAGMENT_MB: Final[int] = 5  # storage size of one fragment

# --- Storage ----------------------------------------------------------------
BACKPACK_CAP_MB: Final[int] = 50  # small field carry -> forces return trips
DOCUMENTS_CAP_MB: Final[int] = 500  # drive store (the "warehouse")

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
HOTBAR_MAX_SLOTS: Final[int] = 7
HOTBAR_START_UNLOCKED: Final[int] = 2

# --- Additional colours (RGB) ----------------------------------------------
FLOOR_A: Final[tuple[int, int, int]] = (26, 26, 40)
FLOOR_B: Final[tuple[int, int, int]] = (32, 32, 48)
FRAGMENT_COLOR: Final[tuple[int, int, int]] = (90, 200, 255)
CORE_COLOR: Final[tuple[int, int, int]] = (120, 255, 180)
PLAYER_COLOR: Final[tuple[int, int, int]] = (240, 240, 255)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/game/config.py tests/test_config.py
git commit -m "feat: add core-loop config constants"
```

---

### Task 2: Player 엔티티

**Files:**
- Create: `src/game/entities/player.py`
- Test: `tests/test_player.py`

**Interfaces:**
- Consumes: `config.PLAYER_SPEED`, `config.PLAYER_RADIUS`
- Produces: `Player(pos: Vector2, radius: float = ..., speed: float = ...)`,
  `Player.update(dt: float, move_dir: Vector2, bounds: tuple[int, int]) -> None`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_player.py
import pygame
import pytest

from game import config
from game.entities.player import Player


def test_moves_in_direction():
    p = Player(pos=pygame.Vector2(100, 100))
    p.update(1.0, pygame.Vector2(1, 0), (2400, 1600))
    assert p.pos.x == 100 + config.PLAYER_SPEED
    assert p.pos.y == 100


def test_diagonal_is_normalized():
    p = Player(pos=pygame.Vector2(500, 500))
    p.update(1.0, pygame.Vector2(1, 1), (2400, 1600))
    travelled = p.pos.distance_to(pygame.Vector2(500, 500))
    assert travelled == pytest.approx(config.PLAYER_SPEED)


def test_zero_direction_does_not_move():
    p = Player(pos=pygame.Vector2(300, 300))
    p.update(1.0, pygame.Vector2(0, 0), (2400, 1600))
    assert p.pos == pygame.Vector2(300, 300)


def test_clamped_to_bounds():
    p = Player(pos=pygame.Vector2(5, 5))
    p.update(1.0, pygame.Vector2(-1, -1), (2400, 1600))
    assert p.pos.x == config.PLAYER_RADIUS
    assert p.pos.y == config.PLAYER_RADIUS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_player.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'game.entities.player'`

- [ ] **Step 3: Implement**

```python
# src/game/entities/player.py
"""Top-down player. Logic-only: movement is a pure function of dt and an
input direction, so it is unit-testable headlessly."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config


@dataclass
class Player:
    pos: pygame.Vector2
    radius: float = config.PLAYER_RADIUS
    speed: float = config.PLAYER_SPEED

    def update(self, dt: float, move_dir: pygame.Vector2, bounds: tuple[int, int]) -> None:
        """Advance by ``dt`` along ``move_dir`` (unnormalized), clamped to bounds."""
        if move_dir.length_squared() > 0:
            self.pos += move_dir.normalize() * self.speed * dt
        width, height = bounds
        self.pos.x = max(self.radius, min(width - self.radius, self.pos.x))
        self.pos.y = max(self.radius, min(height - self.radius, self.pos.y))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_player.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/game/entities/player.py tests/test_player.py
git commit -m "feat: add Player movement entity"
```

---

### Task 3: Fragment 엔티티

**Files:**
- Create: `src/game/entities/fragment.py`
- Test: `tests/test_fragment.py`

**Interfaces:**
- Consumes: `config.FRAGMENT_HP`, `config.FRAGMENT_MB`
- Produces: `Fragment(pos: Vector2, hp: float = ..., mb_value: int = ..., on_depleted: Callable[[Fragment], None] | None = None)`,
  `Fragment.is_depleted -> bool`, `Fragment.damage(amount: float) -> bool` (True로 이번 호출에서 고갈됐음)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fragment.py
import pygame

from game import config
from game.entities.fragment import Fragment


def test_damage_reduces_hp():
    f = Fragment(pos=pygame.Vector2(0, 0))
    depleted = f.damage(10)
    assert f.hp == config.FRAGMENT_HP - 10
    assert depleted is False


def test_damage_returns_true_when_it_depletes():
    f = Fragment(pos=pygame.Vector2(0, 0), hp=15)
    assert f.damage(10) is False
    assert f.damage(10) is True
    assert f.is_depleted


def test_depletion_hook_called_once():
    calls = []
    f = Fragment(pos=pygame.Vector2(0, 0), hp=10, on_depleted=calls.append)
    f.damage(10)
    f.damage(10)  # already depleted, must not fire again
    assert calls == [f]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fragment.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'game.entities.fragment'`

- [ ] **Step 3: Implement**

```python
# src/game/entities/fragment.py
"""A mineable data fragment. Logic-only. The ``on_depleted`` hook exists so a
future disguised "Trojan" fragment can trigger an explosion when mined."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pygame

from game import config


@dataclass
class Fragment:
    pos: pygame.Vector2
    hp: float = config.FRAGMENT_HP
    mb_value: int = config.FRAGMENT_MB
    on_depleted: Callable[[Fragment], None] | None = None

    @property
    def is_depleted(self) -> bool:
        return self.hp <= 0

    def damage(self, amount: float) -> bool:
        """Reduce hp by ``amount``. Return True only on the call that depletes it."""
        if self.is_depleted:
            return False
        self.hp -= amount
        if self.is_depleted:
            if self.on_depleted is not None:
                self.on_depleted(self)
            return True
        return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fragment.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/game/entities/fragment.py tests/test_fragment.py
git commit -m "feat: add Fragment entity with depletion hook"
```

---

### Task 4: Core 엔티티

**Files:**
- Create: `src/game/entities/core.py`
- Test: `tests/test_core.py`

**Interfaces:**
- Consumes: `config.CORE_RADIUS`, `config.CORE_SYNC_RADIUS`
- Produces: `Core(pos: Vector2, radius: float = ..., sync_radius: float = ...)`,
  `Core.is_in_sync_range(point: Vector2) -> bool`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_core.py
import pygame

from game.entities.core import Core


def test_point_inside_sync_range():
    c = Core(pos=pygame.Vector2(1000, 800), sync_radius=100)
    assert c.is_in_sync_range(pygame.Vector2(1050, 800)) is True


def test_point_outside_sync_range():
    c = Core(pos=pygame.Vector2(1000, 800), sync_radius=100)
    assert c.is_in_sync_range(pygame.Vector2(1200, 800)) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_core.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'game.entities.core'`

- [ ] **Step 3: Implement**

```python
# src/game/entities/core.py
"""The central core the player defends and syncs resources to. Logic-only."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config


@dataclass
class Core:
    pos: pygame.Vector2
    radius: float = config.CORE_RADIUS
    sync_radius: float = config.CORE_SYNC_RADIUS

    def is_in_sync_range(self, point: pygame.Vector2) -> bool:
        return self.pos.distance_to(point) <= self.sync_radius
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_core.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/game/entities/core.py tests/test_core.py
git commit -m "feat: add Core entity with sync range"
```

---

### Task 5: Storage — Folder + transfer

**Files:**
- Create: `src/game/inventory/__init__.py` (빈 파일)
- Create: `src/game/inventory/storage.py`
- Test: `tests/test_storage.py`

**Interfaces:**
- Consumes: `config.FRAGMENT_MB`
- Produces:
  `Folder(cap_mb: int, count: int = 0, mb_per_item: int = config.FRAGMENT_MB)`,
  `Folder.used_mb -> int`, `Folder.free_mb -> int`, `Folder.is_full -> bool`,
  `Folder.add(n: int = 1) -> int` (실제로 담긴 개수),
  `transfer(src: Folder, dst: Folder) -> int` (옮긴 개수)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_storage.py
from game.inventory.storage import Folder, transfer


def test_add_increases_count():
    f = Folder(cap_mb=50, mb_per_item=5)  # holds 10
    assert f.add(3) == 3
    assert f.count == 3
    assert f.used_mb == 15


def test_add_caps_at_capacity_and_reports_actual():
    f = Folder(cap_mb=50, mb_per_item=5)  # holds 10
    assert f.add(100) == 10
    assert f.is_full is True
    assert f.add(1) == 0  # no room left


def test_transfer_moves_what_fits():
    src = Folder(cap_mb=50, mb_per_item=5)
    dst = Folder(cap_mb=15, mb_per_item=5)  # holds 3
    src.add(10)
    moved = transfer(src, dst)
    assert moved == 3
    assert dst.count == 3
    assert src.count == 7  # remainder stays (warehouse full)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'game.inventory'`

- [ ] **Step 3: Implement**

`src/game/inventory/__init__.py` 는 빈 파일로 생성.

```python
# src/game/inventory/storage.py
"""Capacity-limited storage for the single data-fragment resource.

Two instances are used by the game: a small field ``Backpack`` (fills while
mining, forces return trips) and the larger ``/Documents`` drive store the
backpack is transferred into at the core. Both are plain ``Folder`` objects.
"""

from __future__ import annotations

from dataclasses import dataclass

from game import config


@dataclass
class Folder:
    cap_mb: int
    count: int = 0
    mb_per_item: int = config.FRAGMENT_MB

    @property
    def used_mb(self) -> int:
        return self.count * self.mb_per_item

    @property
    def free_mb(self) -> int:
        return self.cap_mb - self.used_mb

    @property
    def is_full(self) -> bool:
        return self.free_mb < self.mb_per_item

    def add(self, n: int = 1) -> int:
        """Add up to ``n`` items, bounded by capacity. Return the number added."""
        capacity_left = self.free_mb // self.mb_per_item
        added = max(0, min(n, capacity_left))
        self.count += added
        return added


def transfer(src: Folder, dst: Folder) -> int:
    """Move as many items as fit from ``src`` into ``dst``. Return count moved."""
    moved = dst.add(src.count)
    src.count -= moved
    return moved
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_storage.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/game/inventory/__init__.py src/game/inventory/storage.py tests/test_storage.py
git commit -m "feat: add capacity-limited Folder storage and transfer"
```

---

### Task 6: MiningTool + Hotbar

**Files:**
- Create: `src/game/items/__init__.py` (빈 파일)
- Create: `src/game/items/tools.py`
- Create: `src/game/inventory/hotbar.py`
- Test: `tests/test_hotbar.py`

**Interfaces:**
- Consumes: `config.MINING_RANGE`, `config.MINING_DPS`, `config.HOTBAR_MAX_SLOTS`, `config.HOTBAR_START_UNLOCKED`
- Produces:
  `MiningTool(range: float = ..., dps: float = ..., name: str = "Mining Beam")` (frozen),
  `Hotbar.create() -> Hotbar` (`slots` 길이 `HOTBAR_MAX_SLOTS`, 전부 None),
  `Hotbar.slots: list[object | None]`, `Hotbar.unlocked: int`, `Hotbar.selected: int`,
  `Hotbar.select(index: int) -> None` (unlocked 범위 밖은 무시),
  `Hotbar.active_tool -> object | None`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_hotbar.py
from game import config
from game.inventory.hotbar import Hotbar
from game.items.tools import MiningTool


def test_create_has_max_empty_slots():
    hb = Hotbar.create()
    assert len(hb.slots) == config.HOTBAR_MAX_SLOTS
    assert all(s is None for s in hb.slots)
    assert hb.unlocked == config.HOTBAR_START_UNLOCKED


def test_active_tool_reflects_selection():
    hb = Hotbar.create()
    tool = MiningTool()
    hb.slots[0] = tool
    assert hb.active_tool is tool


def test_select_ignores_locked_slots():
    hb = Hotbar.create()  # unlocked == 2 -> valid indices 0,1
    hb.select(1)
    assert hb.selected == 1
    hb.select(5)  # locked
    assert hb.selected == 1


def test_mining_tool_defaults():
    t = MiningTool()
    assert t.range == config.MINING_RANGE
    assert t.dps == config.MINING_DPS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_hotbar.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'game.items'`

- [ ] **Step 3: Implement**

`src/game/items/__init__.py` 는 빈 파일로 생성.

```python
# src/game/items/tools.py
"""Usable tools. Only the mining tool exists in this milestone; the weapon
tool arrives with the combat spec."""

from __future__ import annotations

from dataclasses import dataclass

from game import config


@dataclass(frozen=True)
class MiningTool:
    range: float = config.MINING_RANGE
    dps: float = config.MINING_DPS
    name: str = "Mining Beam"
```

```python
# src/game/inventory/hotbar.py
"""The CPU-cache hotbar: a fixed number of slots, only some unlocked. The
selected slot's item is the active tool driving the left mouse button."""

from __future__ import annotations

from dataclasses import dataclass

from game import config


@dataclass
class Hotbar:
    slots: list[object | None]
    unlocked: int = config.HOTBAR_START_UNLOCKED
    selected: int = 0

    @classmethod
    def create(cls) -> Hotbar:
        return cls(slots=[None] * config.HOTBAR_MAX_SLOTS)

    def select(self, index: int) -> None:
        if 0 <= index < self.unlocked:
            self.selected = index

    @property
    def active_tool(self) -> object | None:
        return self.slots[self.selected]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_hotbar.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/game/items/__init__.py src/game/items/tools.py src/game/inventory/hotbar.py tests/test_hotbar.py
git commit -m "feat: add MiningTool and Hotbar selection"
```

---

### Task 7: Camera 시스템

**Files:**
- Create: `src/game/systems/camera.py`
- Test: `tests/test_camera.py`

**Interfaces:**
- Consumes: `config.CAMERA_PAN_SPEED`, `config.CAMERA_EDGE_MARGIN`
- Produces:
  `Camera(offset: Vector2, view_size: tuple[int,int], world_size: tuple[int,int], mode: str = LOCKED)`,
  module constants `FREE = "free"`, `LOCKED = "locked"`,
  `Camera.world_to_screen(point) -> Vector2`, `Camera.screen_to_world(point) -> Vector2`,
  `Camera.center_on(point) -> None`, `Camera.toggle_lock(player_pos) -> None`,
  `Camera.update(dt, player_pos, mouse_screen, mining_held) -> None`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_camera.py
import pygame

from game import config
from game.systems.camera import FREE, LOCKED, Camera

VIEW = (960, 540)
WORLD = (2400, 1600)


def _cam(mode=LOCKED):
    return Camera(offset=pygame.Vector2(500, 400), view_size=VIEW, world_size=WORLD, mode=mode)


def test_screen_world_roundtrip():
    cam = _cam()
    p = pygame.Vector2(123, 456)
    assert cam.screen_to_world(cam.world_to_screen(p)) == p


def test_locked_update_centers_on_player():
    cam = _cam(LOCKED)
    cam.update(1 / 60, pygame.Vector2(1200, 800), (0, 0), False)
    assert cam.offset == pygame.Vector2(1200 - 480, 800 - 270)


def test_toggle_from_locked_to_free_keeps_offset():
    cam = _cam(LOCKED)
    before = pygame.Vector2(cam.offset)
    cam.toggle_lock(pygame.Vector2(1200, 800))
    assert cam.mode == FREE
    assert cam.offset == before


def test_toggle_to_locked_snaps_to_player():
    cam = _cam(FREE)
    cam.toggle_lock(pygame.Vector2(1200, 800))
    assert cam.mode == LOCKED
    assert cam.offset == pygame.Vector2(1200 - 480, 800 - 270)


def test_free_pan_at_left_edge_moves_offset_left():
    cam = _cam(FREE)
    cam.update(1.0, pygame.Vector2(1200, 800), (5, 300), False)  # mouse near left edge
    assert cam.offset.x == 500 - config.CAMERA_PAN_SPEED


def test_mining_held_suppresses_pan():
    cam = _cam(FREE)
    cam.update(1.0, pygame.Vector2(1200, 800), (5, 300), True)
    assert cam.offset == pygame.Vector2(500, 400)


def test_offset_clamped_to_world():
    cam = Camera(offset=pygame.Vector2(0, 0), view_size=VIEW, world_size=WORLD, mode=FREE)
    cam.update(1.0, pygame.Vector2(1200, 800), (5, 5), False)  # tries to pan up-left past 0
    assert cam.offset.x == 0
    assert cam.offset.y == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_camera.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'game.systems.camera'`

- [ ] **Step 3: Implement**

```python
# src/game/systems/camera.py
"""World<->screen transform with two modes: LOCKED follows the player;
FREE pans when the mouse hits a screen edge (League-of-Legends style, toggled
with Y). Pure math given its inputs, so it is fully testable headlessly."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config

FREE = "free"
LOCKED = "locked"


@dataclass
class Camera:
    offset: pygame.Vector2  # world coord shown at the view's top-left
    view_size: tuple[int, int]
    world_size: tuple[int, int]
    mode: str = LOCKED

    def world_to_screen(self, point: pygame.Vector2) -> pygame.Vector2:
        return pygame.Vector2(point) - self.offset

    def screen_to_world(self, point: pygame.Vector2) -> pygame.Vector2:
        return pygame.Vector2(point) + self.offset

    def _clamp(self) -> None:
        view_w, view_h = self.view_size
        world_w, world_h = self.world_size
        self.offset.x = max(0.0, min(world_w - view_w, self.offset.x))
        self.offset.y = max(0.0, min(world_h - view_h, self.offset.y))

    def center_on(self, point: pygame.Vector2) -> None:
        view_w, view_h = self.view_size
        self.offset = pygame.Vector2(point) - pygame.Vector2(view_w / 2, view_h / 2)
        self._clamp()

    def toggle_lock(self, player_pos: pygame.Vector2) -> None:
        if self.mode == LOCKED:
            self.mode = FREE
        else:
            self.mode = LOCKED
            self.center_on(player_pos)

    def update(
        self,
        dt: float,
        player_pos: pygame.Vector2,
        mouse_screen: tuple[int, int] | pygame.Vector2,
        mining_held: bool,
    ) -> None:
        if self.mode == LOCKED:
            self.center_on(player_pos)
            return
        if mining_held:
            return  # sharing the mouse with mining: don't pan while channelling
        view_w, view_h = self.view_size
        margin = config.CAMERA_EDGE_MARGIN
        mouse_x, mouse_y = mouse_screen[0], mouse_screen[1]
        direction = pygame.Vector2(0, 0)
        if mouse_x < margin:
            direction.x = -1
        elif mouse_x > view_w - margin:
            direction.x = 1
        if mouse_y < margin:
            direction.y = -1
        elif mouse_y > view_h - margin:
            direction.y = 1
        if direction.length_squared() > 0:
            self.offset += direction * config.CAMERA_PAN_SPEED * dt
            self._clamp()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_camera.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add src/game/systems/camera.py tests/test_camera.py
git commit -m "feat: add Camera with free-pan and lock toggle"
```

---

### Task 8: Mining 시스템

**Files:**
- Create: `src/game/systems/mining.py`
- Test: `tests/test_mining.py`

**Interfaces:**
- Consumes: `MiningTool` (Task 6), `Fragment` (Task 3), `Folder` (Task 5)
- Produces: module status constants `IDLE, MINING, OUT_OF_RANGE, FULL, COLLECTED` (문자열),
  `update_mining(dt, *, active_tool, held, aim_world, player_pos, fragments, backpack) -> str`
  - `fragments`: `list[Fragment]` (고갈된 파편은 이 함수가 제거)
  - `backpack`: `Folder`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_mining.py
import pygame

from game import config
from game.entities.fragment import Fragment
from game.inventory.storage import Folder
from game.items.tools import MiningTool
from game.systems import mining

PLAYER = pygame.Vector2(1000, 1000)


def _backpack():
    return Folder(cap_mb=config.BACKPACK_CAP_MB)


def test_idle_when_not_held():
    frags = [Fragment(pos=pygame.Vector2(1010, 1000))]
    status = mining.update_mining(
        1 / 60, active_tool=MiningTool(), held=False,
        aim_world=pygame.Vector2(1010, 1000), player_pos=PLAYER,
        fragments=frags, backpack=_backpack(),
    )
    assert status == mining.IDLE


def test_channelling_reduces_hp():
    frag = Fragment(pos=pygame.Vector2(1010, 1000))
    frags = [frag]
    status = mining.update_mining(
        1.0, active_tool=MiningTool(), held=True,
        aim_world=pygame.Vector2(1010, 1000), player_pos=PLAYER,
        fragments=frags, backpack=_backpack(),
    )
    assert status == mining.MINING
    assert frag.hp == config.FRAGMENT_HP - config.MINING_DPS


def test_depletion_collects_into_backpack():
    frag = Fragment(pos=pygame.Vector2(1010, 1000), hp=config.MINING_DPS)  # one tick to deplete
    frags = [frag]
    bp = _backpack()
    status = mining.update_mining(
        1.0, active_tool=MiningTool(), held=True,
        aim_world=pygame.Vector2(1010, 1000), player_pos=PLAYER,
        fragments=frags, backpack=bp,
    )
    assert status == mining.COLLECTED
    assert frags == []
    assert bp.count == 1


def test_out_of_range_does_no_damage():
    frag = Fragment(pos=pygame.Vector2(2000, 1000))  # far from player
    frags = [frag]
    status = mining.update_mining(
        1.0, active_tool=MiningTool(), held=True,
        aim_world=pygame.Vector2(2000, 1000), player_pos=PLAYER,
        fragments=frags, backpack=_backpack(),
    )
    assert status == mining.OUT_OF_RANGE
    assert frag.hp == config.FRAGMENT_HP


def test_full_backpack_blocks_and_preserves_fragment():
    frag = Fragment(pos=pygame.Vector2(1010, 1000))
    frags = [frag]
    bp = Folder(cap_mb=config.FRAGMENT_MB)  # holds exactly 1
    bp.add(1)  # now full
    status = mining.update_mining(
        1.0, active_tool=MiningTool(), held=True,
        aim_world=pygame.Vector2(1010, 1000), player_pos=PLAYER,
        fragments=frags, backpack=bp,
    )
    assert status == mining.FULL
    assert frag.hp == config.FRAGMENT_HP  # untouched
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mining.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'game.systems.mining'`

- [ ] **Step 3: Implement**

```python
# src/game/systems/mining.py
"""One mining step. The cursor picks WHICH fragment (nearest to the aim point)
among those within the tool's range of the PLAYER; the tool then channels
damage into it. On depletion the fragment is removed and banked to the backpack.
A full backpack blocks mining without touching the fragment."""

from __future__ import annotations

import pygame

from game.entities.fragment import Fragment
from game.inventory.storage import Folder
from game.items.tools import MiningTool

IDLE = "idle"
MINING = "mining"
OUT_OF_RANGE = "out_of_range"
FULL = "full"
COLLECTED = "collected"


def _pick_target(
    aim_world: pygame.Vector2,
    player_pos: pygame.Vector2,
    fragments: list[Fragment],
    reach: float,
) -> Fragment | None:
    candidates = [
        f
        for f in fragments
        if not f.is_depleted and player_pos.distance_to(f.pos) <= reach
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda f: aim_world.distance_to(f.pos))


def update_mining(
    dt: float,
    *,
    active_tool: object | None,
    held: bool,
    aim_world: pygame.Vector2,
    player_pos: pygame.Vector2,
    fragments: list[Fragment],
    backpack: Folder,
) -> str:
    if not held or not isinstance(active_tool, MiningTool):
        return IDLE
    target = _pick_target(aim_world, player_pos, fragments, active_tool.range)
    if target is None:
        return OUT_OF_RANGE
    if backpack.is_full:
        return FULL  # block before damaging -> fragment preserved
    if target.damage(active_tool.dps * dt):
        backpack.add(1)
        fragments.remove(target)
        return COLLECTED
    return MINING
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mining.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/game/systems/mining.py tests/test_mining.py
git commit -m "feat: add mining system with range/capacity rules"
```

---

### Task 9: Spawner 시스템

**Files:**
- Create: `src/game/systems/spawner.py`
- Test: `tests/test_spawner.py`

**Interfaces:**
- Consumes: `config.SPAWN_INTERVAL`, `config.SPAWN_MAX`, `config.WORLD_*`, `config.FRAGMENT_RADIUS`, `Fragment`, `Core`
- Produces:
  `Spawner(interval: float = ..., max_fragments: int = ...)`,
  `Spawner.update(dt: float, fragments: list[Fragment], core: Core, rng: random.Random) -> Fragment | None`
  (스폰되면 그 `Fragment`를 `fragments`에 append하고 반환, 아니면 None)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_spawner.py
import random

import pygame

from game import config
from game.entities.core import Core
from game.entities.fragment import Fragment
from game.systems.spawner import Spawner

CORE = Core(pos=pygame.Vector2(config.WORLD_WIDTH / 2, config.WORLD_HEIGHT / 2))


def test_no_spawn_before_interval():
    sp = Spawner()
    frags = []
    assert sp.update(0.1, frags, CORE, random.Random(1)) is None
    assert frags == []


def test_spawns_after_interval():
    sp = Spawner()
    frags = []
    result = sp.update(config.SPAWN_INTERVAL, frags, CORE, random.Random(1))
    assert result is not None
    assert frags == [result]


def test_respects_max_fragments():
    sp = Spawner(max_fragments=2)
    frags = [
        Fragment(pos=pygame.Vector2(100, 100)),
        Fragment(pos=pygame.Vector2(200, 200)),
    ]  # already at cap
    assert sp.update(config.SPAWN_INTERVAL, frags, CORE, random.Random(1)) is None
    assert len(frags) == 2


def test_deterministic_with_seed():
    a = Spawner().update(config.SPAWN_INTERVAL, [], CORE, random.Random(42))
    b = Spawner().update(config.SPAWN_INTERVAL, [], CORE, random.Random(42))
    assert a.pos == b.pos


def test_spawn_avoids_core_sync_zone():
    sp = Spawner()
    for seed in range(50):
        frags = []
        frag = sp.update(config.SPAWN_INTERVAL, frags, CORE, random.Random(seed))
        if frag is not None:
            assert CORE.pos.distance_to(frag.pos) >= CORE.sync_radius
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_spawner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'game.systems.spawner'`

- [ ] **Step 3: Implement**

```python
# src/game/systems/spawner.py
"""Time-based fragment spawner. Randomness comes from an injected
``random.Random`` so tests are deterministic. Spawn spots avoid the core's
sync zone and existing fragments; a capped retry count prevents an infinite
loop when the world is saturated."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import pygame

from game import config
from game.entities.core import Core
from game.entities.fragment import Fragment

_MARGIN = 64
_SPAWN_ATTEMPTS = 20


@dataclass
class Spawner:
    interval: float = config.SPAWN_INTERVAL
    max_fragments: int = config.SPAWN_MAX
    _accumulator: float = field(default=0.0, init=False)

    def update(
        self,
        dt: float,
        fragments: list[Fragment],
        core: Core,
        rng: random.Random,
    ) -> Fragment | None:
        self._accumulator += dt
        if self._accumulator < self.interval:
            return None
        self._accumulator -= self.interval
        if len(fragments) >= self.max_fragments:
            return None
        spot = self._find_spot(fragments, core, rng)
        if spot is None:
            return None
        fragment = Fragment(pos=spot)
        fragments.append(fragment)
        return fragment

    def _find_spot(
        self,
        fragments: list[Fragment],
        core: Core,
        rng: random.Random,
    ) -> pygame.Vector2 | None:
        for _ in range(_SPAWN_ATTEMPTS):
            point = pygame.Vector2(
                rng.uniform(_MARGIN, config.WORLD_WIDTH - _MARGIN),
                rng.uniform(_MARGIN, config.WORLD_HEIGHT - _MARGIN),
            )
            if core.pos.distance_to(point) < core.sync_radius + config.FRAGMENT_RADIUS:
                continue
            too_close = any(
                f.pos.distance_to(point) < config.FRAGMENT_RADIUS * 2 for f in fragments
            )
            if too_close:
                continue
            return point
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_spawner.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/game/systems/spawner.py tests/test_spawner.py
git commit -m "feat: add deterministic fragment spawner"
```

---

### Task 10: PlayScene 통합 + 렌더

**Files:**
- Modify (교체): `src/game/scenes/play.py`
- Modify: `tests/test_smoke.py` (옛 `PlayScene.ball` 참조 테스트 교체 — Step 5)
- Test: `tests/test_play_scene.py`

**Interfaces:**
- Consumes: `Player, Fragment, Core, Folder, transfer, Hotbar, MiningTool, Camera(+LOCKED), mining, Spawner`, `config`
- Produces: `PlayScene()` (기존 `Scene` 계약 유지: `handle_event`, `update(dt)`, `draw(surface)`)

> 기존 `PlayScene`(Ball 데모)을 완전히 대체한다. `entities/ball.py`와 `tests/test_ball.py`는 건드리지 않는다(스캐폴딩 제거는 범위 밖). 단, `tests/test_smoke.py`는 옛 `PlayScene.ball`을 참조하므로 **반드시 갱신**한다(Step 5) — 안 하면 `AttributeError`로 회귀.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_play_scene.py
import pygame

from game import config
from game.scenes.play import PlayScene


def _key_event(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def test_number_keys_select_hotbar():
    scene = PlayScene()
    scene.handle_event(_key_event(pygame.K_2))
    assert scene.hotbar.selected == 1
    scene.handle_event(_key_event(pygame.K_1))
    assert scene.hotbar.selected == 0


def test_y_toggles_camera_lock():
    scene = PlayScene()
    start_mode = scene.camera.mode
    scene.handle_event(_key_event(pygame.K_y))
    assert scene.camera.mode != start_mode
    scene.handle_event(_key_event(pygame.K_y))
    assert scene.camera.mode == start_mode


def test_movement_key_moves_player():
    scene = PlayScene()
    start_x = scene.player.pos.x
    scene.handle_event(_key_event(pygame.K_d))
    scene.update(config.FIXED_DT)
    assert scene.player.pos.x > start_x


def test_sync_transfers_backpack_at_core():
    scene = PlayScene()
    scene.player.pos = pygame.Vector2(scene.core.pos)  # stand on the core
    scene.backpack.add(3)
    scene.update(config.FIXED_DT)
    assert scene.backpack.count == 0
    assert scene.documents.count == 3


def test_draw_runs_without_error(surface):
    scene = PlayScene()
    scene.draw(surface)  # must not raise on the 64x64 offscreen surface
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_play_scene.py -v`
Expected: FAIL — `AttributeError: 'PlayScene' object has no attribute 'hotbar'` (기존 Ball 데모라서)

- [ ] **Step 3: Implement (기존 파일 전체 교체)**

```python
# src/game/scenes/play.py
"""Core-loop gameplay scene: mine fragments, fill the backpack, return to the
core to auto-sync into /Documents. Wires the entities and systems together;
accumulates input from events (no polling) and owns all rendering."""

from __future__ import annotations

import random

import pygame

from game import config
from game.core.scene import Scene
from game.entities.core import Core
from game.entities.fragment import Fragment
from game.entities.player import Player
from game.inventory.hotbar import Hotbar
from game.inventory.storage import Folder, transfer
from game.items.tools import MiningTool
from game.systems import mining
from game.systems.camera import LOCKED, Camera
from game.systems.spawner import Spawner

_MOVE_KEYS = {pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d}


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
        self.hotbar.slots[0] = MiningTool()  # slot 1 (key "2") stays empty for the weapon
        self.fragments: list[Fragment] = []
        self.spawner = Spawner()
        self.rng = random.Random(1234)
        self.status = mining.IDLE

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
        self.player.update(dt, self._move_dir(), config.WORLD_SIZE)
        self.camera.update(dt, self.player.pos, self._mouse_screen, self._mouse_held)
        aim_world = self.camera.screen_to_world(self._mouse_screen)
        self.status = mining.update_mining(
            dt,
            active_tool=self.hotbar.active_tool,
            held=self._mouse_held,
            aim_world=aim_world,
            player_pos=self.player.pos,
            fragments=self.fragments,
            backpack=self.backpack,
        )
        self.spawner.update(dt, self.fragments, self.core, self.rng)
        if self.core.is_in_sync_range(self.player.pos):
            transfer(self.backpack, self.documents)

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
        # backpack fill gauge (top-left)
        pygame.draw.rect(surface, (60, 60, 80), pygame.Rect(10, 10, 120, 14))
        frac = self.backpack.used_mb / self.backpack.cap_mb if self.backpack.cap_mb else 0.0
        pygame.draw.rect(surface, (90, 200, 120), pygame.Rect(10, 10, int(120 * frac), 14))
        # hotbar (bottom-left), only unlocked slots
        for i in range(self.hotbar.unlocked):
            x = 10 + i * 44
            color = config.WHITE if i == self.hotbar.selected else (120, 120, 140)
            pygame.draw.rect(
                surface, color, pygame.Rect(x, surface.get_height() - 50, 40, 40), 2
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_play_scene.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Update the obsolete Ball smoke tests**

기존 `tests/test_smoke.py`의 두 테스트(`test_play_scene_draws_something_onto_surface`, `test_play_scene_update_advances_ball`)는 사라진 `PlayScene.ball`을 참조하므로 실패한다. 파일을 아래로 **교체**한다(설정 테스트는 유지, 렌더 스모크는 새 씬에 맞게 다시 씀):

```python
# tests/test_smoke.py
"""Headless smoke tests: exercise the rendering path without a real window."""

from __future__ import annotations

from game import config
from game.scenes.play import PlayScene


def test_config_screen_size_is_consistent() -> None:
    assert config.SCREEN_SIZE == (config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
    assert config.FIXED_DT == 1.0 / config.FPS


def test_play_scene_draws_non_background_pixels(surface) -> None:
    """Drawing the world (floor, core, player) paints over the background."""
    scene = PlayScene()
    surface.fill(config.BACKGROUND)

    scene.draw(surface)

    pixels = {surface.get_at((x, y))[:3] for x in range(64) for y in range(64)}
    assert pixels != {config.BACKGROUND}
```

Run: `pytest tests/test_smoke.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Full quality gate**

Run: `pytest && ruff check . && ruff format --check . && mypy`
Expected: 전체 테스트 PASS, ruff/mypy 오류 없음. (mypy 오류 시 해당 파일의 타입 힌트를 보완하고 재실행.)

- [ ] **Step 7: Commit**

```bash
git add src/game/scenes/play.py tests/test_play_scene.py tests/test_smoke.py
git commit -m "feat: wire core loop into PlayScene with rendering"
```

---

## Self-Review

**1. Spec coverage** (스펙 §별 → 태스크):
- §1 범위(월드/카메라/플레이어/핫바/채굴/스포너/저장/코어/씬) → Task 1–10 ✅
- §2 저장 2단(배낭+/Documents, 둘 다 용량, 만재/부분 이체) → Task 5(Folder/transfer), Task 8(만재 차단), Task 10(sync) ✅
- §3 모듈 구조(타일 데이터 구조 제외) → File Structure + 각 태스크, `world/tilemap.py` 미생성 ✅
- §4 입력 원칙(폴링 금지, 이벤트 축적) → Task 10 `handle_event`/`_move_dir` ✅
- §5.1 프레임 흐름(이동→카메라→채굴→스폰→동기화) → Task 10 `update` ✅
- §5.2 렌더(월드 레이어 + HUD) → Task 10 `draw`/`_draw_floor`/`_draw_hud` ✅
- §6 엔티티 책임(고갈 훅, 카메라 스냅 등) → Task 3/4/7 ✅
- §7 엣지케이스(경계 클램프, 최근접, 스폰 회피/시도상한, 전환 스냅, 채굴 중 팬 억제, 부분 이체, 만재 보존) → Task 7/8/9/10 테스트로 커버 ✅
- §8 초기값 → Task 1 상수 ✅
- §9 테스트 계획 → 각 태스크 테스트가 대응 ✅
- §10 후속 연결점(트로이 훅 등) → Task 3 훅으로 자리 마련, 나머지는 범위 외(의도된 제외) ✅

**2. Placeholder scan:** "TBD/TODO/적절히 처리" 류 없음. 모든 코드 스텝에 실제 코드 포함. ✅

**3. Type consistency:** `update_mining` 상태 상수(`IDLE/MINING/OUT_OF_RANGE/FULL/COLLECTED`)는 Task 8에서 정의·Task 10에서 `mining.<상수>`로만 사용. `Folder.add -> int`, `transfer -> int`, `Camera.update(dt, player_pos, mouse_screen, mining_held)`, `Hotbar.select/active_tool` 시그니처가 태스크 간 일치. `Spawner.update(dt, fragments, core, rng)`도 Task 9 정의와 Task 10 호출 일치. ✅

**4. 통합 계약 확인(재검토):** `app._process_events`가 모든 이벤트(마우스 포함)를 `handle_event`로 전달하고 `scenes.update(FIXED_DT)`를 호출하며 `__main__`이 `PlayScene()`을 무인자로 생성 → Task 10과 일치. `mypy`는 `packages=["game"]`만 검사하므로 테스트 코드는 타입검사 대상 아님. `ruff`는 `src`+`tests` 모두 검사하므로 테스트의 미사용 import 금지(Task 10 반영).

**5. 스캐폴딩 회귀 방지:** 기존 `tests/test_smoke.py`가 옛 `PlayScene.ball`을 참조 → Task 10에서 새 씬에 맞게 갱신(스텝 4)하지 않으면 `AttributeError`로 회귀. 반영 완료.
