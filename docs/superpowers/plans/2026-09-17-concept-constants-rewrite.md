# 1단계: 컨셉 상수 정리 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 컴퓨터/파일시스템 컨셉의 상수·아이템 데이터를 걷어내고, 새 세계관(Golem)의 상수와 아이템 카탈로그로 교체한다.

**Architecture:** 데이터 테이블(`config.py`, `items/item_kinds.py`)과 그 테이블을 떠받치는 저장소 모델(`inventory/storage.py`)만 건드린다. 새 시스템(바이옴 생성·낮밤·습격)은 만들지 않는다 — 2단계 이후 일이다. 각 작업이 끝날 때마다 `pytest`가 초록이어야 한다.

**Tech Stack:** pygame-ce, Python >= 3.10, pytest + pytest-cov, ruff, mypy (strict)

**Spec:** `docs/superpowers/specs/2026-08-29-world-rebuild-concept-design.md`

## Global Constraints

- **로직은 순수 `update(dt, ...)`, 렌더링은 `draw(surface)`.** `pygame.display` / 이벤트 펌프 / `pygame.quit`는 `core/app.py`에만 있다.
- **`config.py`는 pygame을 import하지 않는다.** 색은 평범한 RGB 튜플.
- **고정 타임스텝** `FIXED_DT = 1/60`. `update`에 프레임 델타를 직접 넘기지 않는다.
- **TDD**: 실패하는 테스트 → 최소 구현 → 리팩터. `tests/`는 `src/game/`을 미러링한다.
- **`ItemKind`는 frozen dataclass.** `key`는 세이브에 들어가는 안정적 식별자, `name`은 화면에 보이는 글자. 둘은 절대 합치지 않는다.
- **명령어**: `pytest` · `ruff check . && ruff format --check .` · `mypy`
- 각 작업의 마지막 단계는 커밋이다.

## 이 계획이 스펙 1단계보다 조금 넓은 이유

스펙의 1단계는 "`config.py`, 아이템 카탈로그 재작성"이다. 그런데 `ItemKind.mb`(한 개당 파일 크기)가 `inventory/storage.Folder` 전체를 떠받치고 있다 — 용량도, `fits()`도 전부 MB 산수다. `mb`를 남겨두면 새 아이템 21종에 전부 의미 없는 MB 값을 붙였다가 4단계에서 지워야 한다.

그래서 **저장소의 칸 모델 전환(Task 4)을 여기로 당긴다.** 스펙 4단계의 나머지(슬롯 격자 UI, 배낭 아이템, 죽음 시 배낭 드랍)는 그대로 4단계에 남는다.

## 정한 수치

```
핫바        5칸   (스펙에서 이미 결정)
인벤토리   10칸
배낭       +10칸
코어 저장고 40칸
스택 최대  64개   (희귀품은 낮게: 코어 파편 16, 고기 16, 물약 8)
```

## File Structure

| 파일 | 이 계획에서 하는 일 |
|---|---|
| `src/game/config.py` | 컴퓨터 컨셉 상수 폐기, 골렘/칸 상수 신규 |
| `src/game/items/item_kinds.py` | `mb` → `stack_max`, 카탈로그 21종으로 교체 |
| `src/game/inventory/storage.py` | `Folder`(MB) → `Container`(칸) |
| `src/game/inventory/hotbar.py` | 해금 개념 제거, 5칸 고정 |
| `src/game/entities/enemy.py` | `Virus` → `Golem` |
| `src/game/entities/fragment.py` | 트로이 훅 제거, 산출물이 `CORE_SHARD` |
| `src/game/systems/combat.py` | 명명 추종, 죽음 페널티 반올림 방향 수정 |
| `src/game/systems/enemy_spawner.py` | 명명 추종 |
| `src/game/systems/mining.py` | 타입 힌트 추종 |
| `src/game/scenes/play.py` | 명명·트로이·핫바·저장소 전부 추종 |

---

### Task 1: 골렘 명명

컴퓨터 바이러스가 골렘이 된다. 동작은 하나도 바뀌지 않는 순수 개명이다.

**Files:**
- Modify: `src/game/config.py`, `src/game/entities/enemy.py`, `src/game/systems/combat.py`, `src/game/systems/enemy_spawner.py`, `src/game/systems/spawn_common.py`, `src/game/scenes/play.py`
- Test: `tests/test_config.py`, `tests/test_enemy.py`, `tests/test_combat.py`, `tests/test_enemy_spawner.py`

**Interfaces:**
- Consumes: 없음 (첫 작업)
- Produces: `config.TITLE == "Golem"`; `config.GOLEM_HP / GOLEM_SPEED / GOLEM_RADIUS / GOLEM_CONTACT_DPS / GOLEM_SPAWN_INTERVAL / GOLEM_SPAWN_MAX / GOLEM_COLOR`; `game.entities.enemy.Golem` (필드 `pos, hp, speed, radius`, 메서드 `damage(amount) -> None`, `update(dt, target, bounds) -> None`, 프로퍼티 `is_dead -> bool`)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_config.py`의 `test_combat_constants_are_sane`를 이렇게 바꾸고, 새 테스트를 하나 더 넣는다.

```python
def test_title_is_the_new_concept():
    assert config.TITLE == "Golem"


def test_combat_constants_are_sane():
    assert config.PLAYER_MAX_HP > 0
    assert config.WEAPON_FIRE_RATE > 0
    assert config.PROJECTILE_SPEED > 0
    assert 0.0 <= config.TROJAN_CHANCE <= 1.0
    assert config.DODGE_IFRAMES >= config.DODGE_DURATION
    assert len(config.GOLEM_COLOR) == 3
