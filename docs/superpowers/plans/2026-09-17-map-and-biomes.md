# 2단계: 맵과 바이옴 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사각형 월드를 원형 맵으로 바꾸고, 중앙 초원 + 바깥 링 5등분 바이옴과 사원 자리, 거리에 따른 광물 분포를 만든다. 화면에는 바이옴을 단색으로 칠한다.

**Architecture:** `world/` 패키지를 새로 만든다. `biomes.py`는 `items/item_kinds.py`와 똑같은 frozen dataclass 카탈로그이고, `map.py`의 `WorldMap`은 좌표를 받아 바이옴을 답하는 **순수 데이터 객체**다 — pygame 표면을 만지지 않고, 상태를 바꾸지 않는다. 그래서 헤드리스로 전부 테스트된다. 렌더링은 `scenes/play.py`에만 있다.

**Tech Stack:** pygame-ce, Python >= 3.10, pytest + pytest-cov, ruff, mypy (strict)

**Spec:** `docs/superpowers/specs/2026-08-29-world-rebuild-concept-design.md`

**선행:** `docs/superpowers/plans/2026-09-17-concept-constants-rewrite.md` (1단계, 완료)

## Global Constraints

- **로직은 순수 `update(dt, ...)`, 렌더링은 `draw(surface)`.** `pygame.display` / 이벤트 펌프 / `pygame.quit`는 `core/app.py`에만.
- **`config.py`는 pygame을 import하지 않는다.** 색은 평범한 RGB 튜플.
- **`WorldMap`은 frozen이고 순수하다.** 난수는 `random.Random`을 인자로 받는다 — 절대 모듈 전역 `random`을 쓰지 않는다. 그래야 맵 생성이 재현 가능하다.
- **고정 타임스텝** `FIXED_DT = 1/60`.
- **TDD**: 실패하는 테스트 → 최소 구현 → 리팩터.
- **명령어**: `./.venv/Scripts/python.exe -m pytest` · `-m ruff check . && -m ruff format --check .` · `-m mypy`
- 각 작업의 마지막 단계는 커밋이다.

## 범위 밖 (의도적으로 안 함)

- **타일 에셋** — 사용자가 직접 만든다. 이 계획은 단색으로 칠하고 끝낸다. 나중에 `_draw_world`만 갈아끼우면 되고, `biome_at`은 그대로 쓰인다.
- **지형 효과** — 용암 데미지, 늪 감속, 절벽 낙하. 지형 타일 데이터가 생긴 다음 일이다.
- **사원 건물과 보스** — 8단계. 여기서는 사원 **자리**만 정한다.
- **결계·낮밤·습격** — 3단계.
- **거리에 따른 골렘 강화** — 스펙의 "코어에서 멀수록 강한 골렘"은 6단계(적 재분류와 습격) 일이다. 여기서는 자원 분포만 거리에 반응한다.
- **나무** — 벌목 대상이 아직 엔티티로 없다. 광맥만 거리에 반응하게 만들고, 나무는 5단계(자원과 제작)에서 같은 표에 얹는다.

## 정한 수치

```
맵 반지름        2400   (월드 정사각형 4800×4800, 원이 그 안에 내접)
초원 반지름      1400   ((1400/2400)^2 = 0.34, 스펙의 "맵의 3분의 1")
바이옴 수           5   (링을 72도씩)
사원 반지름 띠  1600 ~ 2200  (안쪽/바깥쪽 끝을 피한다 — 스펙 요구)
사원 각도 여백     12도      (섹터 경계에 걸치면 옆 바이옴 것처럼 보인다)
```

맵 크기는 스펙에서 아직 미정이다. 지름 4800px을 초당 220px로 가로지르면 22초 — 일단 이걸로 굴려보고 조정한다. `MAP_RADIUS` 하나만 고치면 나머지는 따라온다.

## 바이옴 배치: 고정이냐 랜덤이냐

`WorldMap.rotation`(도) 하나가 이걸 정한다. `0.0`이면 고정, `rng.uniform(0, 360)`이면 매판 랜덤이다. **판정 로직은 둘이 똑같다.** 일단 랜덤으로 만들어 두고, 굴려본 뒤 고정으로 바꾸고 싶으면 `WorldMap.create`에서 한 줄만 고친다.

## File Structure

| 파일 | 책임 |
|---|---|
| `src/game/world/__init__.py` | 빈 패키지 표시 |
| `src/game/world/biomes.py` | `Biome` frozen dataclass 카탈로그. 데이터만 |
| `src/game/world/map.py` | `WorldMap` — 좌표 → 바이옴, 원 안 판정/제한, 난수 점, 사원 자리 |
| `src/game/world/resources.py` | 거리 → 광물 분포. 순수 함수 |
| `src/game/config.py` | 맵 반지름·초원 반지름·사원 띠·공백 색 |
| `src/game/systems/physics.py` | `clamp_to_circle` 추가 |
| `src/game/systems/spawn_common.py` | `random_point`가 원 안에서 뽑는다 |
| `src/game/entities/player.py`, `enemy.py` | 경계가 사각형에서 `WorldMap`으로 |
| `src/game/systems/combat.py`, `spawner.py`, `enemy_spawner.py` | 같은 이유로 추종 |
| `src/game/scenes/play.py` | `WorldMap` 보유, 바이옴 단색 렌더링 |
| `CLAUDE.md` | "어디에 무엇" 표에 `world/` 행 추가 |

---

### Task 1: 바이옴 카탈로그

`items/item_kinds.py`와 같은 모양의 데이터 표. 행동은 없다.

**Files:**
- Create: `src/game/world/__init__.py`, `src/game/world/biomes.py`
- Test: `tests/world/__init__.py` 없이 `tests/test_biomes.py`

**Interfaces:**
- Consumes: `game.items.item_kinds`의 `OBSIDIAN, FROST_CRYSTAL, WEATHERED_STONE, BOG_MOSS, THUNDER_STONE, ItemKind`
- Produces: `game.world.biomes`가 export하는 것
  - 속성 상수 `FIRE, ICE, WIND, POISON, LIGHTNING` (전부 `str`)
  - `Biome(key: str, name: str, element: str | None, material: ItemKind | None, color: tuple[int, int, int])` — frozen
  - `GRASSLAND, VOLCANO, SNOWFIELD, WIND_PLATEAU, BOG, WASTELAND`
  - `RING_BIOMES: tuple[Biome, ...]` — 링 순서 = 난이도 순서, 5개
  - `BIOMES: tuple[Biome, ...]` — `(GRASSLAND,) + RING_BIOMES`, 6개
  - `BIOME_BY_KEY: dict[str, Biome]`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_biomes.py`를 새로 만든다.

```python
from game.items import item_kinds
from game.world import biomes
from game.world.biomes import BIOME_BY_KEY, BIOMES, GRASSLAND, RING_BIOMES, Biome


def test_there_are_five_ring_biomes_plus_the_grassland():
    assert len(RING_BIOMES) == 5
    assert BIOMES == (GRASSLAND,) + RING_BIOMES


def test_ring_order_is_difficulty_order():
    # Volcano first: lava is a visible, stationary hazard, the easiest to read.
    # Bog fourth: its stamina drain is unfair before cooking and potions exist.
    # Wasteland last: raids come in crowds and chaining is the answer to them.
    assert [b.key for b in RING_BIOMES] == [
        "volcano",
        "snowfield",
        "wind_plateau",
        "bog",
        "wasteland",
    ]


