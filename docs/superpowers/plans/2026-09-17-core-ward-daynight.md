# 3단계: 코어·결계·낮밤 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 맵을 실제 축척으로 키우고, 코어 파편을 모아 점화하는 시작을 만들고, 코어 레벨에 따라 넓어지는 결계와 그 안에서만 되는 가속 회복, 그리고 낮/밤 주기를 만든다.

**Architecture:** 시계(`systems/daynight.py`)와 회복(`systems/survival.py`)은 순수 `update(dt, ...)`다. 결계는 코어의 상태이지 맵의 상태가 아니므로 `entities/core.py`가 갖는다 — 맵은 지형이고 결계는 플레이어가 키우는 것이라서다. 렌더링은 `scenes/play.py`에만 있다.

**Tech Stack:** pygame-ce, Python >= 3.10, pytest + pytest-cov, ruff, mypy (strict)

**Spec:** `docs/superpowers/specs/2026-08-29-world-rebuild-concept-design.md`

**선행:** 1단계(`2026-09-17-concept-constants-rewrite.md`), 2단계(`2026-09-17-map-and-biomes.md`) — 둘 다 완료

## Global Constraints

- **로직은 순수 `update(dt, ...)`, 렌더링은 `draw(surface)`.** `pygame.display` / 이벤트 펌프 / `pygame.quit`는 `core/app.py`에만.
- **`config.py`는 pygame을 import하지 않는다.** `math`는 괜찮다.
- **고정 타임스텝** `FIXED_DT = 1/60`. 벽시계를 읽지 않는다 — 낮밤도 누적된 `dt`로만 굴러간다.
- **난수는 주입한다** (`random.Random`).
- **TDD**: 실패하는 테스트 → 최소 구현 → 리팩터.
- **명령어**: `./.venv/Scripts/python.exe -m pytest` · `-m ruff check . && -m ruff format --check .` · `-m mypy`
- 각 작업의 마지막 단계는 커밋이다.

## 정한 수치와 그 근거

```
기본 속도       200 px/s     (사용자 지정)
초원 반지름     36,000       코어 -> 경계 정확히 3분
맵 반지름       62,400       초원이 넓이의 1/3 (스펙 유지)
낮 / 밤        300s / 180s   하루 8분
코어 레벨       1 ~ 50
레벨 캡         10/20/30/40/50   보스 하나가 캡 하나를 연다 (5마리 -> 최종 강화)
결계 반경       1,000 -> 11,384  매 레벨 +5.09%
결계 최대 넓이  초원의 1/10      (36,000 / sqrt(10) = 11,384)
점화 파편       5개
```

결계 반경이 **비율로** 자라는 이유: 절대값으로 자라면 초반 한 레벨이 눈에 안 보이고 후반엔 과하다. 매 레벨 같은 비율이면 어느 구간에서든 강화가 같은 무게로 느껴진다.

## 축척이 바꾸는 것 — 놓치면 깨지는 곳

맵 넓이가 **676배**가 된다. 절대 좌표로 박아둔 상수가 전부 틀어진다.

- **사원 띠** `TEMPLE_BAND_INNER/OUTER = 1600/2200`은 새 축척에서 **초원 한복판**이다. 링 두께의 비율로 바꾼다.
- **광맥 밀도** `SPAWN_MAX = 30`은 맵 전체에 30개라는 뜻이라 사실상 아무것도 없다. 스폰을 **플레이어 주변으로** 한정한다.
- **골렘 스폰의 `_MIN_PLAYER_DIST = 300`**도 새 축척에선 코앞이다.

## 범위 밖 (의도적으로 안 함)

- **습격** — 6단계. 결계는 골렘을 항상 막는다. "습격 밤에는 뚫린다"는 예외가 6단계에 붙는다.
- **야생동물** — 6단계. 밤의 위협은 지금 골렘 스포너를 그대로 쓴다.
- **건축(제작대·용광로 배치)** — 5단계. 결계는 아직 "지을 공간"을 제공하지 않는다.
- **거리별 광맥 밀도** — 5단계. 여기서는 플레이어 주변 스폰만 붙인다.
- **스테미나·달리기** — 5단계.

## File Structure

| 파일 | 책임 |
|---|---|
| `src/game/config.py` | 축척·하루·레벨·결계·회복 상수 |
| `src/game/world/map.py` | 사원 띠를 링 비율로 |
| `src/game/systems/daynight.py` | **신규** 하루 시계. 순수 |
| `src/game/systems/survival.py` | **신규** 결계 안 가속 회복. 순수 |
| `src/game/entities/core.py` | 레벨·캡·결계 반경·점화 |
| `src/game/entities/player.py` | `ward_time` 누적 필드 |
| `src/game/systems/combat.py` | 골렘이 결계에 못 들어온다 |
| `src/game/systems/spawner.py`, `enemy_spawner.py` | 플레이어 주변 스폰 |
| `src/game/scenes/play.py` | 배선, 점화 입력, 밤·결계 렌더링 |

---

### Task 1: 세계의 축척

숫자를 키우고, 축척과 함께 깨지는 절대 좌표 상수들을 비율로 바꾼다.

**Files:**
- Modify: `src/game/config.py`, `src/game/world/map.py`, `src/game/systems/spawner.py`, `src/game/systems/enemy_spawner.py`
- Test: `tests/test_config.py`, `tests/test_world_map.py`, `tests/test_spawner.py`, `tests/test_enemy_spawner.py`

**Interfaces:**
- Produces:
  - `config.PLAYER_SPEED = 200.0`, `config.MAP_RADIUS = 62_400.0`, `config.GRASSLAND_RADIUS = 36_000.0`
  - `config.TEMPLE_BAND_INNER_FRAC = 0.20`, `config.TEMPLE_BAND_OUTER_FRAC = 0.80` — 링 두께에 대한 비율. `TEMPLE_BAND_INNER/OUTER`는 사라진다
  - `config.SPAWN_RADIUS = 2_000.0` — 플레이어 주변 이 안에만 스폰한다
  - `WorldMap.ring_width` 프로퍼티
  - `Spawner.update` / `EnemySpawner.update`는 `player_pos` 주변에서만 자리를 찾는다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_config.py`에 더한다.

```python
def test_the_map_is_sized_for_a_three_minute_walk_to_the_biomes():
    # The grassland's rim is exactly three minutes from the core at base speed.
    # Everything else about the map's size follows from that one number.
    assert config.GRASSLAND_RADIUS / config.PLAYER_SPEED == 180.0