```

- [ ] **Step 2: 실패를 확인한다**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `AttributeError: module 'game.config' has no attribute 'GOLEM_COLOR'`, 그리고 `assert 'Defrag' == 'Golem'`

- [ ] **Step 3: 상수를 개명한다**

`src/game/config.py`:

```python
TITLE: Final[str] = "Golem"
```

```python
# --- Combat: golem enemy ------------------------------------------------------
GOLEM_HP: Final[float] = 30.0
GOLEM_SPEED: Final[float] = 140.0  # px/s toward the player
GOLEM_RADIUS: Final[float] = 11.0
GOLEM_CONTACT_DPS: Final[float] = 20.0  # hp/s while touching the player
GOLEM_SPAWN_INTERVAL: Final[float] = 3.0
GOLEM_SPAWN_MAX: Final[int] = 15
```

```python
GOLEM_COLOR: Final[tuple[int, int, int]] = (230, 80, 90)
```

- [ ] **Step 4: 엔티티를 개명한다**

`src/game/entities/enemy.py` 전체를 이렇게 바꾼다.

```python
"""A golem enemy. Logic-only: chases a target point each step, so it is
unit-testable headlessly. Contact damage is applied by systems/combat, not here."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config
from game.systems.physics import clamp_to_bounds


@dataclass
class Golem:
    pos: pygame.Vector2
    hp: float = config.GOLEM_HP
    speed: float = config.GOLEM_SPEED
    radius: float = config.GOLEM_RADIUS

    @property
    def is_dead(self) -> bool:
        return self.hp <= 0

    def damage(self, amount: float) -> None:
        self.hp -= amount

    def update(self, dt: float, target: pygame.Vector2, bounds: tuple[int, int]) -> None:
        to_target = target - self.pos
        if to_target.length_squared() > 0:
            self.pos += to_target.normalize() * self.speed * dt
        clamp_to_bounds(self.pos, self.radius, bounds)
```

- [ ] **Step 5: 나머지 참조를 따라간다**

`src/game/systems/combat.py`
- `from game.entities.enemy import Virus` → `from game.entities.enemy import Golem`
- `enemies: list[Virus]` 2곳 → `list[Golem]`
- `def _first_hit(shot: Projectile, enemies: list[Virus]) -> Virus | None:` → `list[Golem]) -> Golem | None:`
- `config.VIRUS_CONTACT_DPS` → `config.GOLEM_CONTACT_DPS`

`src/game/systems/enemy_spawner.py`
- 모듈 docstring의 `virus` → `golem`
- `from game.entities.enemy import Virus` → `Golem`
- `interval: float = config.VIRUS_SPAWN_INTERVAL` → `config.GOLEM_SPAWN_INTERVAL`
- `max_enemies: int = config.VIRUS_SPAWN_MAX` → `config.GOLEM_SPAWN_MAX`
- `enemies: list[Virus]` → `list[Golem]`, 반환형 `Virus | None` → `Golem | None`
- 지역변수 `virus = Virus(pos=spot)` → `golem = Golem(pos=spot)` (append/return도 같이)
- `config.VIRUS_RADIUS` → `config.GOLEM_RADIUS`

`src/game/systems/spawn_common.py`
- 모듈 docstring의 `virus spawners` → `golem spawners`

`src/game/scenes/play.py`
- `from game.entities.enemy import Virus` → `Golem`
- `self.enemies: list[Virus] = []` → `list[Golem]`
- `_hatch_virus` 안의 `Virus(...)` → `Golem(...)` (이 메서드는 Task 2에서 통째로 사라진다)
- `config.VIRUS_COLOR` → `config.GOLEM_COLOR`

- [ ] **Step 6: 테스트의 참조를 따라간다**

`tests/test_enemy.py`
- `from game.entities.enemy import Virus` → `Golem`
- `Virus(` 3곳 → `Golem(`
- `config.VIRUS_SPEED` → `config.GOLEM_SPEED`

`tests/test_combat.py`
- `from game.entities.enemy import Virus` → `Golem`
- `Virus(` 전부 → `Golem(`
- `config.VIRUS_CONTACT_DPS` → `config.GOLEM_CONTACT_DPS`

`tests/test_enemy_spawner.py`
- `config.VIRUS_SPAWN_INTERVAL` 3곳 → `config.GOLEM_SPAWN_INTERVAL`
- `Virus` 참조가 있으면 `Golem`으로

- [ ] **Step 7: 통과를 확인한다**

Run: `pytest -q && ruff check . && ruff format --check . && mypy`
Expected: 전부 PASS.
잔재 확인: `grep -rn "VIRUS\|Virus\|Defrag" --include='*.py' src tests` → 결과 없음

- [ ] **Step 8: 커밋**

```bash
git add -A src tests
git commit -m "refactor: rename the virus enemy to golem and retitle the game"
```

---

### Task 2: 트로이 제거

파편이 함정일 수 있다는 개념이 죽었다. 새 세계관에는 트로이 목마가 없다.

**Files:**
- Modify: `src/game/config.py`, `src/game/entities/fragment.py`, `src/game/scenes/play.py`
- Test: `tests/test_config.py`, `tests/test_fragment.py`

**Interfaces:**
- Consumes: Task 1의 `Golem`
- Produces: `Fragment`는 필드 `pos, hp, kind`만 갖는다 (`on_depleted` 없음). `damage(amount) -> bool`은 그대로 — 고갈시키는 호출에서만 True.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_fragment.py`에서 `test_depletion_hook_called_once`를 지우고 이걸 넣는다.

```python
def test_the_trojan_hook_is_gone():
    import dataclasses

    fields = {f.name for f in dataclasses.fields(Fragment)}
    assert "on_depleted" not in fields
```

`tests/test_config.py`의 `test_combat_constants_are_sane`에서 `TROJAN_CHANCE` 줄을 지우고, 대신 이걸 추가한다.

```python
def test_the_trojan_constant_is_gone():
    assert not hasattr(config, "TROJAN_CHANCE")
```

- [ ] **Step 2: 실패를 확인한다**

Run: `pytest tests/test_fragment.py tests/test_config.py -v`
Expected: FAIL — `assert 'on_depleted' not in {...}`, `assert not True`

- [ ] **Step 3: 훅을 제거한다**

`src/game/entities/fragment.py` 전체를 이렇게 바꾼다.

```python
"""A mineable core shard. Logic-only, so it is unit-testable headlessly."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config
from game.items.item_kinds import FRAGMENT, ItemKind


