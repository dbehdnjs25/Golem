# 5a단계: 자원과 도구 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 도구에 등급을 주고, 등급이 자격이자 속도가 되게 한다. 나무를 베는 대상으로 만들어 맨 아래 칸을 연다.

**Architecture:** 등급표와 요구표는 `items/item_kinds.py`·`world/biomes.py`와 같은 frozen dataclass 카탈로그다 — 데이터는 표에, 행동은 `systems/`에. 채굴이 등급을 확인하는 것은 순수 함수이므로 헤드리스로 테스트된다.

**Tech Stack:** pygame-ce, Python >= 3.10, pytest + pytest-cov, ruff, mypy (strict)

**Spec:** `docs/superpowers/specs/2026-08-29-world-rebuild-concept-design.md`

**선행:** 1~4단계 완료

## Global Constraints

- 로직은 순수 `update(dt, ...)`, 렌더링은 `draw(surface)`. `pygame.display` / 이벤트 펌프 / `pygame.quit`는 `core/app.py`에만.
- `config.py`는 pygame을 import하지 않는다.
- 고정 타임스텝 `FIXED_DT = 1/60`. 난수는 주입한다.
- TDD: 실패하는 테스트 → 최소 구현 → 리팩터.
- 명령어: `./.venv/Scripts/python.exe -m pytest` · `-m ruff check . && -m ruff format --check .` · `-m mypy`
- 각 작업의 마지막 단계는 커밋이다.

## 정한 것

```
도구 등급   나무 → 돌 → 구리 → 철 → 금 → 황동 → 강철   (7등급)

필요 등급   돌 · 구리      나무
            철             구리
            금 · 아연      철
            바이옴 재료    금
```

**등급은 자격이자 속도다.** 모자라면 아예 손을 못 대고, 넘으면 캐는 속도가 붙는다. 거리(위험)와 등급(자격)이 두 축으로 맞물려, 멀리 가도 등급이 없으면 보고만 오게 된다.

**도구에는 갈래(family)가 있다.** 곡괭이로 나무를 벨 수 없고 도끼로 광맥을 캘 수 없다. 나무에는 등급을 따지지 않는다 — 등급 축을 둘로 늘리면 복잡해지기만 한다.

## 범위 밖 (5b와 그 이후)

- **제작 전부** — 땅바닥 제작, 제작대, 고급 제작대, 시설 배치, 주조. 5b.
- **배낭 제작** — 5b. 그때까지 세계에 떨어뜨려 둔 임시 배낭으로 굴러간다.
- **무기 등급** — 등급표는 무기도 쓸 수 있게 만들지만, 무기에 붙이는 것은 전투 차례에.
- **스테미나** — 채집이 스테미나를 먹는다는 것은 스펙의 생존 절 주제다. 따로 한다.

## File Structure

| 파일 | 책임 |
|---|---|
| `items/grades.py` | **신규** 등급표와 도구 갈래, 무엇이 무엇을 요구하는지 |
| `items/tools.py` | 도구가 등급과 갈래를 갖는다 |
| `entities/fragment.py` | 노드가 무엇을 요구하는지는 종류에서 나온다 |
| `systems/mining.py` | 자격을 확인하고, 속도에 등급을 반영한다 |
| `systems/spawner.py` | 나무도 뿌린다 |
| `scenes/play.py` | 시작 도구, 노드 그리기 |

---

### Task 1: 등급표

**Files:** Create `items/grades.py` · Test `tests/test_grades.py`(신규)

**Produces:**
- `Grade(key, name, rank, speed)` — frozen. `speed`는 채굴 속도 배율
- `GRADES: tuple[Grade, ...]` — 나무부터 강철까지 7개, `rank` 오름차순
- `WOOD_G, STONE_G, COPPER_G, IRON_G, GOLD_G, BRASS_G, STEEL_G`
- 갈래 상수 `PICKAXE`, `AXE`
- `Need(family: str, grade: Grade)` — 한 노드를 캐는 자격
- `NEEDS: dict[ItemKind, Need]` — 무엇이 무엇을 요구하는지
- `need_for(kind) -> Need` — 표에 없으면 맨손으로도 되는 것(기본값)

**핵심 동작 — 테스트로 못박을 것:**
- 등급은 `rank` 순이고 `speed`도 단조 증가한다
- 표의 모든 열쇠가 실제 카탈로그 행이다
- 돌·구리는 나무, 철은 구리, 금·아연은 철, 바이옴 재료는 금을 요구한다
- 나무는 도끼를 요구하고 등급은 맨 아래다
- 광맥은 전부 곡괭이를 요구한다