def test_the_grassland_is_a_third_of_the_map():
    assert 0.30 < (config.GRASSLAND_RADIUS / config.MAP_RADIUS) ** 2 < 0.36


def test_the_temple_band_is_a_fraction_of_the_ring_not_an_absolute_radius():
    # Absolute radii silently land in the wrong place when the map is rescaled.
    assert not hasattr(config, "TEMPLE_BAND_INNER")
    assert not hasattr(config, "TEMPLE_BAND_OUTER")
    assert 0.0 < config.TEMPLE_BAND_INNER_FRAC < config.TEMPLE_BAND_OUTER_FRAC < 1.0
```

`tests/test_world_map.py`의 `test_temples_avoid_the_inner_and_outer_edges_of_the_ring`을 비율 기준으로 고친다.

```python
def test_temples_avoid_the_inner_and_outer_edges_of_the_ring():
    # The spec asks for margin at both ends so a temple never looks like it is
    # falling off the map or leaking into the grassland.
    world = WorldMap()
    inner = world.grassland_radius + config.TEMPLE_BAND_INNER_FRAC * world.ring_width
    outer = world.grassland_radius + config.TEMPLE_BAND_OUTER_FRAC * world.ring_width
    for seed in range(20):
        for site in world.temple_sites(random.Random(seed)):
            distance = world.center.distance_to(site)
            assert inner <= distance <= outer
            assert world.grassland_radius < distance < world.radius


def test_the_ring_width_is_what_is_left_outside_the_grassland():
    world = WorldMap()
    assert world.ring_width == world.radius - world.grassland_radius
```

`tests/test_spawner.py`에 더한다.

```python
def test_nodes_spawn_within_reach_of_the_player():
    # The map is 676x bigger than it was. Scattering a fixed handful of nodes
    # over all of it would leave nothing to find, so spawns follow the player.
    fragments = []
    spawner = Spawner()
    rng = random.Random(3)
    player_pos = CORE.pos + pygame.Vector2(20_000, 0)
    for _ in range(30):
        spawner.update(config.SPAWN_INTERVAL, fragments, CORE, rng, WORLD, player_pos)
    assert fragments
    assert all(player_pos.distance_to(f.pos) <= config.SPAWN_RADIUS for f in fragments)
    assert all(WORLD.contains(f.pos) for f in fragments)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_config.py tests/test_world_map.py tests/test_spawner.py -q --no-cov`
Expected: FAIL — `AttributeError: ... has no attribute 'TEMPLE_BAND_INNER_FRAC'`

- [ ] **Step 3: 상수를 바꾼다**

`src/game/config.py`:

```python
PLAYER_SPEED: Final[float] = 200.0  # px/s
```

World 절의 반지름 두 줄과 사원 띠 세 줄을 바꾼다.

```python
# The grassland's rim is a three-minute walk from the core at PLAYER_SPEED.
# That single number sets the map's scale; the outer radius then follows from
# keeping the grassland at a third of the total area.
GRASSLAND_RADIUS: Final[float] = 36_000.0  # 180s * 200px/s
MAP_RADIUS: Final[float] = 62_400.0  # (36000/62400)^2 = 1/3 of the area
BIOME_COUNT: Final[int] = 5
```

```python
# Where a boss temple may stand inside its sector, as a FRACTION of the ring's
# width -- an absolute radius silently lands in the wrong place the moment the
# map is rescaled. The angular inset keeps it off the seams, where it would
# read as belonging to the neighbouring biome.
TEMPLE_BAND_INNER_FRAC: Final[float] = 0.20
TEMPLE_BAND_OUTER_FRAC: Final[float] = 0.80
TEMPLE_ANGLE_INSET: Final[float] = 12.0  # degrees trimmed from each sector edge
```

Spawner 절에 더한다.

```python
SPAWN_RADIUS: Final[float] = 2_000.0  # spawns follow the player, not the whole map
```

`SPAWN_MAX`는 30 그대로 둔다 — 이제 플레이어 반경 2,000 안의 30개라서 빽빽하다.

- [ ] **Step 4: 맵을 고친다**

`src/game/world/map.py`에 프로퍼티를 더하고 `temple_sites`의 거리 계산을 바꾼다.

```python
    @property
    def ring_width(self) -> float:
        return self.radius - self.grassland_radius
```

```python
            distance = self.grassland_radius + self.ring_width * rng.uniform(
                config.TEMPLE_BAND_INNER_FRAC, config.TEMPLE_BAND_OUTER_FRAC
            )
```

- [ ] **Step 5: 스폰을 플레이어 주변으로 옮긴다**

`src/game/systems/spawner.py`의 `update`와 `_find_spot`에 `player_pos: pygame.Vector2`를 더하고, 자리 찾기를 이렇게 바꾼다.

```python
            point = near_player(player_pos, rng, world)
            if point is None:
                continue
```

`src/game/systems/spawn_common.py`에 공용 헬퍼를 더한다. 두 스포너가 같은 규칙을 쓰게 하려는 것이다.

```python
def near_player(
    player_pos: pygame.Vector2,
    rng: random.Random,
    world: WorldMap,
) -> pygame.Vector2 | None:
    """A random point within ``SPAWN_RADIUS`` of the player, or None if off-map.

    The map is far larger than one trip, so scattering spawns over all of it
    would leave nothing to find. Returning None rather than retrying inside
    keeps the retry budget in one place -- the caller's loop.
    """
    angle = rng.uniform(0.0, 2 * math.pi)
    distance = config.SPAWN_RADIUS * math.sqrt(rng.random())
    point = pygame.Vector2(
        player_pos.x + math.cos(angle) * distance,
        player_pos.y + math.sin(angle) * distance,
    )
    return point if world.contains(point) else None