@dataclass
class Fragment:
    pos: pygame.Vector2
    hp: float = config.FRAGMENT_HP
    kind: ItemKind = FRAGMENT  # what mining it out yields

    @property
    def is_depleted(self) -> bool:
        return self.hp <= 0

    def damage(self, amount: float) -> bool:
        """Reduce hp by ``amount``. Return True only on the call that depletes it."""
        if self.is_depleted:
            return False
        self.hp -= amount
        return self.is_depleted
```

`src/game/config.py`에서 이 두 줄을 지운다.

```python
# --- Combat: trojan -----------------------------------------------------------
TROJAN_CHANCE: Final[float] = 0.15  # chance a spawned fragment is a trap
```

`src/game/scenes/play.py`에서 `update`의 이 세 줄을

```python
        new_fragment = self.spawner.update(dt, self.fragments, self.core, self.rng)
        if new_fragment is not None and self.rng.random() < config.TROJAN_CHANCE:
            new_fragment.on_depleted = self._hatch_virus
```

이 한 줄로 바꾼다.

```python
        self.spawner.update(dt, self.fragments, self.core, self.rng)
```

그리고 `_hatch_virus` 메서드 전체를 지운다.

- [ ] **Step 4: 통과를 확인한다**

Run: `pytest -q && ruff check . && ruff format --check . && mypy`
Expected: 전부 PASS.
잔재 확인: `grep -rn "TROJAN\|trojan\|on_depleted\|hatch" --include='*.py' src tests` → 결과 없음

ruff가 `play.py`에서 쓰지 않게 된 import를 잡으면 지운다. `Fragment`는 `self.fragments: list[Fragment]`에서 아직 쓰이므로 남는다.

- [ ] **Step 5: 커밋**

```bash
git add -A src tests
git commit -m "refactor: drop the trojan fragment concept"
```

---

### Task 3: 핫바 5칸 고정

핫바를 조금씩 해금하던 개념이 죽었다. 스펙에서 5칸으로 못박았다.

**Files:**
- Modify: `src/game/config.py`, `src/game/inventory/hotbar.py`, `src/game/scenes/play.py`
- Test: `tests/test_config.py`, `tests/test_hotbar.py`

**Interfaces:**
- Consumes: 없음
- Produces: `config.HOTBAR_SLOTS: Final[int] = 5`. `Hotbar` 필드는 `slots: list[object | None]`, `selected: int`뿐(`unlocked` 없음). `Hotbar.create()`는 5칸짜리 빈 핫바. `select(index)`는 `0 <= index < len(self.slots)`일 때만 반영.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_hotbar.py`의 위쪽 세 테스트를 이렇게 바꾼다.

```python
def test_create_has_five_empty_slots():
    hb = Hotbar.create()
    assert len(hb.slots) == config.HOTBAR_SLOTS
    assert config.HOTBAR_SLOTS == 5
    assert all(s is None for s in hb.slots)


def test_active_tool_reflects_selection():
    hb = Hotbar.create()
    tool = MiningTool()
    hb.slots[0] = tool
    assert hb.active_tool is tool


def test_select_ignores_out_of_range():
    hb = Hotbar.create()
    hb.select(4)  # last valid slot
    assert hb.selected == 4
    hb.select(5)  # past the end
    assert hb.selected == 4
    hb.select(-1)
    assert hb.selected == 4


def test_the_unlock_concept_is_gone():
    assert not hasattr(Hotbar.create(), "unlocked")
    assert not hasattr(config, "HOTBAR_START_UNLOCKED")
    assert not hasattr(config, "HOTBAR_MAX_SLOTS")
```

`tests/test_config.py`에서 `test_hotbar_start_within_max`를 지운다.

- [ ] **Step 2: 실패를 확인한다**

Run: `pytest tests/test_hotbar.py -v`
Expected: FAIL — `AttributeError: module 'game.config' has no attribute 'HOTBAR_SLOTS'`

- [ ] **Step 3: 구현한다**

`src/game/config.py`에서

```python
# --- Hotbar -----------------------------------------------------------------
HOTBAR_MAX_SLOTS: Final[int] = 7
HOTBAR_START_UNLOCKED: Final[int] = 2
```

를 이렇게 바꾼다.

```python
# --- Hotbar -----------------------------------------------------------------
# Fixed at five. Dying keeps the hotbar and drops half of everything else, so
# "is this worth a hotbar slot?" is the protection decision every trip.
HOTBAR_SLOTS: Final[int] = 5
```

`src/game/inventory/hotbar.py` 전체를 이렇게 바꾼다.

```python
"""The five-slot hotbar. The selected slot's item is the active tool driving the
left mouse button. Everything in it survives death; the inventory does not."""

from __future__ import annotations

from dataclasses import dataclass

from game import config


@dataclass
class Hotbar:
    slots: list[object | None]
    selected: int = 0

    @classmethod
    def create(cls) -> Hotbar:
        return cls(slots=[None] * config.HOTBAR_SLOTS)

    def select(self, index: int) -> None:
        if 0 <= index < len(self.slots):
            self.selected = index

    @property
    def active_tool(self) -> object | None:
        return self.slots[self.selected]
```

`src/game/scenes/play.py`의 `_draw_hud`에서

```python
        # hotbar (bottom-left), only unlocked slots
        for i in range(self.hotbar.unlocked):
```

를 이렇게 바꾼다.

```python
        # hotbar (bottom-left)
        for i in range(len(self.hotbar.slots)):
```

- [ ] **Step 4: 통과를 확인한다**

Run: `pytest -q && ruff check . && ruff format --check . && mypy`
Expected: 전부 PASS.
잔재 확인: `grep -rn "unlocked\|HOTBAR_MAX_SLOTS\|HOTBAR_START_UNLOCKED" --include='*.py' src tests` → 결과 없음

- [ ] **Step 5: 커밋**

```bash
git add -A src tests
git commit -m "refactor: fix the hotbar at five slots and drop the unlock concept"
```

---

### Task 4: 저장소를 칸 모델로

MB 용량이 칸 수가 된다. 이게 카탈로그 교체를 막고 있던 유일한 장애물이다.