- [ ] **Step 1:** `tests/test_grades.py`를 쓴다

```python
from game.items import grades
from game.items.grades import AXE, GRADES, PICKAXE
from game.items.item_kinds import (
    COPPER_ORE, GOLD_ORE, IRON_ORE, ITEM_KINDS, OBSIDIAN, STONE, WOOD, ZINC_ORE,
)


def test_the_ladder_runs_from_wood_to_steel():
    assert [g.key for g in GRADES] == [
        "wood", "stone", "copper", "iron", "gold", "brass", "steel",
    ]


def test_rank_and_speed_both_climb_with_the_ladder():
    assert [g.rank for g in GRADES] == list(range(len(GRADES)))
    speeds = [g.speed for g in GRADES]
    assert speeds == sorted(speeds)
    assert len(set(speeds)) == len(speeds)  # every step is worth taking


def test_stone_and_copper_only_need_a_wooden_pick():
    # This is what lets the opening work bare-handed: wood makes the first
    # tool, and the first tool opens the first two ores.
    for kind in (STONE, COPPER_ORE):
        need = grades.need_for(kind)
        assert need.family == PICKAXE
        assert need.grade is grades.WOOD_G


def test_the_gates_climb_with_the_ore():
    assert grades.need_for(IRON_ORE).grade is grades.COPPER_G
    assert grades.need_for(GOLD_ORE).grade is grades.IRON_G
    assert grades.need_for(ZINC_ORE).grade is grades.IRON_G


def test_biome_materials_are_what_gold_is_for():
    # Ore stops at gold, so without this the top three grades would open
    # nothing at all and be a speed bonus dressed as a ladder.
    assert grades.need_for(OBSIDIAN).grade is grades.GOLD_G


def test_wood_wants_an_axe_at_the_bottom_of_the_ladder():
    need = grades.need_for(WOOD)
    assert need.family == AXE
    assert need.grade is GRADES[0]


def test_every_ore_wants_a_pickaxe():
    for kind, need in grades.NEEDS.items():
        if kind is not WOOD:
            assert need.family == PICKAXE


def test_the_table_only_names_real_catalogue_rows():
    for kind in grades.NEEDS:
        assert ITEM_KINDS[kind.key] is kind


def test_something_not_in_the_table_needs_nothing_special():
    from game.items.item_kinds import POTION

    assert grades.need_for(POTION).grade is GRADES[0]
```

- [ ] **Step 2:** 실패 확인 (`ModuleNotFoundError`)
- [ ] **Step 3:** `items/grades.py` 구현. 표는 `NEEDS`에 명시적으로 쓰고, 없는 것은 `need_for`가 맨 아래 등급의 곡괭이를 답한다
- [ ] **Step 4:** 검증 4종 · **Step 5:** 커밋 `feat(items): add the tool grade ladder and what each node needs`

---

### Task 2: 도구가 등급과 갈래를 갖는다

**Files:** Modify `items/tools.py`, `scenes/play.py` · Test `tests/test_tools.py`, `test_hotbar.py`

**Produces:** `MiningTool(family, grade, range)` — 프로퍼티 `dps`(`config.MINING_DPS * grade.speed`), `name`("구리 곡괭이"). `tools.pickaxe(grade)`, `tools.axe(grade)` 편의 생성자

`MiningTool`의 `dps`와 `name`이 필드에서 프로퍼티로 바뀐다. `mining`은 `active_tool.dps`를 그대로 읽으므로 호출부는 안 바뀐다.

- [ ] **Step 1:** 테스트 — 기본은 나무 곡괭이, 등급이 오르면 `dps`가 오른다, 이름이 등급과 갈래를 담는다, 도끼는 갈래가 다르다, frozen이다
- [ ] **Step 2:** 실패 확인 · **Step 3:** 구현
- [ ] **Step 4:** 씬의 시작 도구를 바꾼다 — 슬롯 0에 **나무 곡괭이**, 슬롯 1에 **나무 도끼**, 슬롯 2에 무기

  도끼를 쥐여주는 이유: 나무가 도끼를 요구하는데 도끼를 만들려면 나무가 필요하다.
  둘 다 없으면 첫 수가 없다. 5b의 땅바닥 제작이 들어오면 시작 도구를 걷어내고,
  흩뿌려진 나뭇가지를 주워 첫 도구를 만드는 진짜 부트스트랩으로 바꾼다 —
  그때까지는 쥐여주는 것이 정직하다.