```

`spawn_common.py`는 이제 `math`, `random`, `pygame`, `config`, `WorldMap`을 import한다. `WorldMap`은 `world.map`을 import하고 `world.map`은 `systems.physics`만 import하므로 순환은 없다.

`enemy_spawner.py`도 같은 함수를 쓰고, `_MIN_PLAYER_DIST`를 `600.0`으로 올린다 — 스폰 반경이 2,000이므로 300은 코앞이다.

`src/game/scenes/play.py`의 두 `spawner.update(...)` 호출에 `self.player.pos`를 더한다.

- [ ] **Step 6: 남은 테스트를 따라간다**

`tests/test_spawner.py`의 기존 `update(...)` 호출에 `player_pos`를 더한다. `CORE.pos`를 쓰면 된다.

`tests/test_enemy_spawner.py`도 마찬가지. `test_spawn_avoids_core_sync_zone_and_player`의 `player_pos = core.pos + (600, 0)`은 이제 코어 sync 반경(120)과 스폰 반경(2,000)이 겹치므로, `core.pos + (5_000, 0)`으로 옮긴다.

`tests/test_player.py`의 `test_clamped_to_the_map_rim`은 그대로 통과한다 (반지름 기준이라 축척 무관).

- [ ] **Step 7: 통과를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest -q --no-cov && ./.venv/Scripts/python.exe -m ruff check . && ./.venv/Scripts/python.exe -m ruff format --check . && ./.venv/Scripts/python.exe -m mypy`
Expected: 전부 PASS.
잔재 확인: `grep -rn "TEMPLE_BAND_INNER\b\|TEMPLE_BAND_OUTER\b\|random_point" --include='*.py' src tests` → `_FRAC` 붙은 것과 `WorldMap.random_point` 정의만 남는다

- [ ] **Step 8: 커밋**

```bash
git add -A src tests
git commit -m "feat(world): scale the map to a three-minute walk and follow the player with spawns"
```

---

### Task 2: 하루 주기

낮과 밤. 벽시계를 읽지 않고 누적된 `dt`로만 굴러간다.

**Files:**
- Create: `src/game/systems/daynight.py`
- Modify: `src/game/config.py`
- Test: `tests/test_daynight.py`

**Interfaces:**
- Produces:
  - `config.DAY_LENGTH = 300.0`, `config.NIGHT_LENGTH = 180.0`, `config.DAY_TOTAL` (= 480.0)
  - `game.systems.daynight`: 상수 `DAY = "day"`, `NIGHT = "night"`
  - `DayNight` dataclass: 필드 `elapsed: float = 0.0`, `day: int = 1`. 메서드 `update(dt) -> None`. 프로퍼티 `phase -> str`, `is_night -> bool`, `phase_fraction -> float` (현재 단계를 0.0~1.0로)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_daynight.py`를 새로 만든다.

```python
from game import config
from game.systems.daynight import DAY, NIGHT, DayNight


def test_a_fresh_clock_starts_on_the_morning_of_day_one():
    clock = DayNight()
    assert clock.day == 1
    assert clock.phase == DAY
    assert clock.is_night is False
    assert clock.phase_fraction == 0.0


def test_day_turns_to_night_at_the_end_of_the_day_length():
    clock = DayNight()
    clock.update(config.DAY_LENGTH - 1)
    assert clock.phase == DAY
    clock.update(1)
    assert clock.phase == NIGHT
    assert clock.is_night is True
    assert clock.day == 1  # still the same day


def test_the_day_counter_rolls_over_after_a_full_cycle():
    clock = DayNight()
    clock.update(config.DAY_TOTAL)
    assert clock.day == 2
    assert clock.phase == DAY
    assert clock.elapsed == 0.0


def test_a_huge_step_advances_several_days_without_drifting():
    # The fixed timestep means this never happens in play, but a clock that
    # loses the remainder on a big step would drift, and that is worth pinning.
    clock = DayNight()
    clock.update(config.DAY_TOTAL * 3 + 10)
    assert clock.day == 4
    assert clock.elapsed == 10


def test_phase_fraction_runs_zero_to_one_within_each_phase():
    clock = DayNight()
    clock.update(config.DAY_LENGTH / 2)
    assert clock.phase_fraction == 0.5
    clock.update(config.DAY_LENGTH / 2 + config.NIGHT_LENGTH / 4)
    assert clock.phase == NIGHT
    assert clock.phase_fraction == 0.25


def test_many_small_steps_match_one_big_step():
    fine = DayNight()
    for _ in range(600):
        fine.update(config.FIXED_DT)
    coarse = DayNight()
    coarse.update(600 * config.FIXED_DT)
    assert fine.day == coarse.day
    assert abs(fine.elapsed - coarse.elapsed) < 1e-6
```

- [ ] **Step 2: 실패를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_daynight.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'game.systems.daynight'`

- [ ] **Step 3: 상수를 넣는다**

`src/game/config.py`의 Timing 절 아래에 더한다.

```python
# --- Day / night --------------------------------------------------------------
# A day is long enough to walk to the biomes and back only just; the night is
# long enough to matter but not to dominate, since the raid cadence shortens to
# every two days late on and the player would otherwise only ever see darkness.
DAY_LENGTH: Final[float] = 300.0  # seconds of daylight
NIGHT_LENGTH: Final[float] = 180.0  # seconds of night
DAY_TOTAL: Final[float] = DAY_LENGTH + NIGHT_LENGTH
```

- [ ] **Step 4: 시계를 구현한다**

`src/game/systems/daynight.py`:

```python
"""The day/night clock. Pure: it advances only on the ``dt`` it is handed, never
on a wall clock, so a run is reproducible and the whole thing is testable
headlessly.

``elapsed`` is the position within the current day, not since the start of the
run -- keeping it bounded means a long session cannot lose precision in it.
"""

from __future__ import annotations

from dataclasses import dataclass

from game import config

DAY = "day"
NIGHT = "night"


@dataclass
class DayNight:
    elapsed: float = 0.0  # seconds into the current day, 0 <= elapsed < DAY_TOTAL
    day: int = 1

    def update(self, dt: float) -> None:
        self.elapsed += dt
        while self.elapsed >= config.DAY_TOTAL:
            self.elapsed -= config.DAY_TOTAL
            self.day += 1

    @property
    def phase(self) -> str:
        return DAY if self.elapsed < config.DAY_LENGTH else NIGHT

    @property
    def is_night(self) -> bool:
        return self.phase == NIGHT

    @property
    def phase_fraction(self) -> float:
        """How far through the current phase, 0.0 to 1.0."""
        if self.elapsed < config.DAY_LENGTH:
            return self.elapsed / config.DAY_LENGTH
        return (self.elapsed - config.DAY_LENGTH) / config.NIGHT_LENGTH
```