한 칸은 한 종류의 아이템을 `stack_max`개까지 담는다. 돌 100개를 `stack_max=64`로 넣으면 2칸을 쓴다. 이미 열려 있는 스택에 채워 넣는 건 새 칸을 쓰지 않는다.

**Files:**
- Modify: `src/game/config.py`, `src/game/items/item_kinds.py`, `src/game/inventory/storage.py`, `src/game/systems/combat.py`, `src/game/systems/mining.py`, `src/game/scenes/play.py`
- Test: `tests/test_storage.py`, `tests/test_item_kinds.py`, `tests/test_mining.py`, `tests/test_combat.py`, `tests/test_play_scene.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `config.STACK_MAX_DEFAULT: Final[int] = 64`, `config.INVENTORY_SLOTS: Final[int] = 10`, `config.BACKPACK_SLOTS: Final[int] = 10`, `config.CORE_STORE_SLOTS: Final[int] = 40`
  - `ItemKind(key: str, name: str, stack_max: int, color: tuple[int, int, int])` — `mb` 없음
  - `game.inventory.storage.Container`: 필드 `slots: int`, `items: dict[ItemKind, int]`, `reserved_slots: int`. 프로퍼티 `slots_used -> int`, `free_slots -> int`. 메서드 `count(kind) -> int`, `fits(kind, n) -> int`, `add(kind, n=1) -> int`, `remove(kind, n=1) -> int`, `rows() -> list[tuple[ItemKind, int]]`, `reserve(slots) -> None`, `release(slots) -> None`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_storage.py` 전체를 이걸로 교체한다.

```python
from game.inventory.storage import Container
from game.items.item_kinds import FRAGMENT, ItemKind

# Deliberately NOT in the catalogue: a container must handle any kind it is
# handed, so slots_used cannot depend on a catalogue lookup.
BULK = ItemKind(key="bulk", name="벌크", stack_max=10, color=(1, 2, 3))


def test_add_counts_per_kind_and_bills_slots():
    c = Container(slots=4)
    assert c.add(BULK, 3) == 3
    assert c.count(BULK) == 3
    assert c.slots_used == 1  # a partial stack still occupies a slot
    assert c.free_slots == 3


def test_a_full_stack_rolls_over_into_the_next_slot():
    c = Container(slots=4)
    c.add(BULK, 10)
    assert c.slots_used == 1
    c.add(BULK, 1)
    assert c.slots_used == 2


def test_topping_up_an_open_stack_takes_no_new_slot():
    c = Container(slots=1)
    c.add(BULK, 4)
    assert c.free_slots == 0  # the only slot is taken
    assert c.add(BULK, 6) == 6  # but the open stack still has room
    assert c.count(BULK) == 10
    assert c.add(BULK, 1) == 0  # now it is genuinely full


def test_add_caps_at_slot_capacity_and_reports_actual():
    c = Container(slots=2)
    assert c.add(BULK, 100) == 20
    assert c.add(BULK, 1) == 0
    assert c.free_slots == 0


def test_remove_is_bounded_by_what_is_stored():
    c = Container(slots=4)
    c.add(BULK, 4)
    assert c.remove(BULK, 3) == 3
    assert c.count(BULK) == 1
    assert c.remove(BULK, 99) == 1
    assert c.count(BULK) == 0
    assert c.slots_used == 0  # an emptied row frees its slot


def test_removing_an_absent_kind_reports_zero():
    c = Container(slots=4)
    assert c.remove(BULK, 5) == 0


def test_kinds_are_counted_separately_and_share_the_slots():
    c = Container(slots=2)
    c.add(BULK, 10)  # one full slot
    assert c.count(BULK) == 10
    assert c.count(FRAGMENT) == 0
    assert c.add(FRAGMENT, 999) == FRAGMENT.stack_max  # one slot left


def test_fits_reports_what_would_actually_go_in():
    c = Container(slots=2)
    assert c.fits(BULK, 4) == 4
    assert c.fits(BULK, 50) == 20
    c.add(BULK, 15)  # one full stack + a partial holding 5
    assert c.fits(BULK, 50) == 5  # only the open stack's room is left


def test_rows_follow_catalogue_order_and_skip_empties():
    c = Container(slots=10)
    assert c.rows() == []
    c.add(FRAGMENT, 2)
    assert c.rows() == [(FRAGMENT, 2)]
    c.add(FRAGMENT, 3)
    assert c.rows() == [(FRAGMENT, 5)]  # count changed, position did not
    c.remove(FRAGMENT, 5)
    assert c.rows() == []  # an emptied row leaves the list
    # BULK is stored (add/count/slots_used all work on it) but is not in
    # CATALOGUE, so it must never surface in rows() -- this is what actually
    # exercises the "absent from CATALOGUE is invisible here" filtering, not
    # just row ordering.
    c.add(FRAGMENT, 1)
    c.add(BULK, 1)
    assert c.rows() == [(FRAGMENT, 1)]


def test_reserved_slots_cannot_be_taken_by_anything_else():
    c = Container(slots=4)
    c.reserve(3)
    assert c.free_slots == 1
    assert c.fits(BULK, 100) == 10
    assert c.add(BULK, 100) == 10


def test_release_gives_the_slots_back():
    c = Container(slots=4)
    c.reserve(4)
    assert c.fits(BULK, 1) == 0
    c.release(4)
    assert c.fits(BULK, 100) == 40


def test_release_cannot_drive_the_reservation_negative():
    c = Container(slots=4)
    c.reserve(1)
    c.release(99)
    assert c.reserved_slots == 0
    assert c.free_slots == 4


def test_two_containers_do_not_share_the_default_dict():
    a, b = Container(slots=4), Container(slots=4)
    a.add(FRAGMENT, 1)
    assert b.count(FRAGMENT) == 0


def test_the_old_megabyte_api_is_gone():
    import game.inventory.storage as storage

    assert not hasattr(storage, "Folder")
    c = Container(slots=4)
    assert not hasattr(c, "used_mb")
    assert not hasattr(c, "free_mb")
    assert not hasattr(c, "cap_mb")
```