- [ ] **Step 5:** 검증 · **Step 6:** 커밋 `feat(items): give tools a grade and a family`

---

### Task 3: 자격을 확인하는 채굴

**Files:** Modify `systems/mining.py` · Test `tests/test_mining.py`

**Produces:** 상태 상수 `WRONG_TOOL`, `TOO_HARD` 추가. `update_mining`이 노드의 `Need`를 확인하고 자격이 없으면 **한 대도 때리지 않고** 돌아온다

**핵심:** 자격 확인은 데미지보다 **먼저**다. 못 캐는 광맥을 반쯤 깎아놓고 막히면 그 노드는 망가진 채 남는다.

- [ ] **Step 1:** 테스트

```python
def test_a_wooden_pick_cannot_touch_iron():
    node = Fragment(pos=..., kind=IRON_ORE)
    status, _ = mining.update_mining(1.0, active_tool=tools.pickaxe(grades.WOOD_G), ...)
    assert status == mining.TOO_HARD
    assert node.hp == config.FRAGMENT_HP  # not even scratched


def test_a_copper_pick_opens_iron():
    ...
    assert status in (mining.MINING, mining.COLLECTED)


def test_an_axe_cannot_mine_ore():
    ...
    assert status == mining.WRONG_TOOL


def test_a_pick_cannot_chop_wood():
    ...
    assert status == mining.WRONG_TOOL


def test_a_better_pick_digs_faster():
    # Same node, same dt, two grades -- the higher one takes more off.
    ...
```

- [ ] **Step 2:** 실패 확인 · **Step 3:** 구현 · **Step 4:** 검증 · **Step 5:** 커밋 `feat(mining): gate nodes behind tool grade and family`

---

### Task 4: 나무

**Files:** Modify `systems/spawner.py`, `world/resources.py`, `scenes/play.py`, `config.py` · Test `tests/test_world_resources.py`, `test_spawner.py`, `test_play_scene.py`

**Produces:** 스포너가 광맥과 **나무**를 함께 뿌린다. 나무는 거리와 무관하게 초원 전역에 나되, 코어에서 멀수록 촘촘하다(스펙의 "멀수록 나무 분포가 늘고")

나무는 `Fragment(kind=WOOD)`다 — 노드가 무엇을 요구하는지는 종류에서 나오므로, 나무를 위해 새 엔티티를 만들 필요가 없다. 화면에서는 색이 다르게 보인다.

`resources.ore_at`은 광맥만 정한다. 나무는 별도 확률로 섞는다 — 나무가 광물 표에 끼면 "깊은 곳에서 나무가 덜 난다"는 이상한 결과가 나온다.

- [ ] **Step 1:** 테스트 — 스폰 결과에 나무가 섞인다, 나무 비율이 거리를 따라 오르지 않고 일정하다(또는 정한 대로), 나무는 도끼로만 베인다
- [ ] **Step 2~4:** 구현·검증·커밋 `feat(world): scatter trees alongside the ore`

---

### Task 5: 못 캘 때 보이게

**Files:** Modify `scenes/play.py` · Test `tests/test_play_scene.py`

자격이 없어 못 캐는 것이 **화면에서 읽혀야** 한다. 아무 일도 안 일어나는 것과 구분이 안 되면 플레이어는 버그로 여긴다.

- 노드를 종류 색으로 그린다 (`kind.color`) — 지금은 전부 같은 파랑이다
- 조준한 노드가 지금 든 도구로 **못 캐는 것이면 붉은 테두리**를 두른다
- 커서 아래 노드를 찾는 것은 `mining._pick_target`과 같은 규칙이어야 한다 — 씬이 따로 계산하면 둘이 어긋난다. `mining`에 조준 대상을 돌려주는 함수를 내놓는다

- [ ] **Step 1~5:** 테스트·구현·검증·커밋 `feat(play): show which nodes the current tool cannot take`

---

## 이 계획이 끝나면

도구에 등급이 생기고, 등급이 자격과 속도를 동시에 결정하고, 나무가 베는 대상이 되고, 못 캐는 노드가 눈에 보인다.

**만드는 방법은 아직 없다.** 나무 곡괭이와 나무 도끼를 쥐고 시작한다 — 5b의 땅바닥 제작이 들어오면 그 둘을 걷어내고, 흩뿌려진 나뭇가지를 주워 만드는 진짜 시작으로 바꾼다.