- [ ] **Step 5: 통과를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest -q --no-cov && ./.venv/Scripts/python.exe -m ruff check . && ./.venv/Scripts/python.exe -m ruff format --check . && ./.venv/Scripts/python.exe -m mypy`
Expected: 전부 PASS

- [ ] **Step 6: 커밋**

```bash
git add -A src tests
git commit -m "feat(systems): add the day/night clock"
```

---

### Task 3: 코어 레벨과 결계

결계는 코어의 상태다. 맵은 지형이고 결계는 플레이어가 키우는 것이라서 맵이 갖지 않는다.

**Files:**
- Modify: `src/game/config.py`, `src/game/entities/core.py`
- Test: `tests/test_core.py`, `tests/test_config.py`

**Interfaces:**
- Produces:
  - `config.CORE_MAX_LEVEL = 50`, `config.CORE_LEVEL_CAPS = (10, 20, 30, 40, 50)`, `config.CORE_SHARDS_TO_IGNITE = 5`
  - `config.WARD_RADIUS_BASE = 1_000.0`, `config.WARD_RADIUS_MAX` (= `GRASSLAND_RADIUS / sqrt(10)`)
  - `Core`: 필드 `pos`, `radius`, `sync_radius`, `level: int = 0`, `bosses_killed: int = 0`. 프로퍼티 `ignited -> bool` (`level >= 1`), `ward_radius -> float` (미점화면 `0.0`), `level_cap -> int`, `can_upgrade -> bool`. 메서드 `ignite() -> None`, `upgrade() -> bool`, `is_in_ward(point) -> bool`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_core.py`에 더한다 (기존 sync 테스트는 그대로 둔다).

```python
import math

from game import config


def _core():
    return Core(pos=pygame.Vector2(0, 0))


def test_an_unignited_core_has_no_ward_at_all():
    core = _core()
    assert core.level == 0
    assert core.ignited is False
    assert core.ward_radius == 0.0
    # Nothing is sheltered before ignition -- that is the pressure to build it.
    assert core.is_in_ward(pygame.Vector2(0, 0)) is False


def test_ignition_puts_the_core_at_level_one():
    core = _core()
    core.ignite()
    assert core.ignited is True
    assert core.level == 1
    assert core.ward_radius == config.WARD_RADIUS_BASE


def test_igniting_twice_changes_nothing():
    core = _core()
    core.ignite()
    core.upgrade()
    core.ignite()
    assert core.level == 2


def test_the_ward_covers_a_tenth_of_the_grassland_at_full_level():
    core = _core()
    core.bosses_killed = len(config.CORE_LEVEL_CAPS)
    while core.upgrade():
        pass
    assert core.level == config.CORE_MAX_LEVEL
    share = (core.ward_radius / config.GRASSLAND_RADIUS) ** 2
    assert math.isclose(share, 0.1, rel_tol=1e-6)


def test_the_ward_grows_by_the_same_ratio_every_level():
    # Absolute growth would make an early level invisible and a late one
    # enormous. A constant ratio makes every upgrade feel the same size.
    core = _core()
    core.bosses_killed = len(config.CORE_LEVEL_CAPS)
    core.ignite()
    ratios = []
    for _ in range(10):
        before = core.ward_radius
        core.upgrade()
        ratios.append(core.ward_radius / before)
    assert max(ratios) - min(ratios) < 1e-9


def test_the_level_cap_starts_at_ten_and_a_boss_opens_each_one():
    core = _core()
    core.ignite()
    assert core.level_cap == config.CORE_LEVEL_CAPS[0] == 10
    for killed, cap in enumerate(config.CORE_LEVEL_CAPS[1:], start=1):
        core.bosses_killed = killed
        assert core.level_cap == cap


def test_upgrading_stops_dead_at_the_cap():
    core = _core()
    core.ignite()
    while core.upgrade():
        pass
    assert core.level == config.CORE_LEVEL_CAPS[0]
    assert core.can_upgrade is False
    core.bosses_killed = 1  # a boss item lifts it
    assert core.can_upgrade is True
    assert core.upgrade() is True
    assert core.level == config.CORE_LEVEL_CAPS[0] + 1


def test_an_unignited_core_cannot_be_upgraded():
    core = _core()
    assert core.can_upgrade is False
    assert core.upgrade() is False
    assert core.level == 0


def test_the_ward_is_a_circle_around_the_core():
    core = _core()
    core.ignite()
    r = core.ward_radius
    assert core.is_in_ward(pygame.Vector2(r - 1, 0)) is True
    assert core.is_in_ward(pygame.Vector2(r + 1, 0)) is False
```

`tests/test_config.py`에 더한다.

```python
def test_the_level_caps_match_the_boss_count():
    # One boss opens one cap, and the fifth opens the final upgrade -- that is
    # what ties the core ladder to the five temples.
    assert config.CORE_LEVEL_CAPS == (10, 20, 30, 40, 50)
    assert config.CORE_LEVEL_CAPS[-1] == config.CORE_MAX_LEVEL
```