- [ ] **Step 2: 실패를 확인한다**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL — `ImportError: cannot import name 'Container' from 'game.inventory.storage'`

- [ ] **Step 3: 상수를 바꾼다**

`src/game/config.py`에서 이 줄을 지운다.

```python
FRAGMENT_MB: Final[int] = 3  # storage size of one fragment
```

그리고 Storage 절 전체를

```python
# --- Storage ----------------------------------------------------------------
BACKPACK_CAP_MB: Final[int] = 100  # small field carry -> forces return trips (33 fragments)
DOCUMENTS_CAP_MB: Final[int] = 750  # drive store, the "warehouse" (250 fragments)
```

이걸로 바꾼다.

```python
# --- Storage ----------------------------------------------------------------
# Slots, not weight. One slot holds up to a kind's stack_max of that kind, so
# the limit is how many DIFFERENT things you can carry, not how heavy they are.
STACK_MAX_DEFAULT: Final[int] = 64
INVENTORY_SLOTS: Final[int] = 10  # carried by default
BACKPACK_SLOTS: Final[int] = 10  # added by wearing a backpack -> doubles the carry
CORE_STORE_SLOTS: Final[int] = 40  # the store at the core, never carried
```

- [ ] **Step 4: `ItemKind`의 필드를 바꾼다**

카탈로그 교체는 Task 5의 일이므로 여기서는 필드 하나와 `FRAGMENT` 한 줄만 고친다.

```python
@dataclass(frozen=True)
class ItemKind:
    key: str  # stable id, used for storage and comparison
    name: str  # shown in the inventory grid
    stack_max: int  # how many fit in one slot
    color: tuple[int, int, int]  # icon colour


FRAGMENT = ItemKind(
    key="fragment",
    name="데이터 조각",
    stack_max=config.STACK_MAX_DEFAULT,
    color=config.FRAGMENT_COLOR,
)
```

`tests/test_item_kinds.py`에서 `mb`를 쓰는 세 군데를 고친다.

```python
def test_fragment_row_matches_config():
    assert FRAGMENT.key == "fragment"
    assert FRAGMENT.stack_max == config.STACK_MAX_DEFAULT
    assert len(FRAGMENT.color) == 3


def test_kinds_are_frozen_and_hashable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        FRAGMENT.stack_max = 99  # type: ignore[misc]
    assert {FRAGMENT: 1}[FRAGMENT] == 1  # usable as a dict key


def test_every_kind_has_a_positive_stack():
    assert all(k.stack_max > 0 for k in CATALOGUE)
```

- [ ] **Step 5: 저장소를 구현한다**

`src/game/inventory/storage.py` 전체를 이걸로 교체한다.

```python
"""Slot-limited storage.

Three instances are used by the game: the carried inventory, the backpack that
extends it, and the store at the core.

A container is a grid of slots. One slot holds up to a kind's ``stack_max`` of
that kind, so 100 stone at a stack of 64 costs two slots. The limit is how many
different things you can carry home, not how heavy they are -- there is no
weight system.

``reserved_slots`` is space promised to a transfer that is still in flight. It
is subtracted from ``free_slots``, so mining and other transfers cannot take the
landing space out from under a job that has already left its source container.
Topping up an already-open stack is exempt: it consumes no new slot, so it
cannot eat a reservation.

Rows are keyed by the ``ItemKind`` itself (it is frozen, therefore hashable),
not by its ``key`` string: counting the contents then needs no catalogue lookup
and cannot fail on an unlisted kind. Saving writes ``kind.key`` -- that is the
save format's business, not this module's.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game.items.item_kinds import CATALOGUE, ItemKind


@dataclass
class Container:
    slots: int
    items: dict[ItemKind, int] = field(default_factory=dict)
    reserved_slots: int = 0

    @property
    def slots_used(self) -> int:
        return sum((n + kind.stack_max - 1) // kind.stack_max for kind, n in self.items.items())

    @property
    def free_slots(self) -> int:
        return self.slots - self.slots_used - self.reserved_slots

    def count(self, kind: ItemKind) -> int:
        return self.items.get(kind, 0)

    def fits(self, kind: ItemKind, n: int) -> int:
        """How many of ``n`` would actually go in right now.

        The open stack's room comes first and is exempt from the reservation,
        since filling it opens no new slot. Whatever is left needs fresh slots.
        """
        open_room = (-self.count(kind)) % kind.stack_max
        room = open_room + max(0, self.free_slots) * kind.stack_max
        return max(0, min(n, room))

    def add(self, kind: ItemKind, n: int = 1) -> int:
        """Add up to ``n``, bounded by free space. Return the number added."""
        added = self.fits(kind, n)
        if added:
            self.items[kind] = self.count(kind) + added
        return added

    def remove(self, kind: ItemKind, n: int = 1) -> int:
        """Remove up to ``n``, bounded by what is stored. Return the number removed."""
        removed = max(0, min(n, self.count(kind)))
        if removed:
            left = self.count(kind) - removed
            if left:
                self.items[kind] = left
            else:
                del self.items[kind]  # an empty row frees its slot
        return removed

    def rows(self) -> list[tuple[ItemKind, int]]:
        """``(kind, count)`` in catalogue order, empties omitted.

        A kind absent from ``CATALOGUE`` is invisible here. Every kind the game
        actually creates is in the catalogue; leaving one out is a bug in the
        table, not a case to handle.
        """
        return [(kind, self.items[kind]) for kind in CATALOGUE if self.items.get(kind)]

    def reserve(self, slots: int) -> None:
        self.reserved_slots += slots

    def release(self, slots: int) -> None:
        self.reserved_slots = max(0, self.reserved_slots - slots)
```

- [ ] **Step 6: 저장소 테스트 통과를 확인한다**

Run: `pytest tests/test_storage.py tests/test_item_kinds.py -v`
Expected: PASS

- [ ] **Step 7: 사용처를 따라간다**

`src/game/systems/combat.py`
- `from game.inventory.storage import Folder` → `Container`
- `def apply_death_penalty(backpack: Folder) -> None:` → `(backpack: Container)`

