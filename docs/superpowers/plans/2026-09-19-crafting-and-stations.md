# 5b단계: 시설과 제작 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 제작 메뉴 하나로 만들기를 통일하고, 결계 안에 시설을 지어 배치하고, 주조에 시간이 걸리게 한다. 도구 등급 사다리를 위까지 잇고 배낭을 만들 수 있게 한다.

**Architecture:** 조합법은 frozen dataclass 표, 무엇을 만들 수 있는지 판정하는 것은 순수 함수다. 시설은 상태와 타이머를 가진 엔티티이고 `update(dt)`가 순수하다. 화면과 마우스 좌표 변환만 `scenes/play.py`에 있다.

**Tech Stack:** pygame-ce, Python >= 3.10, pytest + pytest-cov, ruff, mypy (strict)

**Spec:** `docs/superpowers/specs/2026-08-29-world-rebuild-concept-design.md`

**선행:** 1~4단계, 5a 완료

## Global Constraints

- 로직은 순수 `update(dt, ...)`, 렌더링은 `draw(surface)`. `pygame.display` / 이벤트 펌프 / `pygame.quit`는 `core/app.py`에만.
- `config.py`는 pygame을 import하지 않는다.
- 고정 타임스텝 `FIXED_DT = 1/60`. 난수는 주입한다.
- TDD: 실패하는 테스트 → 최소 구현 → 리팩터.
- 명령어: `./.venv/Scripts/python.exe -m pytest` · `-m ruff check . && -m ruff format --check .` · `-m mypy`
- 각 작업의 마지막 단계는 커밋이다.

## 이 단계의 결정

**제작 메뉴는 하나다.** `C`로 열린다. 땅에 물건을 떨궈 뭉치는 방식은 쓰지 않는다.

**보이는 목록이 서 있는 자리에 따라 달라진다.**

```
아무 데서나        나무 도구 · 제작대
제작대 근처        용광로 · 화덕 · 돌~금 도구 · 배낭 · 고급 제작대
고급 제작대 근처   고로 · 황동/강철 도구
```

그래서 "어디서 만들 수 있나"가 곧 진행도가 된다. 메뉴를 열 때마다 새로운 줄이 늘어나는 것이 보상이다.

**시설은 결계 안에만 지을 수 있다.** 스펙의 귀환 이유 세 가지 중 하나다.

**주조에는 시간이 걸린다.** 넣어두고 나갔다가 돌아와서 꺼낸다. 이것이 결계 안을 "들르는 곳"이 아니라 **운영하는 곳**으로 만든다.

**고로는 결계 반경을 요구한다.** 자리를 많이 차지하기 때문이고, 그래서 최고 등급인 강철이 코어 레벨에 묶인다.

## 사슬이 맞물리는 지점

> 나무 → 나무 도구 → 제작대 → 용광로 → 구리·철 주괴 → 더 나은 곡괭이 → 아연 →
> 황동 → 고급 제작대 → (결계를 넓히고) → 고로 → 숯 + 철 → 강철

고로를 지으려면 황동이 필요하고 황동은 용광로에서 나온다. 결계 반경 요구까지 걸리므로 강철은 **코어를 올리지 않으면 도달할 수 없다**.

## 범위 밖

- **무기 등급** — 등급표는 이미 있지만 무기에 붙이는 것은 전투 차례에.
- **스테미나** — 생존 절 주제. 따로.
- **요리** — 화덕이 고기를 굽는 것은 생존 차례에. 여기서는 숯만 굽는다.
- **습격**(6단계), **마법**(7단계).

## File Structure

| 파일 | 책임 |
|---|---|
| `items/recipes.py` | **신규** 조합법 표 |
| `systems/crafting.py` | **신규** 무엇을 만들 수 있는지, 만들면 무엇이 오가는지. 순수 |
| `entities/station.py` | **신규** 배치된 시설. 상태와 타이머 |
| `items/item_kinds.py` | 시설 아이템 4종 + 고급 제작대 |
| `scenes/play.py` | 제작 메뉴, 배치, 시설 갱신·렌더링 |
| `config.py` | 주조 시간, 배치 규칙, 고로의 결계 요구 |

---

### Task 1: 조합법 표

**Files:** Create `items/recipes.py` · Modify `items/item_kinds.py` · Test `tests/test_recipes.py`(신규)

**Produces:**
- 카탈로그에 시설 아이템: `BENCH`("제작대"), `SMELTER`("용광로"), `HEARTH`("화덕"), `BLAST_FURNACE`("고로"), `FINE_BENCH`("고급 제작대") — 전부 스택 1
- 도구 아이템: 등급×갈래로 `WOOD_PICK` … `STEEL_PICK`, `WOOD_AXE` … `STEEL_AXE`
- `Station` 상수: `NONE`, `BENCH_S`, `FINE_S` — 조합법이 요구하는 자리
- `Recipe(output: ItemKind, count: int, inputs: tuple[tuple[ItemKind, int], ...], station: str, seconds: float)`
- `RECIPES: tuple[Recipe, ...]`
- `recipes_at(station) -> tuple[Recipe, ...]`

