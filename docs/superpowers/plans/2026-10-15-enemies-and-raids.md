# 6단계: 적 재분류와 습격 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 적을 골렘과 야생동물로 나누고, 코어에 HP를 주고, 정해진 밤마다 결계가 뚫리는 습격을 만든다. 습격의 주기와 구성이 플레이어의 진행도를 따라가게 한다.

**Architecture:** 적 종류는 frozen dataclass 표, 습격 일정은 순수 계산이다. 코어 피해와 수리는 순수 함수. 렌더링만 `scenes/play.py`에.

**Tech Stack:** pygame-ce, Python >= 3.10, pytest + pytest-cov, ruff, mypy (strict)

**Spec:** `docs/superpowers/specs/2026-08-29-world-rebuild-concept-design.md`
**구조를 물려받는 곳:** `docs/superpowers/specs/2026-07-30-core-defense-design.md` (코어 HP·수리·패배 신호의 구조는 유효, 이름과 수치는 교체)

**선행:** 1~5단계 완료

## Global Constraints

- 로직은 순수 `update(dt, ...)`, 렌더링은 `draw(surface)`. `pygame.display` / 이벤트 펌프 / `pygame.quit`는 `core/app.py`에만.
- `config.py`는 pygame을 import하지 않는다.
- 고정 타임스텝 `FIXED_DT = 1/60`. 난수는 주입한다. 벽시계를 읽지 않는다.
- TDD: 실패하는 테스트 → 최소 구현 → 리팩터.
- 명령어: `./.venv/Scripts/python.exe -m pytest` · `-m ruff check . && -m ruff format --check .` · `-m mypy`
- 각 작업의 마지막 단계는 커밋이다.

## 이 단계의 결정

**적은 두 갈래다.**

| | 노리는 것 | 언제 | 주는 것 |
|---|---|---|---|
| **골렘** | 코어 | 점화 후 항상, 습격 밤에 몰려옴 | 없음 |
| **야생동물** | 플레이어 | 밤, 결계 주변 | 고기·가죽 |

야생동물이 **점화 전의 유일한 위협**이다. 5단계에서 골렘을 점화 뒤로 미루면서 오프닝이 완전히 조용해졌는데, 스펙은 거기에 긴장이 있기를 원한다 — 회복이 안 되는 상태로 밤을 보내는 압박이 코어를 켜게 만드는 힘이다.

**습격 밤에는 결계가 골렘을 막지 못한다.** 다만 **회복은 계속 된다.** 스펙이 뚫리는 것은 골렘뿐이라고 말하고, 싸우는 동안 회복마저 끊기면 습격은 버티는 게 아니라 당하는 것이 된다. 결계는 벽이기를 멈추지만 화로이기는 계속한다.

**코어에 HP가 생긴다.** 습격 밤에 코어에 닿은 골렘이 깎는다. 0이 되면 **패배 신호**까지만 — 화면이나 흐름은 9단계(최종전)에서 붙인다. 수리는 자원을 먹는다.

**주기와 구성이 진행도를 따라간다.**

```
잡은 보스   0    1    2    3    4    5
습격 주기   7일  6일  5일  4일  3일  2일
```

어떤 바이옴의 보스를 잡으면 그 바이옴의 골렘이 습격에 합류한다. 별도의 난이도 수치가 없고, **"강해진 대가로 밤이 잦고 험해진다"**로 읽힌다.

## 범위 밖

- **보스** — 8단계. 여기서는 `bosses_killed`를 읽기만 한다 (지금은 늘 0).
- **바이옴 골렘의 고유 행동** — 8단계. 여기서는 합류한다는 사실과 수치만.
- **패배 화면·게임 흐름** — 9단계. 여기서는 플래그까지.
- **스테미나** — 생존 절 주제. 따로.

## File Structure