`src/game/systems/mining.py`
- `from game.inventory.storage import Folder` → `Container`
- `backpack: Folder,` → `backpack: Container,`

`src/game/scenes/play.py`
- `from game.inventory.storage import Folder` → `Container`
- `self.backpack = Folder(cap_mb=config.BACKPACK_CAP_MB)` → `self.backpack = Container(slots=config.INVENTORY_SLOTS)`
- `self.documents = Folder(cap_mb=config.DOCUMENTS_CAP_MB)` → `self.store = Container(slots=config.CORE_STORE_SLOTS)`
- `update` 안의 `self.documents` → `self.store`
- `_draw_hud`의 첫 두 줄

```python
        # backpack fill gauge
        frac = self.backpack.used_mb / self.backpack.cap_mb if self.backpack.cap_mb else 0.0
```

를 이렇게 바꾼다.

```python
        # inventory fill gauge
        frac = self.backpack.slots_used / self.backpack.slots if self.backpack.slots else 0.0
```

- [ ] **Step 8: 나머지 테스트를 따라간다**

`tests/test_mining.py`
- `from game.inventory.storage import Folder` → `Container`
- `def _backpack() -> Folder: return Folder(cap_mb=config.BACKPACK_CAP_MB)` → `def _backpack() -> Container: return Container(slots=config.INVENTORY_SLOTS)`
- `test_full_backpack_blocks_and_preserves_fragment`의 `bp = Folder(cap_mb=config.FRAGMENT_MB)` 두 줄을 이렇게 바꾼다

```python
    bp = Container(slots=1)  # one slot
    bp.add(FRAGMENT, FRAGMENT.stack_max)  # now full
```

`tests/test_combat.py`
- `from game.inventory.storage import Folder` → `Container`
- `Folder(cap_mb=1000)` 2곳 → `Container(slots=100)`
- 상단의 `HEAVY = ItemKind(key="heavy", name="큰 파일", mb=10, color=(1, 2, 3))` → `HEAVY = ItemKind(key="heavy", name="벌크", stack_max=10, color=(1, 2, 3))`

`tests/test_play_scene.py`
- `scene.documents` 참조 4곳 → `scene.store`

`tests/test_config.py`
- `test_capacities_are_positive_multiples_of_fragment_mb`를 지우고 이걸 넣는다

```python
def test_slot_counts_are_sane():
    assert config.INVENTORY_SLOTS > 0
    assert config.BACKPACK_SLOTS > 0
    assert config.CORE_STORE_SLOTS > config.INVENTORY_SLOTS
    assert config.STACK_MAX_DEFAULT > 0
```

- [ ] **Step 9: 통과를 확인한다**

Run: `pytest -q && ruff check . && ruff format --check . && mypy`
Expected: 전부 PASS.
잔재 확인: `grep -rn "Folder\|cap_mb\|used_mb\|free_mb\|_CAP_MB\|FRAGMENT_MB\|documents" --include='*.py' src tests` → 결과 없음

- [ ] **Step 10: 커밋**

```bash
git add -A src tests
git commit -m "refactor(inventory): replace megabyte capacity with a slot model"
```

---

### Task 5: 아이템 카탈로그 교체

데이터 조각 하나뿐이던 카탈로그를 새 세계관의 21종으로 바꾼다. 조합법은 넣지 않는다 — 5단계 일이다.

**Files:**
- Modify: `src/game/items/item_kinds.py`, `src/game/entities/fragment.py`, `src/game/scenes/play.py`
- Test: `tests/test_item_kinds.py`, `tests/test_storage.py`, `tests/test_mining.py`, `tests/test_combat.py`, `tests/test_play_scene.py`

**Interfaces:**
- Consumes: Task 4의 `ItemKind(key, name, stack_max, color)`와 `Container`
- Produces: `game.items.item_kinds`가 `CORE_SHARD, STONE, WOOD, CHARCOAL, COPPER_ORE, IRON_ORE, GOLD_ORE, ZINC_ORE, COPPER_INGOT, IRON_INGOT, GOLD_INGOT, BRASS_INGOT, STEEL_INGOT, OBSIDIAN, FROST_CRYSTAL, WEATHERED_STONE, BOG_MOSS, THUNDER_STONE, RAW_MEAT, COOKED_MEAT, POTION` 21개를 export. `FRAGMENT`는 사라진다. `CATALOGUE`는 이 순서 그대로의 튜플, `ITEM_KINDS`는 `key -> ItemKind`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_item_kinds.py` 전체를 이걸로 교체한다.

```python
import dataclasses

import pytest

from game import config
from game.items import item_kinds
from game.items.item_kinds import CATALOGUE, CORE_SHARD, ITEM_KINDS, STEEL_INGOT, ItemKind


def test_core_shard_leads_the_catalogue():
    assert CATALOGUE[0] is CORE_SHARD
    assert CORE_SHARD.key == "core_shard"
    assert CORE_SHARD.name == "코어 파편"


def test_the_file_metaphor_is_gone():
    assert not hasattr(item_kinds, "FRAGMENT")
    assert all("데이터" not in k.name for k in CATALOGUE)


def test_the_grade_ladder_is_present():
    ladder = ["stone", "copper_ingot", "iron_ingot", "gold_ingot", "brass_ingot", "steel_ingot"]
    assert all(key in ITEM_KINDS for key in ladder)


def test_zinc_is_an_ore_with_no_ingot():
    # Zinc is smelting-only: it feeds brass and never becomes a tool tier.
    assert "zinc_ore" in ITEM_KINDS
    assert "zinc_ingot" not in ITEM_KINDS


def test_every_biome_material_is_present():
    for key in ("obsidian", "frost_crystal", "weathered_stone", "bog_moss", "thunder_stone"):
        assert key in ITEM_KINDS


def test_lookup_maps_every_catalogue_key():
    assert set(ITEM_KINDS) == {k.key for k in CATALOGUE}
    assert ITEM_KINDS["steel_ingot"] is STEEL_INGOT