- [ ] **Step 2: 실패를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_core.py -q --no-cov`
Expected: FAIL — `AttributeError: 'Core' object has no attribute 'ignited'`

- [ ] **Step 3: 상수를 넣는다**

`src/game/config.py` 맨 위에 `import math`를 더하고 (`from __future__` 아래, `typing` 위), Core 절을 이렇게 바꾼다.

```python
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
# growth makes an early level invisible and a late one enormous. At full level
# it covers a tenth of the grassland's area, hence the sqrt(10).
WARD_RADIUS_BASE: Final[float] = 1_000.0
WARD_RADIUS_MAX: Final[float] = GRASSLAND_RADIUS / math.sqrt(10.0)
WARD_GROWTH: Final[float] = (WARD_RADIUS_MAX / WARD_RADIUS_BASE) ** (1 / (CORE_MAX_LEVEL - 1))
```

Core 절이 World 절보다 **아래**에 있어야 한다 (`GRASSLAND_RADIUS`를 쓰므로). 현재 파일이 그렇다.

- [ ] **Step 4: 코어를 구현한다**

`src/game/entities/core.py` 전체를 이걸로 교체한다.

```python
"""The central core the player assembles, ignites, and defends.

The ward is the core's state, not the map's: the map is terrain that was always
there, and the ward is the one thing the player grows. Upgrading it is the only
source of safety, of healing, and (later) of build space.

Level 0 is an unlit core with no ward at all -- there is nowhere to heal before
ignition, which is the pressure that gets the core built.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config


@dataclass
class Core:
    pos: pygame.Vector2
    radius: float = config.CORE_RADIUS
    sync_radius: float = config.CORE_SYNC_RADIUS
    level: int = 0  # 0 = not yet ignited
    bosses_killed: int = 0

    def is_in_sync_range(self, point: pygame.Vector2) -> bool:
        return self.pos.distance_to(point) <= self.sync_radius

    # --- ignition and levels --------------------------------------------
    @property
    def ignited(self) -> bool:
        return self.level >= 1

    def ignite(self) -> None:
        """Place the assembled core. Day one starts here. A no-op once lit."""
        if not self.ignited:
            self.level = 1

    @property
    def level_cap(self) -> int:
        """How high this core can go until another boss drop arrives."""
        index = min(self.bosses_killed, len(config.CORE_LEVEL_CAPS) - 1)
        return config.CORE_LEVEL_CAPS[index]

    @property
    def can_upgrade(self) -> bool:
        return self.ignited and self.level < self.level_cap

    def upgrade(self) -> bool:
        """Raise the level by one. Return False when the cap blocks it."""
        if not self.can_upgrade:
            return False
        self.level += 1
        return True

    # --- the ward --------------------------------------------------------
    @property
    def ward_radius(self) -> float:
        if not self.ignited:
            return 0.0
        return config.WARD_RADIUS_BASE * config.WARD_GROWTH ** (self.level - 1)

    def is_in_ward(self, point: pygame.Vector2) -> bool:
        return self.ignited and self.pos.distance_to(point) <= self.ward_radius
```

- [ ] **Step 5: 통과를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest -q --no-cov && ./.venv/Scripts/python.exe -m ruff check . && ./.venv/Scripts/python.exe -m ruff format --check . && ./.venv/Scripts/python.exe -m mypy`
Expected: 전부 PASS

수치를 눈으로 확인한다:

```bash
./.venv/Scripts/python.exe -c "
from game.entities.core import Core
from game import config
import pygame
c = Core(pos=pygame.Vector2(0,0)); c.ignite(); c.bosses_killed = 9
for target in (1,10,20,30,40,50):
    while c.level < target: c.upgrade()
    print(f'level {c.level:2d}  ward {c.ward_radius:9,.0f}')"
```

- [ ] **Step 6: 커밋**

```bash
git add -A src tests
git commit -m "feat(core): add levels, boss-gated caps and the ward radius"
```

---

### Task 4: 결계 안 가속 회복

들어오면 천천히, 머물수록 빨라진다. 나가면 리셋된다. 가장자리만 툭 찍는 꼼수를 막는다.

**Files:**
- Create: `src/game/systems/survival.py`
- Modify: `src/game/config.py`, `src/game/entities/player.py`
- Test: `tests/test_survival.py`

**Interfaces:**
- Consumes: Task 3의 `Core.is_in_ward`
- Produces:
  - `config.WARD_REGEN_BASE = 1.0`, `config.WARD_REGEN_RAMP = 0.5`, `config.WARD_REGEN_MAX = 8.0`
  - `Player`에 필드 `ward_time: float = 0.0`
  - `game.systems.survival.update_regen(dt: float, player: Player, core: Core) -> None`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_survival.py`를 새로 만든다.

```python
import pygame

from game import config
from game.entities.core import Core
from game.entities.player import Player
from game.systems import survival

CENTRE = pygame.Vector2(0, 0)


def _lit_core() -> Core:
    core = Core(pos=pygame.Vector2(CENTRE))
    core.ignite()
    return core


def _hurt(pos: pygame.Vector2, hp: float = 10.0) -> Player:
    return Player(pos=pos, hp=hp)


def test_there_is_no_healing_in_the_field():
    core = _lit_core()
    player = _hurt(pygame.Vector2(core.ward_radius + 100, 0))
    survival.update_regen(5.0, player, core)
    assert player.hp == 10.0
    assert player.ward_time == 0.0


def test_there_is_no_healing_before_the_core_is_lit():
    core = Core(pos=pygame.Vector2(CENTRE))  # unignited
    player = _hurt(pygame.Vector2(CENTRE))
    survival.update_regen(5.0, player, core)
    assert player.hp == 10.0


def test_healing_starts_slow_inside_the_ward():
    core = _lit_core()
    player = _hurt(pygame.Vector2(CENTRE))
    survival.update_regen(1.0, player, core)
    assert player.hp == 10.0 + config.WARD_REGEN_BASE


def test_healing_speeds_up_the_longer_you_stay():
    core = _lit_core()
    player = _hurt(pygame.Vector2(CENTRE))
    survival.update_regen(1.0, player, core)
    first = player.hp - 10.0
    before = player.hp
    survival.update_regen(1.0, player, core)
    second = player.hp - before
    assert second > first


def test_the_rate_stops_climbing_at_the_cap():
    core = _lit_core()
    player = _hurt(pygame.Vector2(CENTRE), hp=1.0)
    player.max_hp = 10_000.0  # room to keep healing
    for _ in range(100):
        survival.update_regen(1.0, player, core)
    before = player.hp
    survival.update_regen(1.0, player, core)
    assert player.hp - before == config.WARD_REGEN_MAX


def test_stepping_out_resets_the_ramp():
    # Otherwise tagging the ward's edge between fights would bank the fast rate.
    core = _lit_core()
    player = _hurt(pygame.Vector2(CENTRE))
    for _ in range(30):
        survival.update_regen(1.0, player, core)
    assert player.ward_time > 0
    player.pos = pygame.Vector2(core.ward_radius + 100, 0)
    survival.update_regen(1.0, player, core)
    assert player.ward_time == 0.0
    player.pos = pygame.Vector2(CENTRE)
    before = player.hp
    survival.update_regen(1.0, player, core)
    assert player.hp - before == config.WARD_REGEN_BASE  # slow again


def test_healing_never_passes_full():
    core = _lit_core()
    player = Player(pos=pygame.Vector2(CENTRE), hp=config.PLAYER_MAX_HP - 1)
    survival.update_regen(10.0, player, core)
    assert player.hp == config.PLAYER_MAX_HP


def test_a_dead_player_is_not_healed():
    core = _lit_core()
    player = Player(pos=pygame.Vector2(CENTRE), hp=0.0)
    survival.update_regen(10.0, player, core)
    assert player.hp == 0.0
```

- [ ] **Step 2: 실패를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_survival.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'game.systems.survival'`

- [ ] **Step 3: 상수와 필드를 넣는다**

`src/game/config.py`에 더한다 (Core 절 아래).

```python
# --- Survival ----------------------------------------------------------------
# Regen ramps up the longer the player stays inside the ward and resets the
# moment they leave, so tagging the edge between fights banks nothing. Free but
# slow to start, which leaves potions their job: healing RIGHT NOW.
WARD_REGEN_BASE: Final[float] = 1.0  # hp/s on arrival
WARD_REGEN_RAMP: Final[float] = 0.5  # hp/s added per second spent inside
WARD_REGEN_MAX: Final[float] = 8.0  # hp/s ceiling, reached after 14s
```

`src/game/entities/player.py`의 필드에 더한다.

```python
    ward_time: float = 0.0  # seconds spent inside the ward; resets on leaving
```

- [ ] **Step 4: 회복을 구현한다**

`src/game/systems/survival.py`:

```python
"""Staying alive: healing inside the ward.