**핵심 — 테스트로 못박을 것:**
- 모든 재료와 산출물이 실제 카탈로그 행이다
- 아무 데서나 되는 것은 나무 도구와 제작대뿐이다
- 고로는 고급 제작대를 요구하고, 고급 제작대는 제작대를 요구한다
- 황동은 용광로, 강철은 고로에서만 나온다
- **순환이 없다** — 어떤 조합법도 자기 자신을 재료로 요구하지 않고, 아무 데서나 되는 것에서 출발해 모든 조합법에 도달할 수 있다 (도달 가능성 검사)

도달 가능성 검사가 이 표에서 가장 중요한 테스트다. 사슬이 한 군데만 끊겨도 게임이 막히는데, 표를 눈으로 읽어서는 알 수 없다.

- [ ] **Step 1:** `tests/test_recipes.py` — 위 항목 전부, 특히 도달 가능성
- [ ] **Step 2:** 실패 확인 · **Step 3:** 구현 · **Step 4:** 검증 · **Step 5:** 커밋 `feat(items): add the recipe table`

---

### Task 2: 도구가 아이템이 된다

**Files:** Modify `items/tools.py`, `inventory/hotbar.py`, `scenes/play.py` · Test `tests/test_tools.py`, `test_hotbar.py`, `test_play_scene.py`

지금 핫바는 `MiningTool` **객체**를 슬롯에 담는다. 제작이 들어오면 도구는 **아이템**이다. 이 다리를 먼저 놓지 않으면 Task 3에서 곡괭이를 만들어도 네 작업 동안 쓸 수 없는 죽은 아이템이 된다.

**Produces:** `tools.tool_for(kind) -> MiningTool | WeaponTool | None` — 도구 아이템 하나가 어떤 도구인지. `Hotbar.active_tool`이 `Stack`을 들고 있으면 그 종류의 도구를 답한다.

그러면 핫바는 **아이템만** 담고 도구는 아이템에서 파생된다. 슬롯에 도구 객체를 직접 넣는 방식이 사라지고, 죽음·격자·제작이 전부 같은 것(아이템)을 다루게 된다.

- [ ] **Step 1:** 테스트 — 나무 곡괭이 아이템을 든 핫바의 `active_tool`이 나무 곡괭이다, 재료 스택은 `active_tool`이 `None`이다, 등급마다 맞는 도구가 나온다
- [ ] **Step 2~5:** 실패 확인 · 구현 · 씬의 시작 슬롯을 아이템으로 · 검증 · 커밋 `refactor(items): let a tool be an item the hotbar carries`

---

### Task 3: 무엇을 만들 수 있는가

**Files:** Create `systems/crafting.py` · Test `tests/test_crafting.py`(신규)

**Produces:**
- `crafting.available(station, backpack, hotbar) -> list[tuple[Recipe, bool]]` — 그 자리에서 보이는 조합법과, 지금 재료가 되는지
- `crafting.craft(recipe, backpack, hotbar) -> ItemKind | None` — 재료를 빼고 산출물을 넣는다. 재료가 모자라거나 넣을 자리가 없으면 아무것도 하지 않고 `None`

**핵심:**
- 재료는 **배낭과 핫바 둘 다에서** 센다 (`_carried`와 같은 규칙). 배낭이 없어도 제작이 되어야 맨손 시작이 굴러간다
- 재료를 뺄 자리가 있는지 **먼저 확인하고** 뺀다. 절반만 빼고 실패하면 재료가 증발한다
- 산출물이 들어갈 자리가 없으면 **아예 만들지 않는다** — 만들고 나서 바닥에 떨구면 5분 시계가 붙는 짐이 된다

- [ ] **Step 1:** 테스트 — 재료가 있으면 만들 수 있다고 답한다, 모자라면 아니라고 답한다, 만들면 재료가 빠지고 산출물이 들어온다, 산출물 자리가 없으면 재료가 그대로 남는다, 배낭 없이 핫바만으로도 된다, 다른 자리의 조합법은 목록에 없다
- [ ] **Step 2~5:** 실패 확인 · 구현 · 검증 · 커밋 `feat(systems): work out what can be crafted where`

---

### Task 4: 시설 — 짓고 놓기

**Files:** Create `entities/station.py` · Modify `scenes/play.py`, `config.py` · Test `tests/test_station.py`(신규), `test_play_scene.py`