| 파일 | 책임 |
|---|---|
| `entities/enemy.py` | `EnemyKind` 표, `Golem`이 종류를 갖는다 |
| `entities/beast.py` | **신규** 야생동물 |
| `systems/raids.py` | **신규** 습격 일정. 순수 |
| `entities/core.py` | HP·피해·수리·파괴 |
| `systems/enemy_spawner.py` | 거리에 따른 강화, 습격 때 몰려옴 |
| `systems/beast_spawner.py` | **신규** 밤에 결계 주변 |
| `systems/combat.py` | 습격 밤에는 결계가 골렘을 막지 않는다 |
| `items/item_kinds.py` | 가죽 |
| `scenes/play.py` | 배선, 습격 표시, 코어 HP 바 |

---

### Task 1: 적 카탈로그

**Files:** Modify `entities/enemy.py`, `config.py` · Test `tests/test_enemy.py`

**Produces:**
- 표적 상수 `TARGET_CORE`, `TARGET_PLAYER`
- `EnemyKind(key, name, target, hp, speed, radius, damage, color)` — frozen
- `GOLEM_KINDS: tuple[EnemyKind, ...]` — 평범한 골렘 1종으로 시작하고, 바이옴 골렘 5종은 8단계에서 붙는다
- `Golem`이 `kind: EnemyKind`를 갖고, hp/speed/radius/color가 거기서 나온다

**핵심:** 지금 `Golem`은 수치를 직접 들고 있다. 바이옴마다 다른 골렘이 생기면 그 방식으로는 종류마다 클래스가 하나씩 필요해진다. 표로 빼면 행 하나가 종류 하나다 — `ItemKind`·`Biome`과 같은 모양.

- [ ] **Step 1~5:** 테스트 · 실패 확인 · 구현 · 검증 · 커밋 `refactor(enemy): put golem stats in a kind table`

---

### Task 2: 거리에 따른 강화

**Files:** Modify `systems/enemy_spawner.py`, `config.py` · Test `tests/test_enemy_spawner.py`

**Produces:** 스폰되는 골렘의 HP와 속도가 **코어에서의 거리**를 따라 오른다. `config.GOLEM_SCALE_AT_EDGE`가 맵 가장자리에서의 배율

스펙의 "코어에서 멀어질수록 강한 골렘"이다. 거리는 이미 `WorldMap.distance_fraction`이 답한다.

**핵심 — 테스트로 못박을 것:**
- 결계 근처에서 나온 골렘과 맵 끝에서 나온 골렘의 HP가 다르다
- 배율은 거리에 대해 단조 증가한다
- 코어 바로 옆(`fraction == 0`)에서는 표의 기본값 그대로다

- [ ] **Step 1~5:** 테스트 · 구현 · 검증 · 커밋 `feat(enemy): make golems harder the further out they spawn`

---

### Task 3: 야생동물

**Files:** Create `entities/beast.py`, `systems/beast_spawner.py` · Modify `items/item_kinds.py`, `systems/combat.py`, `scenes/play.py`, `config.py` · Test `tests/test_beast.py`(신규), `test_play_scene.py`

**Produces:**
- 카탈로그에 `HIDE`("가죽") — 이걸로 **가죽 배낭** 조합법이 생긴다(5단계에서 비워둔 자리)
- `BeastKind` 두 종: **늑대**(쫓아와서 문다) / **토끼**(달아난다, 잡으면 재료)
- `Beast(pos, kind)` — `update(dt, player_pos, world)`
- `BeastSpawner` — **밤에만**, **결계 주변 띠**에 나온다. 점화 전에는 플레이어 주변에
- 죽으면 고기와 가죽을 떨군다

**핵심:**
- 야생동물은 **코어를 노리지 않는다.** 파밍하러 나가는 길을 성가시게 하는 것이 일이다
- **점화 전에도 나온다.** 그게 오프닝의 유일한 위협이고, 회복할 곳이 없다는 사실과 합쳐져 코어를 켜게 만든다
- 낮이 되면 **새로 나오지 않는다**. 이미 나온 것은 남는다 — 해가 떴다고 늑대가 증발하면 이상하다

- [ ] **Step 1~6:** 테스트 · 구현 · 배선 · 가죽 배낭 조합법 · 검증 · 커밋 `feat(world): put wild animals out at night`

---

### Task 4: 습격 일정

**Files:** Create `systems/raids.py` · Modify `config.py` · Test `tests/test_raids.py`(신규)