Pure functions over injected state, like the rest of ``systems/``.

There is no healing in the field at all. The ward is the only place HP comes
back for free, and it comes back slowly at first -- the rate climbs the longer
the player stays and resets the moment they step out, so touching the edge
between fights banks nothing. Potions stay worth carrying because they are the
only healing that is instant.
"""

from __future__ import annotations

from game import config
from game.entities.core import Core
from game.entities.player import Player


def update_regen(dt: float, player: Player, core: Core) -> None:
    """Heal the player if they are inside the ward, at a rate that ramps up."""
    if player.hp <= 0 or not core.is_in_ward(player.pos):
        player.ward_time = 0.0
        return
    rate = min(
        config.WARD_REGEN_MAX,
        config.WARD_REGEN_BASE + config.WARD_REGEN_RAMP * player.ward_time,
    )
    player.ward_time += dt
    player.hp = min(player.max_hp, player.hp + rate * dt)
```

- [ ] **Step 5: 통과를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest -q --no-cov && ./.venv/Scripts/python.exe -m ruff check . && ./.venv/Scripts/python.exe -m ruff format --check . && ./.venv/Scripts/python.exe -m mypy`
Expected: 전부 PASS

- [ ] **Step 6: 커밋**

```bash
git add -A src tests
git commit -m "feat(systems): heal inside the ward at a rate that ramps up"
```

---

### Task 5: 골렘은 결계에 못 들어온다

결계의 두 번째 값어치. 습격 밤의 예외는 6단계에서 붙는다.

**Files:**
- Modify: `src/game/systems/combat.py`, `src/game/systems/enemy_spawner.py`, `src/game/scenes/play.py`
- Test: `tests/test_combat.py`, `tests/test_enemy_spawner.py`

**Interfaces:**
- Consumes: Task 3의 `Core.is_in_ward`, `Core.ward_radius`
- Produces: `combat.update_enemies(dt, enemies, player, world, core)` — 인자가 하나 늘어난다. 결계 안으로 들어간 골렘은 가장자리로 밀려난다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_combat.py`에 더한다.

```python
def test_golems_cannot_enter_the_ward():
    core = Core(pos=pygame.Vector2(CENTRE))
    core.ignite()
    player = Player(pos=pygame.Vector2(CENTRE))  # standing at the core
    golem = Golem(pos=CENTRE + pygame.Vector2(core.ward_radius + 5, 0))
    for _ in range(200):
        combat.update_enemies(config.FIXED_DT, [golem], player, WORLD, core)
    # It chases the player but the ward holds it on the rim.
    assert CENTRE.distance_to(golem.pos) >= core.ward_radius - 1e-6


def test_an_unlit_core_shelters_nothing():
    core = Core(pos=pygame.Vector2(CENTRE))  # never ignited
    player = Player(pos=pygame.Vector2(CENTRE))
    golem = Golem(pos=CENTRE + pygame.Vector2(200, 0))
    combat.update_enemies(1.0, [golem], player, WORLD, core)
    assert CENTRE.distance_to(golem.pos) < 200  # walked straight in
```

기존 `update_enemies` 호출 세 곳에 `core` 인자를 더한다. 파일 상단에 `from game.entities.core import Core`를 더한다.

`tests/test_enemy_spawner.py`에 더한다.

```python
def test_golems_do_not_spawn_inside_the_ward():
    spawner = EnemySpawner()
    core = _core()
    core.ignite()
    player_pos = core.pos + pygame.Vector2(1_500, 0)  # inside the spawn radius
    for seed in range(30):
        enemies: list[Golem] = []
        spawner = EnemySpawner()
        golem = spawner.update(
            config.GOLEM_SPAWN_INTERVAL, enemies, player_pos, core, random.Random(seed), WORLD
        )
        if golem is not None:
            assert not core.is_in_ward(golem.pos)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_combat.py tests/test_enemy_spawner.py -q --no-cov`
Expected: FAIL — `TypeError: update_enemies() takes 4 positional arguments but 5 were given`

- [ ] **Step 3: 구현한다**

`src/game/systems/combat.py`
- import에 `from game.entities.core import Core`를 더한다
- `update_enemies`에 `core: Core` 인자를 더한다
- 본문의 `enemy.update(dt, player.pos, world)` 다음에 결계 밀어내기를 넣는다

```python
    for enemy in enemies:
        enemy.update(dt, player.pos, world)
        _hold_outside_ward(enemy, core)
        if player.invulnerable:
            continue
        ...
```

그리고 모듈에 헬퍼를 더한다.

```python
def _hold_outside_ward(enemy: Golem, core: Core) -> None:
    """Push a golem back to the ward's rim. The ward is what the core buys.

    On raid nights this will be lifted -- that is the whole point of a raid --
    but the exception belongs with the raid scheduler, not here.
    """
    if not core.is_in_ward(enemy.pos):
        return
    offset = enemy.pos - core.pos
    distance = offset.length()
    if distance == 0:
        offset = pygame.Vector2(1, 0)
        distance = 1.0
    enemy.pos.update(core.pos + offset * (core.ward_radius / distance))
```

`src/game/systems/enemy_spawner.py`의 `_find_spot` 재시도 루프에 한 줄을 더한다.

```python
            if core.is_in_ward(point):
                continue
```

`src/game/scenes/play.py`의 `combat.update_enemies(...)` 호출에 `self.core`를 더한다.

- [ ] **Step 4: 통과를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest -q --no-cov && ./.venv/Scripts/python.exe -m ruff check . && ./.venv/Scripts/python.exe -m ruff format --check . && ./.venv/Scripts/python.exe -m mypy`
Expected: 전부 PASS

- [ ] **Step 5: 커밋**

```bash
git add -A src tests
git commit -m "feat(combat): keep golems out of the ward"
```

---

### Task 6: 점화와 화면

파편을 모아 코어를 직접 놓는다. 그 순간이 1일차다. 그리고 밤과 결계를 눈에 보이게 만든다.

**Files:**
- Modify: `src/game/config.py`, `src/game/scenes/play.py`
- Test: `tests/test_play_scene.py`

**Interfaces:**
- Consumes: Task 2~5 전부
- Produces:
  - `config.NIGHT_DARKNESS = 150`, `config.WARD_COLOR`, `config.PEDESTAL_COLOR`
  - `PlayScene.clock: DayNight`
  - `PlayScene`가 **E**로 점화한다 (코어 자리에 서서, 파편 `CORE_SHARDS_TO_IGNITE`개를 들고). 점화 전에는 E가 저장고 이동을 하지 않는다 — 저장고가 없다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_play_scene.py`에 더한다.

```python
def test_the_run_starts_with_an_unlit_core_and_no_ward():
    scene = PlayScene()
    assert scene.core.ignited is False
    assert scene.core.ward_radius == 0.0
    assert scene.clock.day == 1


def test_shards_are_scattered_within_reach_of_the_spawn():
    scene = PlayScene()
    on_ground = [f for f in scene.fragments if f.kind is CORE_SHARD]
    assert len(on_ground) >= config.CORE_SHARDS_TO_IGNITE
    assert all(scene.player.pos.distance_to(f.pos) < config.SPAWN_RADIUS for f in on_ground)


def test_pressing_e_on_the_pedestal_with_enough_shards_ignites_the_core():
    scene = PlayScene()
    scene.player.pos = pygame.Vector2(scene.core.pos)
    scene.backpack.add(CORE_SHARD, config.CORE_SHARDS_TO_IGNITE)
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    assert scene.core.ignited is True
    assert scene.core.level == 1
    assert scene.backpack.count(CORE_SHARD) == 0  # the shards are consumed


def test_too_few_shards_does_not_ignite():
    scene = PlayScene()
    scene.player.pos = pygame.Vector2(scene.core.pos)
    scene.backpack.add(CORE_SHARD, config.CORE_SHARDS_TO_IGNITE - 1)
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    assert scene.core.ignited is False
    assert scene.backpack.count(CORE_SHARD) == config.CORE_SHARDS_TO_IGNITE - 1


def test_igniting_away_from_the_pedestal_does_nothing():
    scene = PlayScene()
    scene.player.pos = scene.core.pos + pygame.Vector2(5_000, 0)
    scene.backpack.add(CORE_SHARD, config.CORE_SHARDS_TO_IGNITE)
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    assert scene.core.ignited is False


def test_the_clock_advances_with_the_scene():
    scene = PlayScene()
    for _ in range(120):
        scene.update(config.FIXED_DT)
    assert scene.clock.elapsed == pytest.approx(120 * config.FIXED_DT)


def test_the_player_heals_only_after_ignition():
    scene = PlayScene()
    scene.player.pos = pygame.Vector2(scene.core.pos)
    scene.player.hp = 10.0
    scene.update(config.FIXED_DT)
    assert scene.player.hp == 10.0  # no ward yet
    scene.core.ignite()
    scene.update(config.FIXED_DT)
    assert scene.player.hp > 10.0


def test_night_darkens_the_screen():
    scene = PlayScene()
    scene.camera.center_on(scene.world.center)
    probe = (config.SCREEN_WIDTH // 2 + int(config.CORE_RADIUS) + 20, config.SCREEN_HEIGHT // 2)

    lit = pygame.Surface(config.SCREEN_SIZE)
    scene.draw(lit)
    day_pixel = lit.get_at(probe)[:3]

    scene.clock.elapsed = config.DAY_LENGTH + 1  # into the night
    dark = pygame.Surface(config.SCREEN_SIZE)
    scene.draw(dark)
    night_pixel = dark.get_at(probe)[:3]

    assert sum(night_pixel) < sum(day_pixel)
```

`tests/test_play_scene.py` 상단에 `import pytest`를 더한다.

**주의:** 기존 `test_sync_moves_the_backpack_into_the_store` 계열 테스트는 이제 점화되지 않은 코어에서 E를 누르므로 실패한다. 각 테스트 앞에 `scene.core.ignite()`를 넣어 고친다.

- [ ] **Step 2: 실패를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_play_scene.py -q --no-cov`
Expected: FAIL — `AttributeError: 'PlayScene' object has no attribute 'clock'`

- [ ] **Step 3: 상수를 넣는다**

`src/game/config.py`의 색 절에 더한다.

```python
NIGHT_DARKNESS: Final[int] = 150  # alpha of the night overlay, 0-255
WARD_COLOR: Final[tuple[int, int, int]] = (120, 220, 255)
PEDESTAL_COLOR: Final[tuple[int, int, int]] = (150, 150, 165)
```

- [ ] **Step 4: 씬을 배선한다**

`src/game/scenes/play.py`

import에 더한다.

```python
from game.systems import combat, mining, survival
from game.systems.daynight import DayNight
```

`__init__`에서 `self.core` 생성 뒤에 더한다.

```python
        self.clock = DayNight()
```

그리고 파편 목록을 만든 뒤, 점화용 파편을 뿌린다.

```python
        self.fragments: list[Fragment] = []
        self.spawner = Spawner()
        self._scatter_starting_shards()
```

메서드를 더한다.

```python
    def _scatter_starting_shards(self) -> None:
        """Seed the pedestal's surroundings with the shards that light the core.

        They sit within reach of the spawn on purpose: the opening should be a
        short errand, not a search. Placing the core is what starts day one, and
        the player chooses when.
        """
        for _ in range(config.CORE_SHARDS_TO_IGNITE + 2):  # two spare
            spot = near_player(self.player.pos, self.rng, self.world)
            if spot is not None:
                self.fragments.append(Fragment(pos=spot, kind=CORE_SHARD))
```

`from game.systems.spawn_common import near_player`를 import에 더한다.

`update`에서 시계와 회복을 돌리고, E의 의미를 갈라준다.

```python
        self.clock.update(dt)
```

를 `self.player.update(...)` 앞에 넣고,

```python
        if sync and self.core.is_in_sync_range(self.player.pos):
            moved = self.store.add(CORE_SHARD, self.backpack.count(CORE_SHARD))
            self.backpack.remove(CORE_SHARD, moved)
```

를 이걸로 바꾼다.

```python
        if sync and self.core.is_in_sync_range(self.player.pos):
            if self.core.ignited:
                moved = self.store.add(CORE_SHARD, self.backpack.count(CORE_SHARD))
                self.backpack.remove(CORE_SHARD, moved)
            elif self.backpack.count(CORE_SHARD) >= config.CORE_SHARDS_TO_IGNITE:
                self.backpack.remove(CORE_SHARD, config.CORE_SHARDS_TO_IGNITE)
                self.core.ignite()
```

`combat.update_enemies(...)` 호출에 `self.core`를 더하고, 그 아래에 회복을 넣는다.

```python
        survival.update_regen(dt, self.player, self.core)
```

- [ ] **Step 5: 렌더링을 더한다**

`draw`의 `self._draw_temples(surface)` 다음에 결계를, `self._draw_hud(surface)` 앞에 밤을 넣는다.

```python
        self._draw_world(surface)
        self._draw_ward(surface)
        self._draw_temples(surface)
        ...
        self._draw_night(surface)
        self._draw_hud(surface)
```

메서드 두 개를 더한다.

```python
    def _draw_ward(self, surface: pygame.Surface) -> None:
        """The ward's rim, or the bare pedestal before the core is lit."""
        center = self.camera.world_to_screen(self.core.pos)
        if not self.core.ignited:
            pygame.draw.circle(surface, config.PEDESTAL_COLOR, center, self.core.radius, 3)
            return
        pygame.draw.circle(surface, config.WARD_COLOR, center, self.core.ward_radius, 2)

    def _draw_night(self, surface: pygame.Surface) -> None:
        """Darken everything outside the ward once night falls.

        Drawn before the HUD so the gauges stay readable, and punched through
        inside the ward so the safe ground reads as safe at a glance.
        """
        if not self.clock.is_night:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 20, config.NIGHT_DARKNESS))
        if self.core.ignited:
            pygame.draw.circle(
                overlay,
                (0, 0, 0, 0),
                self.camera.world_to_screen(self.core.pos),
                self.core.ward_radius,
            )
        surface.blit(overlay, (0, 0))