def test_the_grassland_has_no_attribute_and_no_material():
    # Grade comes from the grassland, attributes come from the biomes. The two
    # ladders do not mix, so the grassland carries neither of the biome fields.
    assert GRASSLAND.element is None
    assert GRASSLAND.material is None


def test_every_ring_biome_has_its_own_element_and_material():
    elements = [b.element for b in RING_BIOMES]
    materials = [b.material for b in RING_BIOMES]
    assert all(e is not None for e in elements)
    assert all(m is not None for m in materials)
    assert len(set(elements)) == 5
    assert len(set(materials)) == 5


def test_materials_are_real_catalogue_rows():
    for biome in RING_BIOMES:
        assert biome.material is not None
        assert item_kinds.ITEM_KINDS[biome.material.key] is biome.material


def test_element_constants_are_the_ones_used():
    assert {b.element for b in RING_BIOMES} == {
        biomes.FIRE,
        biomes.ICE,
        biomes.WIND,
        biomes.POISON,
        biomes.LIGHTNING,
    }


def test_keys_names_and_colours_are_unique():
    assert len({b.key for b in BIOMES}) == len(BIOMES)
    assert len({b.name for b in BIOMES}) == len(BIOMES)
    assert len({b.color for b in BIOMES}) == len(BIOMES)


def test_lookup_maps_every_biome():
    assert set(BIOME_BY_KEY) == {b.key for b in BIOMES}
    assert BIOME_BY_KEY["grassland"] is GRASSLAND


def test_biomes_are_frozen_and_hashable():
    import dataclasses

    import pytest

    with pytest.raises(dataclasses.FrozenInstanceError):
        GRASSLAND.name = "x"  # type: ignore[misc]
    assert {GRASSLAND: 1}[GRASSLAND] == 1


def test_biome_is_a_dataclass_row():
    assert isinstance(GRASSLAND, Biome)
    assert all(len(b.color) == 3 for b in BIOMES)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_biomes.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'game.world'`

- [ ] **Step 3: 패키지를 만든다**

`src/game/world/__init__.py` — 빈 파일.

`src/game/world/biomes.py`:

```python
"""The catalogue of biomes. Data only -- a frozen row per biome, no behaviour.

Same shape as ``items/item_kinds.py``: the table lives here, the code that acts
on it lives in ``world/map.py``. Adding a biome is adding a row.

``key`` is the stable identifier that goes into save files; ``name`` is what the
player reads. The grassland carries neither an element nor a material on
purpose: grade comes from the grassland and attributes come from the biomes, and
the two ladders never mix.

Boss gimmicks are NOT here. This table says what the ground is, not what guards
it -- the bosses arrive with the temples.
"""

from __future__ import annotations

from dataclasses import dataclass

from game.items.item_kinds import (
    BOG_MOSS,
    FROST_CRYSTAL,
    OBSIDIAN,
    THUNDER_STONE,
    WEATHERED_STONE,
    ItemKind,
)

# Attribute magic families. One per ring biome; the grassland has none.
FIRE = "fire"
ICE = "ice"
WIND = "wind"
POISON = "poison"
LIGHTNING = "lightning"


@dataclass(frozen=True)
class Biome:
    key: str  # stable id, used for saves and comparison
    name: str  # shown to the player
    element: str | None  # the attribute its glyphs grant; None in the grassland
    material: ItemKind | None  # what only this biome yields; None in the grassland
    color: tuple[int, int, int]  # flat fill until real tiles exist


GRASSLAND = Biome("grassland", "초원", None, None, (74, 110, 68))

# Ring order is difficulty order. Volcano first because lava is a visible,
# stationary hazard -- the easiest kind to read. Bog fourth because its stamina
# drain is unfair before cooking and potions exist. Wasteland last because raids
# come in crowds and chaining is the answer to the final gauntlet.
VOLCANO = Biome("volcano", "화산지대", FIRE, OBSIDIAN, (110, 52, 44))
SNOWFIELD = Biome("snowfield", "설원", ICE, FROST_CRYSTAL, (206, 219, 230))
WIND_PLATEAU = Biome("wind_plateau", "바람 고원", WIND, WEATHERED_STONE, (150, 145, 120))
BOG = Biome("bog", "늪지", POISON, BOG_MOSS, (72, 86, 58))
WASTELAND = Biome("wasteland", "황무지", LIGHTNING, THUNDER_STONE, (140, 120, 92))

RING_BIOMES: tuple[Biome, ...] = (VOLCANO, SNOWFIELD, WIND_PLATEAU, BOG, WASTELAND)
BIOMES: tuple[Biome, ...] = (GRASSLAND, *RING_BIOMES)

BIOME_BY_KEY: dict[str, Biome] = {biome.key: biome for biome in BIOMES}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest -q --no-cov && ./.venv/Scripts/python.exe -m ruff check . && ./.venv/Scripts/python.exe -m ruff format --check . && ./.venv/Scripts/python.exe -m mypy`
Expected: 전부 PASS

- [ ] **Step 5: 커밋**

```bash
git add -A src tests
git commit -m "feat(world): add the biome catalogue"
```

---

### Task 2: 원형 맵과 바이옴 판정

좌표를 받아 어느 바이옴인지 답하는 순수 객체. 이게 2단계의 심장이다.

**Files:**
- Create: `src/game/world/map.py`
- Modify: `src/game/config.py`
- Test: `tests/test_world_map.py`

**Interfaces:**
- Consumes: Task 1의 `biomes.GRASSLAND`, `biomes.RING_BIOMES`
- Produces:
  - `config.MAP_RADIUS: Final[float] = 2400.0`, `config.GRASSLAND_RADIUS: Final[float] = 1400.0`, `config.BIOME_COUNT: Final[int] = 5`, `config.VOID_COLOR: Final[tuple[int, int, int]]`
  - `config.WORLD_WIDTH/WORLD_HEIGHT/WORLD_SIZE`가 `MAP_RADIUS`에서 파생된다
  - `game.world.map.WorldMap` (frozen): 필드 `radius: float`, `grassland_radius: float`, `rotation: float`. 프로퍼티 `center -> pygame.Vector2`, `sector_degrees -> float`. 클래스메서드 `create(rng: random.Random) -> WorldMap`. 메서드 `contains(point) -> bool`, `biome_at(point) -> Biome | None`, `distance_fraction(point) -> float`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_world_map.py`를 새로 만든다.