**Produces:**
- `config.RAID_INTERVALS: tuple[int, ...] = (7, 6, 5, 4, 3, 2)`
- `raids.interval(bosses_killed) -> int`
- `raids.is_raid_night(day, bosses_killed) -> bool`
- `raids.days_until(day, bosses_killed) -> int`

**핵심 — 테스트로 못박을 것:**
- 보스 0마리면 7일마다, 5마리면 2일마다
- 보스 수가 표를 넘어도(6 이상) 2일로 머문다 — 인덱스가 터지지 않는다
- `days_until`이 습격 당일에 0을 답한다
- 1일차는 습격이 아니다 — 시작하자마자 습격이면 배울 시간이 없다

**순수 계산이다.** 시계도 상태도 들고 있지 않고, 날짜와 보스 수만 받는다. 그래서 "7일 뒤에 무슨 일이 생기나"를 테스트가 한 줄로 물어볼 수 있다.

- [ ] **Step 1~5:** 테스트 · 실패 확인 · 구현 · 검증 · 커밋 `feat(systems): work out which nights are raids`

---

### Task 5: 코어 HP와 뚫리는 결계

**Files:** Modify `entities/core.py`, `systems/combat.py`, `systems/enemy_spawner.py`, `scenes/play.py`, `config.py` · Test `tests/test_core.py`, `test_combat.py`, `test_play_scene.py`

**Produces:**
- `Core.hp`, `Core.max_hp`(레벨을 따라 오른다), `Core.damage(amount)`, `Core.repair(n) -> int`, `Core.is_destroyed`
- `combat.update_enemies(..., raid: bool)` — 습격 밤이면 결계가 골렘을 막지 않는다
- 코어에 닿은 골렘이 HP를 깎는다
- `PlayScene.defeated` — HP 0에서 참. **신호까지만**

**핵심:**
- **회복은 습격 중에도 된다.** 뚫리는 것은 골렘뿐이다. 싸우는 동안 회복마저 끊기면 습격은 버티는 게 아니라 당하는 것이 된다 — 결계는 벽이기를 멈추지만 화로이기는 계속한다
- 코어 HP는 **레벨을 따라 오른다.** 코어를 올리는 또 하나의 값어치이고, 비어 있던 36~50레벨에 줄 수 있는 일거리다
- 수리는 자원을 먹는다 (돌? 주괴?) — **정확히 무엇을 먹을지는 Task 5에서 정한다**
- 패배는 플래그로 끝낸다. 화면도 재시작도 9단계 일이다

- [ ] **Step 1~6:** 테스트 · 구현 · 배선 · 검증 · 커밋 `feat(core): give the core hit points and let raids through the ward`

---

### Task 6: 습격이 보이게

**Files:** Modify `scenes/play.py`, `config.py` · Test `tests/test_play_scene.py`

- **코어 HP 바** — 왼쪽 위 막대에 한 줄 추가. 깎였을 때만 보이게 할지는 구현하면서 판단
- **습격 밤 표시** — 밤 막대가 붉게, 결계 테두리가 끊기거나 붉게. 뚫려 있다는 것이 눈에 보여야 한다
- **오늘이 며칠이고 습격까지 며칠인지** — 글자로. 제작 메뉴에 쓴 글꼴을 그대로
- 야생동물과 골렘이 **색으로 구분**되어야 한다

**핵심:** 습격은 예고 없이 오면 안 된다. 스펙의 주기는 플레이어가 **셀 수 있어야** 의미가 있고, 셀 수 없으면 그냥 가끔 벌어지는 사고다.

- [ ] **Step 1~5:** 테스트 · 구현 · 손으로 확인 · 검증 · 커밋 `feat(play): show the day, the next raid and the core's health`

---

## 이 계획이 끝나면

밤에 늑대가 돌아다니고, 며칠마다 결계가 뚫려 골렘이 코어로 몰려오고, 코어가 깎이고 수리된다. 습격 주기는 보스를 잡을수록 짧아지는데, 보스가 아직 없으므로 지금은 7일 고정이다.

**남는 것:** 바이옴 골렘 5종과 그 합류(8단계), 패배 화면(9단계), 스테미나.