def test_kinds_are_frozen_and_hashable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        CORE_SHARD.stack_max = 99  # type: ignore[misc]
    assert {CORE_SHARD: 1}[CORE_SHARD] == 1  # usable as a dict key


def test_every_kind_has_a_positive_stack_and_a_colour():
    assert all(k.stack_max > 0 for k in CATALOGUE)
    assert all(len(k.color) == 3 for k in CATALOGUE)


def test_rare_kinds_stack_lower_than_the_default():
    assert CORE_SHARD.stack_max < config.STACK_MAX_DEFAULT
    assert ITEM_KINDS["potion"].stack_max < config.STACK_MAX_DEFAULT


def test_keys_are_unique():
    keys = [k.key for k in CATALOGUE]
    assert len(keys) == len(set(keys))


def test_names_are_unique():
    names = [k.name for k in CATALOGUE]
    assert len(names) == len(set(names))


def test_kind_is_a_dataclass_with_a_name():
    assert isinstance(CORE_SHARD, ItemKind)
    assert CORE_SHARD.name
```

- [ ] **Step 2: 실패를 확인한다**

Run: `pytest tests/test_item_kinds.py -v`
Expected: FAIL — `ImportError: cannot import name 'CORE_SHARD' from 'game.items.item_kinds'`

- [ ] **Step 3: 카탈로그를 쓴다**

`src/game/items/item_kinds.py` 전체를 이걸로 교체한다.

```python
"""The catalogue of item kinds. Data only -- a frozen row per kind, no behaviour.

Same shape as ``items/tools.py``: the table lives here, the systems that act on
it live in ``systems/`` and ``inventory/``. Adding an item kind is adding a row.

``key`` is the stable identifier that goes into save files; ``name`` is what the
player reads. They are separate so renaming the display text never invalidates a
save.

Recipes are NOT here. This table says what exists, not what turns into what --
smelting and crafting arrive with the crafting stations.
"""

from __future__ import annotations

from dataclasses import dataclass

from game import config

_STACK = config.STACK_MAX_DEFAULT


@dataclass(frozen=True)
class ItemKind:
    key: str  # stable id, used for storage and comparison
    name: str  # shown in the inventory grid
    stack_max: int  # how many fit in one slot
    color: tuple[int, int, int]  # icon colour


# --- The core ------------------------------------------------------------------
# Scattered around the pedestal at the start. Assembling and placing them is what
# starts day one, so they stack low enough to be felt.
CORE_SHARD = ItemKind("core_shard", "코어 파편", 16, config.FRAGMENT_COLOR)

# --- Gathered ------------------------------------------------------------------
STONE = ItemKind("stone", "돌", _STACK, (140, 140, 150))
WOOD = ItemKind("wood", "나무", _STACK, (150, 110, 70))
CHARCOAL = ItemKind("charcoal", "숯", _STACK, (60, 58, 62))

# --- Mined ---------------------------------------------------------------------
# Zinc is smelting-only: it never becomes a tool tier, it only feeds brass. It is
# rare and lives in the outer grassland, so brass costs distance, not depth.
COPPER_ORE = ItemKind("copper_ore", "구리 광석", _STACK, (190, 120, 80))
IRON_ORE = ItemKind("iron_ore", "철 광석", _STACK, (170, 170, 180))
GOLD_ORE = ItemKind("gold_ore", "금 광석", _STACK, (220, 190, 90))
ZINC_ORE = ItemKind("zinc_ore", "아연 광석", _STACK, (190, 200, 210))

# --- Smelted -------------------------------------------------------------------
# The tool grade ladder: 돌 -> 구리 -> 철 -> 금 -> 황동 -> 강철.
COPPER_INGOT = ItemKind("copper_ingot", "구리 주괴", _STACK, (205, 130, 85))
IRON_INGOT = ItemKind("iron_ingot", "철 주괴", _STACK, (185, 185, 195))
GOLD_INGOT = ItemKind("gold_ingot", "금 주괴", _STACK, (240, 205, 95))
BRASS_INGOT = ItemKind("brass_ingot", "황동 주괴", _STACK, (215, 180, 90))
STEEL_INGOT = ItemKind("steel_ingot", "강철 주괴", _STACK, (120, 130, 150))

# --- Biome materials -----------------------------------------------------------
# These never raise a grade. They feed magic and temple locators instead -- grade
# and attribute are two ladders that do not mix.
OBSIDIAN = ItemKind("obsidian", "흑요석", _STACK, (45, 35, 55))
FROST_CRYSTAL = ItemKind("frost_crystal", "서리 결정", _STACK, (150, 220, 240))
WEATHERED_STONE = ItemKind("weathered_stone", "풍화석", _STACK, (185, 175, 155))
BOG_MOSS = ItemKind("bog_moss", "늪 이끼", _STACK, (95, 130, 75))
THUNDER_STONE = ItemKind("thunder_stone", "뇌석", _STACK, (215, 200, 120))

# --- Consumed ------------------------------------------------------------------
# Meat restores stamina only; raw costs HP on top. Potions are the HP answer in
# the field and are deliberately scarce.
RAW_MEAT = ItemKind("raw_meat", "생고기", 16, (200, 110, 115))
COOKED_MEAT = ItemKind("cooked_meat", "익힌 고기", 16, (165, 105, 65))
POTION = ItemKind("potion", "물약", 8, (210, 80, 130))

# Draw order for the inventory grid. Fixed on purpose: rows must not shuffle under
# the cursor as counts change, or drag targets move while the player is aiming.
CATALOGUE: tuple[ItemKind, ...] = (
    CORE_SHARD,
    STONE,
    WOOD,
    CHARCOAL,
    COPPER_ORE,
    IRON_ORE,
    GOLD_ORE,
    ZINC_ORE,
    COPPER_INGOT,
    IRON_INGOT,
    GOLD_INGOT,
    BRASS_INGOT,
    STEEL_INGOT,
    OBSIDIAN,
    FROST_CRYSTAL,
    WEATHERED_STONE,
    BOG_MOSS,
    THUNDER_STONE,
    RAW_MEAT,
    COOKED_MEAT,
    POTION,
)