```python
import math
import random

import pygame

from game import config
from game.world import biomes
from game.world.map import WorldMap


def _at(world: WorldMap, degrees: float, dist: float) -> pygame.Vector2:
    """A world point ``dist`` from the centre, at ``degrees`` (0 = +x, y grows down)."""
    a = math.radians(degrees)
    return world.center + pygame.Vector2(math.cos(a), math.sin(a)) * dist


def test_the_centre_sits_at_the_middle_of_the_world_square():
    world = WorldMap()
    assert world.center == pygame.Vector2(config.MAP_RADIUS, config.MAP_RADIUS)
    assert config.WORLD_SIZE == (2 * config.MAP_RADIUS, 2 * config.MAP_RADIUS)


def test_the_grassland_is_about_a_third_of_the_map():
    world = WorldMap()
    ratio = (world.grassland_radius / world.radius) ** 2
    assert 0.28 < ratio < 0.40


def test_contains_is_the_circle_not_the_square():
    world = WorldMap()
    assert world.contains(world.center)
    assert world.contains(_at(world, 0, world.radius - 1))
    assert not world.contains(_at(world, 0, world.radius + 1))
    # a square corner is outside the inscribed circle
    assert not world.contains(pygame.Vector2(0, 0))


def test_the_centre_is_grassland():
    world = WorldMap()
    assert world.biome_at(world.center) is biomes.GRASSLAND
    assert world.biome_at(_at(world, 123, world.grassland_radius - 1)) is biomes.GRASSLAND


def test_outside_the_map_has_no_biome():
    world = WorldMap()
    assert world.biome_at(_at(world, 45, world.radius + 10)) is None


def test_the_ring_is_split_into_five_sectors_in_order():
    world = WorldMap(rotation=0.0)
    mid = (world.grassland_radius + world.radius) / 2
    for i, biome in enumerate(biomes.RING_BIOMES):
        degrees = i * 72 + 36  # the middle of sector i
        assert world.biome_at(_at(world, degrees, mid)) is biome


def test_rotation_turns_the_whole_ring():
    turned = WorldMap(rotation=72.0)
    mid = (turned.grassland_radius + turned.radius) / 2
    # sector 0 now starts at 72 degrees, so its middle is at 108
    assert turned.biome_at(_at(turned, 108, mid)) is biomes.RING_BIOMES[0]
    # and what used to be sector 0's middle now belongs to the last sector
    assert turned.biome_at(_at(turned, 36, mid)) is biomes.RING_BIOMES[-1]


def test_rotation_does_not_change_the_grassland():
    for rotation in (0.0, 37.0, 180.0, 359.0):
        world = WorldMap(rotation=rotation)
        assert world.biome_at(world.center) is biomes.GRASSLAND


def test_every_ring_point_lands_in_some_biome():
    world = WorldMap(rotation=17.0)
    mid = (world.grassland_radius + world.radius) / 2
    seen = {world.biome_at(_at(world, d, mid)) for d in range(0, 360, 3)}
    assert None not in seen
    assert seen == set(biomes.RING_BIOMES)


def test_create_randomises_the_rotation_reproducibly():
    a = WorldMap.create(random.Random(7))
    b = WorldMap.create(random.Random(7))
    c = WorldMap.create(random.Random(8))
    assert a == b  # same seed, same map
    assert a.rotation != c.rotation
    assert 0.0 <= a.rotation < 360.0


def test_distance_fraction_runs_zero_at_the_core_to_one_at_the_edge():
    world = WorldMap()
    assert world.distance_fraction(world.center) == 0.0
    assert world.distance_fraction(_at(world, 0, world.radius)) == 1.0
    assert world.distance_fraction(_at(world, 0, world.radius * 2)) == 1.0  # clamped
    assert world.distance_fraction(_at(world, 0, world.radius / 2)) == 0.5


def test_the_map_is_frozen():
    import dataclasses

    import pytest

    with pytest.raises(dataclasses.FrozenInstanceError):
        WorldMap().rotation = 1.0  # type: ignore[misc]
```

- [ ] **Step 2: 실패를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_world_map.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'game.world.map'`

- [ ] **Step 3: 상수를 넣는다**

`src/game/config.py`의 World 절을

```python
# --- World ------------------------------------------------------------------
WORLD_WIDTH: Final[int] = 2400
WORLD_HEIGHT: Final[int] = 1600
WORLD_SIZE: Final[tuple[int, int]] = (WORLD_WIDTH, WORLD_HEIGHT)
TILE_SIZE: Final[int] = 32  # visual floor rendering only, not a data grid
```

이걸로 바꾼다.

```python
# --- World ------------------------------------------------------------------
# The playable map is a CIRCLE inscribed in a square world box. The box is what
# the camera clamps against; the circle is what the player can stand on, so the
# box corners are void. A central grassland fills about a third of the circle
# and the remaining ring is split into BIOME_COUNT equal sectors.
MAP_RADIUS: Final[float] = 2400.0
GRASSLAND_RADIUS: Final[float] = 1400.0  # (1400/2400)^2 = 0.34 of the area
BIOME_COUNT: Final[int] = 5