**Produces:**
- `Station(pos, kind, ...)` — 배치된 시설
- `config.STATION_RADIUS`, `config.STATION_REACH`(이 안에 서면 그 시설의 조합법이 열린다), `config.BLAST_FURNACE_MIN_WARD`
- `PlayScene.stations: list[Station]`
- 배치: 시설 아이템을 핫바에서 골라 든 채 **결계 안**을 클릭하면 놓인다
- `station_at(pos) -> str` — 지금 서 있는 자리에서 열리는 가장 높은 등급의 자리

**핵심 규칙 — 테스트로 못박을 것:**
- **결계 밖에는 못 놓는다**, 점화 전에는 결계가 없으므로 아무 데도 못 놓는다
- **시설끼리 겹치지 않는다**
- **고로는 결계 반경이 `BLAST_FURNACE_MIN_WARD` 이상일 때만** 놓인다 → 강철이 코어 레벨에 묶인다
- 놓으면 아이템이 소모된다. 못 놓으면 소모되지 않는다
- `station_at`은 가장 높은 등급을 답한다 — 제작대와 고급 제작대 사이에 서 있으면 고급 쪽 목록이 나와야 한다

`BLAST_FURNACE_MIN_WARD`는 결계 사다리(4,000 → 12,000, 35레벨 완성)에서 **중간쯤**으로 잡는다. 대략 7,000이면 20레벨 근처다 — 보스 하나는 잡아야 닿는다.

- [ ] **Step 1~6:** 테스트 · 실패 확인 · 구현 · 배선 · 검증 · 커밋 `feat(world): build stations inside the ward`

---

### Task 5: 시간이 걸리는 주조

**Files:** Modify `entities/station.py`, `scenes/play.py`, `items/recipes.py` · Test `tests/test_station.py`

**Produces:** 용광로·화덕·고로가 **일감**을 갖는다. 재료를 넣으면 `seconds`만큼 돌고, 끝나면 산출물이 시설 안에 쌓인다. 플레이어가 와서 꺼낸다

- `Station.job: Recipe | None`, `Station.remaining: float`, `Station.output: Container`
- `Station.update(dt)` — 순수. 일감이 끝나면 `output`에 넣고 비운다
- `Station.start(recipe) -> bool`, `Station.collect() -> list[tuple[ItemKind, int]]`

**핵심:**
- 시설의 `update`는 플레이어가 곁에 없어도 돈다. 그게 요점이다 — 넣어두고 나갔다 온다
- 죽어 있는 동안에도 돈다 (4단계에서 세운 규칙과 같다)
- `output`이 차면 일감을 시작하지 않는다. 안 그러면 산출물이 사라진다
- 제작대와 고급 제작대는 **즉시**다 (`seconds == 0`). 도구를 만드는 데 기다릴 이유가 없다

- [ ] **Step 1~5:** 테스트 · 구현 · 배선 · 검증 · 커밋 `feat(world): make smelting take time`

---

### Task 6: 제작 메뉴 화면

**Files:** Modify `scenes/play.py`, `config.py` · Test `tests/test_play_scene.py`

**Produces:** `C`로 열리는 화면. 지금 자리에서 만들 수 있는 것들이 줄로 뜨고, 재료가 되는 것은 밝게, 안 되는 것은 어둡게. 클릭하면 만들어진다

격자 화면(`I`)과 같은 규칙을 따른다 — 열려 있으면 세상은 멈추지만 시계는 돈다. 둘이 동시에 열리지 않는다.

- [ ] **Step 1~5:** 테스트 · 구현 · 검증 · 커밋 `feat(play): add the crafting menu`

---

### Task 7: 임시 조치를 걷어낸다

**Files:** Modify `scenes/play.py`, `items/recipes.py` · Test `tests/test_play_scene.py`

- **배낭 조합법**을 넣고, 세계에 떨어뜨려 둔 임시 `WORN_PACK` 노드를 **지운다**
- **시작 도구를 걷어낸다.** 대신 스폰 주변에 **나무**를 몇 그루 세워두고, 맨손으로 나무를 벨 수 있게 한다 — 나무만은 도구 없이 되게 하는 것이 부트스트랩의 정직한 답이다

  (5a에서는 도끼를 쥐여줬다. 이제 제작이 있으므로, 맨손으로 나무를 주워 나무 도끼를 만드는 것이 첫 수가 된다.)
- [ ] **Step 1~5:** 테스트 · 조합법 · 임시 조치 제거 · 검증 · 커밋 `feat(world): craft the first axe instead of being handed one`

---

## 이 계획이 끝나면

맨손으로 나무를 베어 도끼를 만들고, 제작대를 세우고, 용광로에 광석을 넣고 나갔다 돌아와 주괴를 꺼내고, 더 나은 곡괭이로 더 깊이 들어간다. 고로는 결계를 넓히기 전에는 지을 수 없다.

**남는 것:** 화덕은 숯만 굽는다(요리는 생존 차례), 무기는 아직 등급이 없다, 스테미나는 없다.