ITEM_KINDS: dict[str, ItemKind] = {kind.key: kind for kind in CATALOGUE}
```

- [ ] **Step 4: 사용처를 따라간다**

`src/game/entities/fragment.py`
- `from game.items.item_kinds import FRAGMENT, ItemKind` → `from game.items.item_kinds import CORE_SHARD, ItemKind`
- `kind: ItemKind = FRAGMENT` → `kind: ItemKind = CORE_SHARD`

`src/game/scenes/play.py`
- `from game.items.item_kinds import FRAGMENT` → `CORE_SHARD`
- `update` 안의 두 줄

```python
            moved = self.store.add(CORE_SHARD, self.backpack.count(CORE_SHARD))
            self.backpack.remove(CORE_SHARD, moved)
```

- [ ] **Step 5: 나머지 테스트를 따라간다**

`tests/test_storage.py`, `tests/test_mining.py`, `tests/test_combat.py`, `tests/test_play_scene.py` 네 파일에서
- `from game.items.item_kinds import FRAGMENT` → `CORE_SHARD` (`ItemKind`도 같이 import하는 파일은 그대로 유지)
- 본문의 `FRAGMENT` 전부 → `CORE_SHARD` (`FRAGMENT.stack_max` 포함)

- [ ] **Step 6: 통과를 확인한다**

Run: `pytest -q && ruff check . && ruff format --check . && mypy`
Expected: 전부 PASS.
잔재 확인: `grep -rn "FRAGMENT" --include='*.py' src tests` → `config.FRAGMENT_HP` / `FRAGMENT_RADIUS` / `FRAGMENT_COLOR`만 남는다. 이건 코어 파편 엔티티의 상수이므로 새 컨셉에서도 맞는 이름이다.

- [ ] **Step 7: 커밋**

```bash
git add -A src tests
git commit -m "feat(items): replace the catalogue with the new world's materials"
```

---

### Task 6: 죽음 페널티 반올림 방향

스펙이 "떨구는 쪽을 올림"으로 정해졌다. 지금 코드는 남기는 쪽을 올림하고 있어서 1개짜리 희귀품이 보호돼 버린다.

배낭 자체를 떨구는 것과 핫바 제외는 4단계 일이다. 여기서는 반올림만 고친다.

**Files:**
- Modify: `src/game/systems/combat.py`
- Test: `tests/test_combat.py`, `tests/test_play_scene.py`

**Interfaces:**
- Consumes: Task 4의 `Container`, Task 5의 `CORE_SHARD`
- Produces: `combat.apply_death_penalty(backpack: Container) -> None` — 모든 행에서 `ceil(n/2)`개를 떨구고 `floor(n/2)`개를 남긴다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_combat.py`의 `test_death_penalty_halves_round_up`을 이걸로 바꾼다.

```python
@pytest.mark.parametrize(
    "start,kept",
    [(32, 16), (7, 3), (5, 2), (2, 1), (1, 0), (0, 0)],
)
def test_death_penalty_drops_the_rounded_up_half(start, kept):
    # Rounding up on the DROPPED amount means a lone rare item is lost, which is
    # what makes the five hotbar slots a real decision every trip.
    backpack = Container(slots=100)
    backpack.add(CORE_SHARD, start)
    combat.apply_death_penalty(backpack)
    assert backpack.count(CORE_SHARD) == kept
```

같은 파일의 `test_death_penalty_cannot_shelter_one_kind_by_dropping_another`에서 기대값과 주석의 산수를 고친다.

```python
    backpack = Container(slots=100)
    backpack.add(CORE_SHARD, 5)
    backpack.add(HEAVY, 1)
    combat.apply_death_penalty(backpack)

    # Per-row: each kind drops its own rounded-up half (5 -> 3 dropped, 2 kept;
    # 1 -> 1 dropped, 0 kept). A per-total implementation would instead halve the
    # combined count and could spare the smaller HEAVY row entirely to get there,
    # which is exactly the "sheltering" the per-row rule prevents.
    assert backpack.count(CORE_SHARD) == 2
    assert backpack.count(HEAVY) == 0
```

`tests/test_play_scene.py`의 `test_death_applies_penalty_and_starts_respawn`에서

```python
    assert scene.backpack.count(CORE_SHARD) == 2  # drops the rounded-up half
```

- [ ] **Step 2: 실패를 확인한다**

Run: `pytest tests/test_combat.py -k death -v`
Expected: FAIL — `assert 1 == 0` (1개짜리가 아직 살아남는다), `assert 3 == 2`

- [ ] **Step 3: 구현한다**

`src/game/systems/combat.py`의 `apply_death_penalty`를 이렇게 바꾼다.

```python
def apply_death_penalty(backpack: Container) -> None:
    """Drop the rounded-up half of every row. The store at the core is untouched.

    Per-row rather than per-total so no kind can be sheltered by dropping another.
    Rounding up on the dropped side means a count of 1 drops -- rare singles are
    not protected, which is what gives the hotbar its job. ``rows()`` returns a
    fresh list, so mutating during the loop is safe.
    """
    for kind, n in backpack.rows():
        backpack.remove(kind, (n + 1) // 2)
```

- [ ] **Step 4: 통과를 확인한다**

Run: `pytest -q && ruff check . && ruff format --check . && mypy`
Expected: 전부 PASS

- [ ] **Step 5: 커밋**

```bash
git add -A src tests
git commit -m "fix(combat): drop the rounded-up half on death so single rares are lost"
```

---

## 이 계획이 끝나면

`config.py`와 아이템 데이터가 새 세계관 위에 서고, 저장소가 칸 모델이 된다. 게임은 여전히 예전 방식으로 굴러간다 — 파편을 캐서 코어에 넣는 루프 그대로다. 맵도 결계도 낮밤도 아직 없다.

**2단계(맵과 바이옴) 전에 답이 필요한 것:** 바이옴 배치가 매판 랜덤이냐 고정이냐. 랜덤이면 탐지기 아이템이 의미를 갖고, 고정이면 두 번째 판부터 죽는다.