WORLD_WIDTH: Final[int] = int(2 * MAP_RADIUS)
WORLD_HEIGHT: Final[int] = int(2 * MAP_RADIUS)
WORLD_SIZE: Final[tuple[int, int]] = (WORLD_WIDTH, WORLD_HEIGHT)
TILE_SIZE: Final[int] = 32  # visual floor rendering only, not a data grid
```

그리고 색 절에 공백 색을 더한다.

```python
VOID_COLOR: Final[tuple[int, int, int]] = (18, 18, 26)  # outside the map circle
```

- [ ] **Step 4: 맵을 구현한다**

`src/game/world/map.py`:

```python
"""The world map: a circle, a central grassland, and a ring split into sectors.

Pure data with pure methods. It holds no pygame surface, mutates nothing, and
takes its randomness as an injected ``random.Random`` -- so a seed reproduces a
map exactly, and every question it answers is testable headlessly.

The biome a point belongs to is computed from its distance and angle, not looked
up in a grid. There is no map file to load and none to ship: ``MAP_RADIUS`` and
``GRASSLAND_RADIUS`` are the whole terrain description.

``rotation`` decides which way the ring faces. Randomising it in ``create``
makes each run's layout different, which is what gives the temple locators a job
-- set it to 0.0 to pin the layout instead. Nothing else changes.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from game import config
from game.world.biomes import GRASSLAND, RING_BIOMES, Biome


@dataclass(frozen=True)
class WorldMap:
    radius: float = config.MAP_RADIUS
    grassland_radius: float = config.GRASSLAND_RADIUS
    rotation: float = 0.0  # degrees; where the first ring sector starts

    @classmethod
    def create(cls, rng: random.Random) -> WorldMap:
        return cls(rotation=rng.uniform(0.0, 360.0))

    @property
    def center(self) -> pygame.Vector2:
        # A fresh vector every call: the map is frozen, and handing out a shared
        # mutable Vector2 would let a caller move the centre of the world.
        return pygame.Vector2(self.radius, self.radius)

    @property
    def sector_degrees(self) -> float:
        return 360.0 / config.BIOME_COUNT

    def contains(self, point: pygame.Vector2) -> bool:
        return self.center.distance_to(point) <= self.radius

    def distance_fraction(self, point: pygame.Vector2) -> float:
        """0.0 at the core, 1.0 at the map edge. Clamped, never above 1."""
        return min(1.0, self.center.distance_to(point) / self.radius)

    def biome_at(self, point: pygame.Vector2) -> Biome | None:
        """The biome under ``point``, or None outside the map circle."""
        offset = point - self.center
        distance = offset.length()
        if distance > self.radius:
            return None
        if distance <= self.grassland_radius:
            return GRASSLAND
        degrees = math.degrees(math.atan2(offset.y, offset.x))
        index = int(((degrees - self.rotation) % 360.0) // self.sector_degrees)
        # A point exactly on 360.0 would index past the end after the modulo's
        # rounding; clamping costs nothing and cannot surprise anyone later.
        return RING_BIOMES[min(index, len(RING_BIOMES) - 1)]
```

- [ ] **Step 5: 통과를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest -q --no-cov && ./.venv/Scripts/python.exe -m ruff check . && ./.venv/Scripts/python.exe -m ruff format --check . && ./.venv/Scripts/python.exe -m mypy`
Expected: 전부 PASS. 기존 테스트도 그대로 통과해야 한다 — 월드가 커졌을 뿐 사각형 경계 코드는 아직 안 건드렸다.

- [ ] **Step 6: 커밋**

```bash
git add -A src tests
git commit -m "feat(world): make the map a circle with a grassland core and a biome ring"
```

---

### Task 3: 원 안으로 이동 제한과 스폰

지금은 플레이어도 골렘도 투사체도 사각형 기준이다. 원 밖으로 나가면 바이옴이 없으므로 나갈 수 없어야 한다.

**Files:**
- Modify: `src/game/systems/physics.py`, `src/game/world/map.py`, `src/game/systems/spawn_common.py`, `src/game/entities/player.py`, `src/game/entities/enemy.py`, `src/game/systems/combat.py`, `src/game/systems/spawner.py`, `src/game/systems/enemy_spawner.py`, `src/game/scenes/play.py`
- Test: `tests/test_physics.py` (신규), `tests/test_world_map.py`, `tests/test_player.py`, `tests/test_enemy.py`, `tests/test_combat.py`, `tests/test_spawner.py`, `tests/test_enemy_spawner.py`

**Interfaces:**
- Consumes: Task 2의 `WorldMap`
- Produces:
  - `physics.clamp_to_circle(pos, radius, center, limit) -> None` — `pos`를 제자리에서 수정
  - `WorldMap.clamp(pos, radius) -> None` — 반지름 `radius`짜리 원이 맵 안에 있도록 `pos`를 제자리에서 수정
  - `WorldMap.random_point(rng, outward=False) -> pygame.Vector2` — 원 안 균일 분포. `outward=True`면 바깥쪽으로 치우친다
  - `Player.update(dt, move_dir, world: WorldMap, dodge_pressed=False) -> None` — 세 번째 인자가 `tuple[int, int]`에서 `WorldMap`으로 바뀐다
  - `Golem.update(dt, target, world: WorldMap) -> None` — 같은 변경
  - `combat.update_projectiles(dt, projectiles, enemies, world: WorldMap)`, `combat.update_enemies(dt, enemies, player, world: WorldMap)`
  - `spawn_common.random_point`는 사라진다 (`WorldMap.random_point`가 대신한다). `MARGIN`도 사라진다 — 원에는 모서리 여백이라는 개념이 없다
  - `Spawner.update(dt, fragments, core, rng, world)`, `EnemySpawner.update(dt, enemies, player_pos, core, rng, world)`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_physics.py`를 새로 만든다.

```python
import pygame

from game.systems.physics import clamp_to_circle

CENTRE = pygame.Vector2(100, 100)


def test_a_point_well_inside_is_left_alone():
    p = pygame.Vector2(110, 100)
    clamp_to_circle(p, 5, CENTRE, 50)
    assert p == pygame.Vector2(110, 100)


def test_a_point_outside_is_pulled_to_the_rim():
    p = pygame.Vector2(200, 100)
    clamp_to_circle(p, 5, CENTRE, 50)
    assert p == pygame.Vector2(145, 100)  # 50 - 5 from the centre


def test_the_body_radius_keeps_the_whole_circle_inside():
    p = pygame.Vector2(100, 148)
    clamp_to_circle(p, 10, CENTRE, 50)
    assert CENTRE.distance_to(p) == 40


def test_a_point_exactly_on_the_centre_is_left_alone():
    p = pygame.Vector2(100, 100)
    clamp_to_circle(p, 5, CENTRE, 50)
    assert p == CENTRE  # no direction to push it in, and none is needed


def test_a_body_bigger_than_the_circle_lands_on_the_centre():
    p = pygame.Vector2(200, 100)
    clamp_to_circle(p, 80, CENTRE, 50)
    assert p == CENTRE
```

`tests/test_world_map.py`에 아래를 덧붙인다.

```python
def test_clamp_keeps_a_body_inside_the_circle():
    world = WorldMap()
    p = _at(world, 30, world.radius * 2)
    world.clamp(p, 14)
    assert world.contains(p)
    assert round(world.center.distance_to(p), 6) == world.radius - 14


def test_random_points_all_land_inside_the_map():
    world = WorldMap()
    rng = random.Random(3)
    points = [world.random_point(rng) for _ in range(500)]
    assert all(world.contains(p) for p in points)
    assert all(world.biome_at(p) is not None for p in points)


def test_random_points_are_reproducible_from_a_seed():
    world = WorldMap()
    a = [world.random_point(random.Random(11)) for _ in range(3)]
    b = [world.random_point(random.Random(11)) for _ in range(3)]
    assert a == b


def test_uniform_random_points_do_not_bunch_at_the_centre():
    # Sampling radius uniformly would put half the points inside 0.5R, which is
    # only a quarter of the area. Area-uniform sampling gives a mean radius of
    # 2R/3, and that is what this pins down.
    world = WorldMap()
    rng = random.Random(5)
    radii = [world.center.distance_to(world.random_point(rng)) for _ in range(4000)]
    mean = sum(radii) / len(radii)
    assert abs(mean / world.radius - 2 / 3) < 0.03


def test_outward_sampling_pushes_points_towards_the_edge():
    # Resources get denser away from the core, so the spawner needs a sampler
    # that is biased outward. Density proportional to radius gives a mean of
    # 3R/4, measurably further out than the flat 2R/3.
    world = WorldMap()
    rng = random.Random(5)
    radii = [
        world.center.distance_to(world.random_point(rng, outward=True)) for _ in range(4000)
    ]
    mean = sum(radii) / len(radii)
    assert abs(mean / world.radius - 3 / 4) < 0.03
```

- [ ] **Step 2: 실패를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_physics.py tests/test_world_map.py -q --no-cov`
Expected: FAIL — `ImportError: cannot import name 'clamp_to_circle'`

- [ ] **Step 3: 물리와 맵 메서드를 구현한다**

`src/game/systems/physics.py` 전체를 이걸로 교체한다.

```python
"""Small movement helpers shared by entities. Pure maths on vectors -- no pygame
display, no entity imports -- so any entity can use it without an import cycle."""

from __future__ import annotations

import pygame


def clamp_to_circle(
    pos: pygame.Vector2,
    radius: float,
    center: pygame.Vector2,
    limit: float,
) -> None:
    """Clamp ``pos`` in place so a body of ``radius`` stays inside the circle.

    A body larger than the circle, or one sitting exactly on the centre, has no
    valid rim to sit on -- both land on the centre, which is the only point that
    is always inside.
    """
    reach = limit - radius
    offset = pos - center
    distance = offset.length()
    if distance <= reach:
        return
    if reach <= 0 or distance == 0:
        pos.update(center)
        return
    pos.update(center + offset * (reach / distance))
```

`clamp_to_bounds`는 사라진다. 원형 맵에서 사각형 제한은 쓰는 곳이 없다.

`src/game/world/map.py`에 아래 두 메서드를 `biome_at` 뒤에 더한다.

```python
    def clamp(self, pos: pygame.Vector2, radius: float = 0.0) -> None:
        """Pull ``pos`` in place so a body of ``radius`` stays on the map."""
        clamp_to_circle(pos, radius, self.center, self.radius)

    def random_point(self, rng: random.Random, outward: bool = False) -> pygame.Vector2:
        """A random point inside the map circle.

        The radius is NOT sampled uniformly: that would crowd the centre, since
        a thin ring far out holds far more area than one near the middle. The
        square root spreads points evenly by area instead.

        ``outward`` swaps the square root for a cube root, which makes density
        grow with distance -- resources are meant to thicken away from the core.
        """
        angle = rng.uniform(0.0, 2 * math.pi)
        spread = rng.random() ** (1 / 3 if outward else 1 / 2)
        distance = self.radius * spread
        return self.center + pygame.Vector2(math.cos(angle), math.sin(angle)) * distance
```

그리고 import에 `from game.systems.physics import clamp_to_circle`를 더한다. `systems/physics.py`는 아무것도 import하지 않으므로 순환 참조가 생기지 않는다.

- [ ] **Step 4: 엔티티와 시스템을 원형으로 옮긴다**

`src/game/entities/player.py`
- `from game.systems.physics import clamp_to_bounds` → `from game.world.map import WorldMap`
- 시그니처 `bounds: tuple[int, int],` → `world: WorldMap,`
- 독스트링 `clamped to bounds` → `clamped to the map circle`
- `clamp_to_bounds(self.pos, self.radius, bounds)` → `world.clamp(self.pos, self.radius)`

`src/game/entities/enemy.py`
- 같은 import 교체
- `def update(self, dt: float, target: pygame.Vector2, bounds: tuple[int, int]) -> None:` → `world: WorldMap`
- `clamp_to_bounds(self.pos, self.radius, bounds)` → `world.clamp(self.pos, self.radius)`

`src/game/systems/combat.py`
- `from game.world.map import WorldMap` 추가
- `_in_bounds` 함수를 통째로 지운다
- `update_projectiles(dt, projectiles, enemies, bounds: tuple[int, int])` → `world: WorldMap`
- 그 안의 `if shot.is_expired or not _in_bounds(shot.pos, bounds):` → `if shot.is_expired or not world.contains(shot.pos):`
- `update_enemies(dt, enemies, player, bounds: tuple[int, int])` → `world: WorldMap`
- 그 안의 `enemy.update(dt, player.pos, bounds)` → `enemy.update(dt, player.pos, world)`

`src/game/systems/spawn_common.py`
- `random_point`와 `MARGIN`을 지운다. `pygame`과 `config` import도 같이 지운다 (`TimedSpawner`와 `SPAWN_ATTEMPTS`만 남는다)
- 모듈 독스트링에서 "random spawnable point" 문장을 빼고, 남은 책임만 적는다

`src/game/systems/spawner.py`
- `from game.systems.spawn_common import SPAWN_ATTEMPTS, TimedSpawner, random_point` → `from game.systems.spawn_common import SPAWN_ATTEMPTS, TimedSpawner`
- `from game.world.map import WorldMap` 추가
- `update(self, dt, fragments, core, rng)` 끝에 `world: WorldMap` 인자를 더하고 `self._find_spot(fragments, core, rng, world)`로 넘긴다
- `_find_spot(self, fragments, core, rng)`에 `world: WorldMap`를 더하고 `point = random_point(rng)` → `point = world.random_point(rng, outward=True)`

`src/game/systems/enemy_spawner.py`
- 같은 방식으로 `world: WorldMap`를 `update`와 `_find_spot`에 더한다
- `point = random_point(rng)` → `point = world.random_point(rng)` (골렘은 바깥으로 치우칠 이유가 없다)

`src/game/scenes/play.py`
- `from game.world.map import WorldMap` 추가
- `__init__`에서 `self.world = WorldMap.create(self.rng)` — 단 `self.rng`가 먼저 만들어져야 하므로 `self.rng = random.Random(1234)` 줄을 `self.world` 위로 옮긴다
- `center = pygame.Vector2(...)` 두 줄을 `center = self.world.center`로 바꾼다
- `self.player.update(dt, self._move_dir(), config.WORLD_SIZE, dodge)` → `self.world` 를 넘긴다
- `combat.update_projectiles(dt, self.projectiles, self.enemies, config.WORLD_SIZE)` → `self.world`
- `combat.update_enemies(dt, self.enemies, self.player, config.WORLD_SIZE)` → `self.world`
- `self.spawner.update(dt, self.fragments, self.core, self.rng)` → 끝에 `self.world` 추가
- `self.enemy_spawner.update(dt, self.enemies, self.player.pos, self.core, self.rng)` → 끝에 `self.world` 추가

- [ ] **Step 5: 테스트를 따라간다**

**주의: 기존 테스트 좌표가 대부분 맵 밖이다.** 월드 중심이 `(2400, 2400)`이고 반지름이 2400이므로, `(500, 500)`은 중심에서 2687 떨어진 **바깥**이다. 그냥 `WorldMap()`만 끼워 넣으면 `clamp`가 좌표를 끌어당겨 테스트가 전부 깨진다. 좌표를 중심 근처로 옮겨야 한다.

`tests/test_player.py` 전체를 이걸로 교체한다.

```python
import pygame
import pytest

from game import config
from game.entities.player import Player
from game.world.map import WorldMap

WORLD = WorldMap()
CENTRE = WORLD.center


def _player(offset=(0, 0)) -> Player:
    return Player(pos=CENTRE + pygame.Vector2(offset))


def test_moves_in_direction():
    p = _player()
    start = pygame.Vector2(p.pos)
    p.update(1.0, pygame.Vector2(1, 0), WORLD)
    assert p.pos.x == start.x + config.PLAYER_SPEED
    assert p.pos.y == start.y


def test_diagonal_is_normalized():
    p = _player()
    start = pygame.Vector2(p.pos)
    p.update(1.0, pygame.Vector2(1, 1), WORLD)
    assert p.pos.distance_to(start) == pytest.approx(config.PLAYER_SPEED)


def test_zero_direction_does_not_move():
    p = _player((300, -200))
    start = pygame.Vector2(p.pos)
    p.update(1.0, pygame.Vector2(0, 0), WORLD)
    assert p.pos == start


def test_clamped_to_the_map_rim():
    # Standing just inside the rim and walking straight out: the body's radius
    # keeps the whole circle on the map, so it stops short of the edge.
    p = Player(pos=CENTRE + pygame.Vector2(WORLD.radius - 1, 0))
    p.update(1.0, pygame.Vector2(1, 0), WORLD)
    assert CENTRE.distance_to(p.pos) == pytest.approx(WORLD.radius - config.PLAYER_RADIUS)
    assert WORLD.contains(p.pos)


def test_the_square_corner_is_off_the_map():
    # The world box's corner is outside the inscribed circle, so a player put
    # there is pulled back onto the rim rather than left standing in the void.
    p = Player(pos=pygame.Vector2(0, 0))
    p.update(1.0, pygame.Vector2(0, 0), WORLD)
    assert WORLD.contains(p.pos)


def test_dodge_grants_iframes_and_cooldown():
    p = _player()
    assert p.invulnerable is False
    p.update(0.0, pygame.Vector2(0, 0), WORLD, dodge_pressed=True)
    assert p.invulnerable is True
    assert p.dodge_cooldown_timer == config.DODGE_COOLDOWN


def test_dodge_iframes_expire():
    p = _player()
    p.update(0.0, pygame.Vector2(0, 0), WORLD, dodge_pressed=True)
    p.update(config.DODGE_IFRAMES, pygame.Vector2(0, 0), WORLD)
    assert p.invulnerable is False


def test_dodge_dashes_faster_when_moving():
    normal = _player()
    normal.update(config.DODGE_DURATION, pygame.Vector2(1, 0), WORLD)
    dashed = _player()
    dashed.update(config.DODGE_DURATION, pygame.Vector2(1, 0), WORLD, dodge_pressed=True)
    assert dashed.pos.x > normal.pos.x


def test_dodge_blocked_during_cooldown():
    p = _player()
    p.update(0.0, pygame.Vector2(0, 0), WORLD, dodge_pressed=True)
    p.update(config.DODGE_IFRAMES, pygame.Vector2(0, 0), WORLD)  # iframes end, still cooling
    assert p.invulnerable is False
    p.update(0.0, pygame.Vector2(0, 0), WORLD, dodge_pressed=True)  # re-press mid-cooldown
    assert p.invulnerable is False  # blocked
```

`tests/test_enemy.py`: 상단에 `from game.world.map import WorldMap`를 더하고, `WORLD = WorldMap()` / `CENTRE = WORLD.center`를 둔다. `Golem(pos=pygame.Vector2(50, 50))`을 `Golem(pos=CENTRE)`로, 목표점 `pygame.Vector2(150, 50)`을 `CENTRE + pygame.Vector2(100, 0)`으로 옮기고, 세 번째 인자 `(2400, 1600)`을 `WORLD`로 바꾼다. 이동 검증은 절대 좌표 대신 시작점 기준으로 비교한다.

`tests/test_combat.py`: 상단에 `WORLD = WorldMap()` / `CENTRE = WORLD.center`. `Player(pos=pygame.Vector2(500, 500))`과 `Golem(pos=pygame.Vector2(500, 500))`을 전부 `CENTRE` 기준으로 옮기고, `(2400, 1600)` 인자를 `WORLD`로 바꾼다. `test_distant_enemy_deals_no_damage`의 `(0, 0)` / `(2000, 1500)`은 **둘 다 맵 안**이면서 서로 먼 두 점으로 바꾼다 — 예: `CENTRE` 와 `CENTRE + (1800, 0)`.

`tests/test_spawner.py`: `CORE`는 이미 `(WORLD_WIDTH/2, WORLD_HEIGHT/2)` = 새 월드 중심이라 그대로 맞다. 상단에 `from game.world.map import WorldMap` / `WORLD = WorldMap()`를 더하고, `sp.update(...)` 호출 다섯 곳 끝에 `WORLD`를 더한다.

`tests/test_enemy_spawner.py`: 같은 방식으로 `WORLD`를 더한다. 단 `test_spawn_avoids_core_sync_zone_and_player`의 `player_pos = pygame.Vector2(100, 100)`은 맵 **밖**이라 "300px 이상 떨어져 있다"가 저절로 참이 되어 테스트가 무의미해진다. 맵 안으로 옮긴다.

```python
def test_spawn_avoids_core_sync_zone_and_player():
    spawner = EnemySpawner()
    enemies: list[Golem] = []
    core = _core()
    player_pos = core.pos + pygame.Vector2(600, 0)  # inside the map, not on the core
    v = spawner.update(config.GOLEM_SPAWN_INTERVAL, enemies, player_pos, core, random.Random(7), WORLD)
    assert v is not None
    assert core.pos.distance_to(v.pos) >= core.sync_radius
    assert player_pos.distance_to(v.pos) >= 300
```

- [ ] **Step 6: 통과를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest -q --no-cov && ./.venv/Scripts/python.exe -m ruff check . && ./.venv/Scripts/python.exe -m ruff format --check . && ./.venv/Scripts/python.exe -m mypy`
Expected: 전부 PASS.
잔재 확인: `grep -rn "clamp_to_bounds\|_in_bounds\|WORLD_SIZE" --include='*.py' src tests` → `config.py`의 정의와 `camera` 관련만 남는다

- [ ] **Step 7: 커밋**

```bash
git add -A src tests
git commit -m "feat(world): confine movement, projectiles and spawns to the map circle"
```

---

### Task 4: 사원 자리 5개

바이옴마다 하나씩, 바이옴 안 랜덤 위치. 안쪽/바깥쪽 끝과 섹터 경계는 피한다.

**Files:**
- Modify: `src/game/config.py`, `src/game/world/map.py`
- Test: `tests/test_world_map.py`

**Interfaces:**
- Consumes: Task 2의 `WorldMap`, Task 1의 `RING_BIOMES`
- Produces:
  - `config.TEMPLE_BAND_INNER: Final[float] = 1600.0`, `config.TEMPLE_BAND_OUTER: Final[float] = 2200.0`, `config.TEMPLE_ANGLE_INSET: Final[float] = 12.0`
  - `WorldMap.temple_sites(rng: random.Random) -> tuple[pygame.Vector2, ...]` — `RING_BIOMES`와 같은 순서로 5개

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_world_map.py`에 덧붙인다.

```python
def test_there_is_one_temple_per_biome_in_ring_order():
    world = WorldMap(rotation=41.0)
    sites = world.temple_sites(random.Random(2))
    assert len(sites) == len(biomes.RING_BIOMES)
    for site, biome in zip(sites, biomes.RING_BIOMES, strict=True):
        assert world.biome_at(site) is biome


def test_temples_avoid_the_inner_and_outer_edges_of_the_ring():
    # The spec asks for margin at both ends so a temple never looks like it is
    # falling off the map or leaking into the grassland.
    world = WorldMap()
    for seed in range(20):
        for site in world.temple_sites(random.Random(seed)):
            distance = world.center.distance_to(site)
            assert config.TEMPLE_BAND_INNER <= distance <= config.TEMPLE_BAND_OUTER
            assert world.grassland_radius < distance < world.radius


def test_temples_are_reproducible_from_a_seed():
    world = WorldMap(rotation=41.0)
    assert world.temple_sites(random.Random(9)) == world.temple_sites(random.Random(9))


def test_different_seeds_move_the_temples():
    world = WorldMap(rotation=41.0)
    assert world.temple_sites(random.Random(1)) != world.temple_sites(random.Random(2))


def test_temples_stay_clear_of_the_sector_seams():
    # A temple sitting on a boundary reads as belonging to the neighbour, so it
    # is inset from both edges of its own sector.
    world = WorldMap(rotation=0.0)
    inset = config.TEMPLE_ANGLE_INSET
    for seed in range(20):
        for i, site in enumerate(world.temple_sites(random.Random(seed))):
            offset = site - world.center
            degrees = math.degrees(math.atan2(offset.y, offset.x)) % 360.0
            within = (degrees - i * world.sector_degrees) % 360.0
            assert inset <= within <= world.sector_degrees - inset
```

- [ ] **Step 2: 실패를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_world_map.py -q --no-cov -k temple`
Expected: FAIL — `AttributeError: 'WorldMap' object has no attribute 'temple_sites'`

- [ ] **Step 3: 구현한다**

`src/game/config.py`의 World 절 끝에 더한다.

```python
# Where a boss temple may stand inside its sector. The radial band keeps it off
# both edges of the ring; the angular inset keeps it off the seams, where it
# would read as belonging to the neighbouring biome.
TEMPLE_BAND_INNER: Final[float] = 1600.0
TEMPLE_BAND_OUTER: Final[float] = 2200.0
TEMPLE_ANGLE_INSET: Final[float] = 12.0  # degrees trimmed from each sector edge
```

`src/game/world/map.py`에 더한다.

```python
    def temple_sites(self, rng: random.Random) -> tuple[pygame.Vector2, ...]:
        """One boss temple per ring biome, in ``RING_BIOMES`` order.

        Placed randomly inside its own sector but kept off all four edges: the
        radial band leaves margin at the ring's inner and outer rims, and the
        angular inset leaves margin at the seams with the neighbouring biomes.
        """
        sites: list[pygame.Vector2] = []
        for index in range(len(RING_BIOMES)):
            start = self.rotation + index * self.sector_degrees
            degrees = rng.uniform(
                start + config.TEMPLE_ANGLE_INSET,
                start + self.sector_degrees - config.TEMPLE_ANGLE_INSET,
            )
            distance = rng.uniform(config.TEMPLE_BAND_INNER, config.TEMPLE_BAND_OUTER)
            angle = math.radians(degrees)
            sites.append(
                self.center + pygame.Vector2(math.cos(angle), math.sin(angle)) * distance
            )
        return tuple(sites)
```

- [ ] **Step 4: 통과를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest -q --no-cov && ./.venv/Scripts/python.exe -m ruff check . && ./.venv/Scripts/python.exe -m ruff format --check . && ./.venv/Scripts/python.exe -m mypy`
Expected: 전부 PASS

띠가 링 안에 들어 있는지도 눈으로 확인한다: `GRASSLAND_RADIUS(1400) < TEMPLE_BAND_INNER(1600)` 이고 `TEMPLE_BAND_OUTER(2200) < MAP_RADIUS(2400)`.

- [ ] **Step 5: 커밋**

```bash
git add -A src tests
git commit -m "feat(world): place one boss temple site per biome, clear of every edge"
```

---

### Task 5: 거리에 따른 자원 분포

코어에서 멀어질수록 좋은 광물이 나온다. 아연은 초원 바깥쪽에만 있다.

**Files:**
- Create: `src/game/world/resources.py`
- Modify: `src/game/systems/spawner.py`
- Test: `tests/test_world_resources.py` (신규), `tests/test_spawner.py`

**Interfaces:**
- Consumes: Task 2의 `WorldMap.distance_fraction`, 1단계의 `item_kinds`
- Produces: `game.world.resources.ore_at(fraction: float, rng: random.Random) -> ItemKind` — `fraction`은 0.0(코어)~1.0(맵 끝)
- `Spawner`가 새 파편에 `kind`를 정해서 넣는다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_world_resources.py`를 새로 만든다.

```python
import random

from game.items.item_kinds import (
    COPPER_ORE,
    GOLD_ORE,
    IRON_ORE,
    STONE,
    ZINC_ORE,
)
from game.world.resources import ore_at


def _draw(fraction: float, n: int = 3000, seed: int = 1) -> dict:
    rng = random.Random(seed)
    counts: dict = {}
    for _ in range(n):
        kind = ore_at(fraction, rng)
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def test_it_always_returns_a_real_ore():
    rng = random.Random(0)
    allowed = {STONE, COPPER_ORE, IRON_ORE, GOLD_ORE, ZINC_ORE}
    for step in range(21):
        assert ore_at(step / 20, rng) in allowed


def test_the_inner_grassland_is_mostly_stone_and_copper():
    counts = _draw(0.1)
    assert set(counts) <= {STONE, COPPER_ORE}
    assert counts[STONE] > counts[COPPER_ORE]


def test_gold_does_not_appear_in_the_grassland():
    for fraction in (0.1, 0.3, 0.5):
        assert GOLD_ORE not in _draw(fraction)


def test_zinc_appears_only_in_the_outer_grassland():
    # Zinc is smelting-only and deliberately awkward: brass costs the trip out
    # to the grassland's rim, not a deeper mine.
    assert ZINC_ORE not in _draw(0.1)
    assert ZINC_ORE in _draw(0.5)
    assert ZINC_ORE not in _draw(0.9)


def test_the_outer_ring_favours_the_high_tiers():
    counts = _draw(0.95)
    assert counts[GOLD_ORE] > counts[STONE]
    assert counts[IRON_ORE] > counts[STONE]


def test_better_ore_gets_likelier_further_out():
    near = _draw(0.3)
    far = _draw(0.95)
    assert far.get(IRON_ORE, 0) > near.get(IRON_ORE, 0)
    assert far.get(STONE, 0) < near.get(STONE, 0)


def test_it_is_reproducible_from_a_seed():
    a = [ore_at(0.8, rng) for rng in [random.Random(4)] for _ in range(20)]
    b = [ore_at(0.8, rng) for rng in [random.Random(4)] for _ in range(20)]
    assert a == b
```

`tests/test_spawner.py`에 덧붙인다.

```python
def test_spawned_nodes_carry_an_ore_kind():
    from game.world.resources import ore_at  # noqa: F401  (documents the source)

    fragments = []
    spawner = Spawner()
    world = WorldMap()
    rng = random.Random(21)
    for _ in range(30):
        spawner.update(config.SPAWN_INTERVAL, fragments, _core(), rng, world)
    assert fragments, "the spawner should have produced something in 30 attempts"
    assert all(f.kind is not None for f in fragments)
    # Not every node is a core shard any more -- the ore table decides.
    assert len({f.kind for f in fragments}) > 1
```

`_core()` 헬퍼와 import는 그 파일에 이미 있는 것을 쓴다. 없으면 `tests/test_enemy_spawner.py`의 것과 같은 모양으로 만든다.

- [ ] **Step 2: 실패를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_world_resources.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'game.world.resources'`

- [ ] **Step 3: 구현한다**

`src/game/world/resources.py`:

```python
"""What a mined node yields, as a function of how far out it is.