```

`_draw_hud`에 날짜와 단계를 더한다. 이 씬에는 아직 폰트가 없으므로 글자 대신 **막대**로 표시한다 — 폰트는 별도 작업이다.

```python
        # day progress: fills across the day, empties across the night
        phase_color = (240, 220, 130) if not self.clock.is_night else (90, 110, 200)
        _draw_bar(surface, 62, 5, self.clock.phase_fraction, phase_color, bg=(40, 40, 55))
```

- [ ] **Step 6: 통과를 확인한다**

Run: `./.venv/Scripts/python.exe -m pytest -q && ./.venv/Scripts/python.exe -m ruff check . && ./.venv/Scripts/python.exe -m ruff format --check . && ./.venv/Scripts/python.exe -m mypy`
Expected: 전부 PASS

손으로 확인한다:

```bash
PYTHONIOENCODING=utf-8 SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
./.venv/Scripts/python.exe -c "
import pygame; pygame.init()
from game.scenes.play import PlayScene
from game import config
from game.items.item_kinds import CORE_SHARD
s = PlayScene()
print('start   : ignited', s.core.ignited, '| day', s.clock.day)
s.player.pos = pygame.Vector2(s.core.pos)
s.backpack.add(CORE_SHARD, config.CORE_SHARDS_TO_IGNITE)
s.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
s.update(config.FIXED_DT)
print('ignited : level', s.core.level, '| ward', round(s.core.ward_radius))
s.player.hp = 10.0
for _ in range(int(20/config.FIXED_DT)): s.update(config.FIXED_DT)
print('after20s: hp', round(s.player.hp,1), '| phase', s.clock.phase)
for _ in range(int(config.DAY_TOTAL/config.FIXED_DT)): s.update(config.FIXED_DT)
print('next day: day', s.clock.day, '| phase', s.clock.phase)
pygame.quit()"
```

- [ ] **Step 7: 커밋**

```bash
git add -A src tests
git commit -m "feat(play): ignite the core, run the clock and show the ward and the night"
```

---

## 이 계획이 끝나면

맵이 실제 축척이고, 코어를 직접 점화해서 하루가 시작되고, 결계가 레벨을 따라 넓어지고, 그 안에서만 (그리고 머물수록 빠르게) 회복되고, 골렘이 결계에 못 들어오고, 낮과 밤이 돈다.

습격도 야생동물도 건축도 없다. 코어를 올리는 **수단**(강화 비용)도 아직 없다 — `upgrade()`는 있지만 부르는 쪽이 없다. 그건 5단계(자원과 제작)에서 제작 시설과 함께 붙는다.

**남은 걱정:** 사원까지 편도 3.4~4.8분이라 왕복이 하루를 통째로 먹는다. 완화하려면 `TEMPLE_BAND_*_FRAC`을 `0.10 / 0.40`으로 당기면 편도 2~3분이 된다. 상수 두 개다.