Pure. The distance fraction comes from ``WorldMap.distance_fraction`` -- 0.0 at
the core, 1.0 at the map edge -- and the randomness is injected, so a seed
reproduces a world's ore exactly.

The bands are keyed to the map's own radii rather than to bare numbers: the
grassland's rim moves if ``GRASSLAND_RADIUS`` moves, and zinc moves with it.
"""

from __future__ import annotations

import random

from game import config
from game.items.item_kinds import COPPER_ORE, GOLD_ORE, IRON_ORE, STONE, ZINC_ORE, ItemKind

_GRASSLAND_EDGE = config.GRASSLAND_RADIUS / config.MAP_RADIUS
_INNER_GRASSLAND = _GRASSLAND_EDGE / 2
_INNER_RING = _GRASSLAND_EDGE + (1.0 - _GRASSLAND_EDGE) / 2

# (upper bound of the band, ((kind, weight), ...)). Read top to bottom; the first
# band whose bound the fraction falls under wins.
#
# Gold is a ring tier and never shows up in the grassland. Zinc is the opposite:
# it lives ONLY on the grassland's rim, so brass costs a trip to the edge of the
# safe land rather than a trip into a biome.
_BANDS: tuple[tuple[float, tuple[tuple[ItemKind, int], ...]], ...] = (
    (_INNER_GRASSLAND, ((STONE, 70), (COPPER_ORE, 30))),
    (_GRASSLAND_EDGE, ((STONE, 40), (COPPER_ORE, 35), (IRON_ORE, 20), (ZINC_ORE, 5))),
    (_INNER_RING, ((STONE, 20), (COPPER_ORE, 25), (IRON_ORE, 35), (GOLD_ORE, 20))),
    (1.01, ((STONE, 10), (COPPER_ORE, 15), (IRON_ORE, 35), (GOLD_ORE, 40))),
)


def ore_at(fraction: float, rng: random.Random) -> ItemKind:
    """What a node at ``fraction`` of the way to the map edge yields."""
    for bound, table in _BANDS:
        if fraction < bound:
            kinds = [kind for kind, _ in table]
            weights = [weight for _, weight in table]
            return rng.choices(kinds, weights=weights, k=1)[0]
    raise AssertionError(f"no ore band covers {fraction}")  # pragma: no cover
```

`src/game/systems/spawner.py`의 `update`에서 파편을 만드는 줄을 바꾼다.

```python
        fragment = Fragment(pos=spot, kind=ore_at(world.distance_fraction(spot), rng))
```

그리고 `from game.world.resources import ore_at`를 import에 더한다.

- [ ] **Step 4: 통과를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest -q --no-cov && ./.venv/Scripts/python.exe -m ruff check . && ./.venv/Scripts/python.exe -m ruff format --check . && ./.venv/Scripts/python.exe -m mypy`
Expected: 전부 PASS

- [ ] **Step 5: 커밋**

```bash
git add -A src tests
git commit -m "feat(world): make ore quality follow distance from the core"
```

---

### Task 6: 씬 배선과 단색 렌더링

바이옴을 눈으로 확인할 수 있게 칠한다. **타일은 안 쓴다** — 바이옴이 각도 부채꼴이라 다각형 5개로 정확하게 칠할 수 있고, 프레임당 그리기 호출이 7번이면 끝난다. 지금 체커보드는 프레임당 500번 넘게 그린다.

타일 에셋이 생기면 `_draw_world`만 갈아끼우면 된다. `biome_at`은 그대로 남는다.

**Files:**
- Modify: `src/game/scenes/play.py`, `CLAUDE.md`
- Test: `tests/test_play_scene.py`

**Interfaces:**
- Consumes: Task 2~5 전부
- Produces: `PlayScene.world: WorldMap`, `PlayScene.temple_sites: tuple[pygame.Vector2, ...]`. `_draw_floor`는 `_draw_world`로 대체된다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_play_scene.py`에 덧붙인다. 픽셀을 보는 테스트라 `surface` 픽스처를 쓴다.

```python
def test_the_scene_owns_a_map_and_five_temple_sites():
    scene = PlayScene()
    assert scene.world.contains(scene.player.pos)
    assert len(scene.temple_sites) == 5
    assert all(scene.world.contains(site) for site in scene.temple_sites)


def test_the_core_stands_at_the_centre_of_the_map():
    scene = PlayScene()
    assert scene.core.pos == scene.world.center


def test_the_centre_of_the_view_is_painted_grassland():
    import pygame

    from game.world import biomes

    scene = PlayScene()
    surface = pygame.Surface(config.SCREEN_SIZE)
    scene.camera.center_on(scene.world.center)
    scene.draw(surface)
    # The camera is centred on the core, so the middle of the screen is the
    # middle of the grassland -- unless something is drawn on top of it, which
    # the core itself is, so sample a little to the side of it.
    probe = (config.SCREEN_WIDTH // 2 + int(config.CORE_RADIUS) + 20, config.SCREEN_HEIGHT // 2)
    assert surface.get_at(probe)[:3] == biomes.GRASSLAND.color


def test_outside_the_map_is_painted_void():
    import pygame

    scene = PlayScene()
    surface = pygame.Surface(config.SCREEN_SIZE)
    # Park the camera on the world box's top-left corner, which is outside the
    # inscribed circle.
    scene.camera.mode = "free"
    scene.camera.offset = pygame.Vector2(0, 0)
    scene.draw(surface)
    assert surface.get_at((2, 2))[:3] == config.VOID_COLOR
```

- [ ] **Step 2: 실패를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_play_scene.py -q --no-cov`
Expected: FAIL — `AttributeError: 'PlayScene' object has no attribute 'temple_sites'`

- [ ] **Step 3: 씬을 배선한다**

`src/game/scenes/play.py`의 `__init__` 앞부분을 이렇게 만든다. `rng`가 맵보다 먼저 있어야 한다.

```python
        self.rng = random.Random(1234)
        self.world = WorldMap.create(self.rng)
        self.temple_sites = self.world.temple_sites(self.rng)
        center = self.world.center
        self.core = Core(pos=pygame.Vector2(center))
        self.player = Player(pos=pygame.Vector2(center))
```

그리고 아래쪽에 있던 `self.rng = random.Random(1234)` 줄을 지운다 (위로 옮겼으므로).

import에 `import math`와 `from game.world import biomes`, `from game.world.map import WorldMap`를 더한다.

- [ ] **Step 4: 렌더링을 바꾼다**

`_draw_floor` 메서드 전체를 지우고 `_draw_world`로 대체한다.

```python
    def _draw_world(self, surface: pygame.Surface) -> None:
        """Paint the map: void, then one wedge per ring biome, then the grassland.

        Flat colours until real tiles exist. Wedges rather than tiles because
        the biomes ARE angular sectors -- five polygons draw them exactly, with
        no stair-stepping and no per-tile biome lookup every frame.
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
        pygame.draw.circle(
            surface, biomes.GRASSLAND.color, center, self.world.grassland_radius
        )

    def _draw_temples(self, surface: pygame.Surface) -> None:
        """Placeholder markers so the five sites are visible before temples exist."""
        for site in self.temple_sites:
            pygame.draw.circle(surface, config.WHITE, self.camera.world_to_screen(site), 9, 3)
```

`draw`에서 `self._draw_floor(surface)`를 `self._draw_world(surface)`로 바꾸고, 파편을 그리기 직전에 `self._draw_temples(surface)`를 넣는다. `surface.fill(config.BACKGROUND)` 줄은 지운다 — `_draw_world`가 이미 채운다.

- [ ] **Step 5: CLAUDE.md의 표를 고친다**

"Where things go" 표의 `Cross-entity systems` 행 아래에 더한다.

```markdown
| Terrain: biomes, the map circle, resource distribution | `game/world/*.py` |
```

- [ ] **Step 6: 통과를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest -q && ./.venv/Scripts/python.exe -m ruff check . && ./.venv/Scripts/python.exe -m ruff format --check . && ./.venv/Scripts/python.exe -m mypy`
Expected: 전부 PASS.
잔재 확인: `grep -rn "_draw_floor\|TILE_SIZE\|FLOOR_A\|FLOOR_B" --include='*.py' src tests` → 결과 없음. 남아 있으면 `config.py`에서 `TILE_SIZE`, `FLOOR_A`, `FLOOR_B`를 지운다 (체커보드와 함께 죽었다).

눈으로 확인한다:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy ./.venv/Scripts/python.exe -c "
import pygame; pygame.init()
from game.scenes.play import PlayScene
from game import config
s = PlayScene()
for _ in range(600): s.update(config.FIXED_DT)
print('rotation :', round(s.world.rotation, 1))
print('temples  :', [s.world.biome_at(t).name for t in s.temple_sites])
print('nodes    :', sorted({f.kind.name for f in s.fragments}))
pygame.quit()"
```

- [ ] **Step 7: 커밋**

```bash
git add -A src tests CLAUDE.md
git commit -m "feat(world): paint the biomes and mark the temple sites"
```

---

## 이 계획이 끝나면

맵이 원이고, 좌표를 넣으면 어느 바이옴인지 답하고, 사원 자리 5개가 정해지고, 코어에서 멀수록 좋은 광물이 나온다. 화면에는 바이옴이 단색으로 칠해지고 사원 자리에 표식이 찍힌다.

지형 효과(용암 데미지·늪 감속·절벽)와 타일 에셋은 없다. 결계·낮밤·습격도 없다 — 3단계다.

**타일이 들어올 자리:** `_draw_world` 하나. `biome_at`, `distance_fraction`, `temple_sites`는 그대로 남는다.
