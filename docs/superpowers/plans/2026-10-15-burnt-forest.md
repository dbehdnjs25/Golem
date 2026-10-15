# 화산지대를 불탄 숲으로 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 첫 바이옴을 화산지대에서 **불탄 숲**으로 바꾼다. 불탄 나무는 숯 대신 쓰고, 용암 웅덩이가 자연히 생기고, 웅덩이 둘레에만 흑요석이 박힌 돌이 선다.

**Architecture:** 웅덩이는 세계가 씨앗에서 만드는 고정 지형. 피해는 순수 함수. 렌더링만 `scenes/play.py`에.

**Tech Stack:** pygame-ce, Python >= 3.10, pytest + pytest-cov, ruff, mypy (strict)

**선행:** 1~7단계 완료

## Global Constraints

- 로직은 순수 `update(dt, ...)`, 렌더링은 `draw(surface)`.
- `config.py`는 pygame을 import하지 않는다.
- 난수는 주입한다. 같은 씨앗은 같은 세계.
- TDD: 실패하는 테스트 → 최소 구현 → 리팩터.
- 명령어: `./.venv/Scripts/python.exe -m pytest` · `-m ruff check . && -m ruff format --check .` · `-m mypy`
- 각 작업의 마지막 단계는 커밋이다.

## 이 바꿈이 고치는 것

**흑요석의 출처가 말이 안 됐다.** 화산 유리가 바이옴 전역에 12% 확률로 깔려 있었다. 이제 **용암 웅덩이 둘레에만** 박힌 돌이 서므로, 흑요석을 캔다는 것이 곧 **위험 옆에 서는 일**이 된다. 상급 지팡이와 탐지기가 그 대가로 사기로 한 것이 비로소 생긴다.

**바이옴이 가장 쉬운 자리에 있는 이유가 되살아난다.** 스펙은 화산지대를 첫째로 둔 이유를 "용암은 눈에 보이고 가만히 있는 위험 — 읽기 가장 쉬운 종류"라고 적었다. 그런데 지금까지 용암이 없었다. 웅덩이가 들어오면 그 설명이 다시 참이 된다.

**불탄 나무는 숯으로 가는 지름길이다.** 보통 숯은 화덕에서 나무 3 → 숯 2, 12초가 걸린다. 불탄 나무는 이미 반쯤 탄 것이라 **맨손으로 1:1, 즉시**. 강철이 숯을 먹으니, 불탄 숲에 다녀오는 것이 제강을 앞당긴다.

## 범위 밖

- 다른 네 바이옴의 지형지물 — 이 바꿈은 첫째 바이옴만 다룬다
- 보스와 사원(8단계), 엔딩(9단계)

## File Structure

| 파일 | 책임 |
|---|---|
| `world/biomes.py` | 이름·색·재료 |
| `world/lava.py` | **신규** 웅덩이 배치, 용암 안인지 판정 |
| `entities/lava.py` | **신규** 웅덩이 하나 |
| `items/item_kinds.py`, `recipes.py` | 불탄 나무, 흑요석 돌, 숯 전환 |
| `world/resources.py` | 불탄 숲의 나무는 불탄 나무 |
| `systems/survival.py` | 용암 피해 |
| `scenes/play.py` | 배선과 그리기 |

---

### Task 1: 이름 바꾸기

**Files:** Modify `world/biomes.py`, `items/glyphs.py`, `items/item_kinds.py`, `systems/detector.py`, 관련 테스트, 스펙 문서

**Produces:**
- `VOLCANO` → `BURNT_FOREST`, key `"burnt_forest"`, 이름 "불탄 숲"
- 색은 타버린 숲으로 — 붉은 돌이 아니라 그을린 갈색
- 탐지기 "화산 탐지기" → "불탄 숲 탐지기"
- 그림 이름 `용암심` → 숲에 맞는 것으로. `불씨`·`화염`은 그대로 (불 속성은 안 바뀐다)
- 스펙의 「다섯 바이옴」 표와 난이도 설명

**핵심:** 키를 바꾸는 것은 지금이 마지막 기회다. 세이브가 생기면 못 바꾼다.

- [x] **Step 1~5:** 테스트 · 구현 · 검증 · 커밋 `refactor(world): turn the volcano into a burnt forest`

---

### Task 2: 불탄 나무

**Files:** Modify `items/item_kinds.py`, `recipes.py`, `world/resources.py`, `items/grades.py` · Test `test_world_resources.py`, `test_recipes.py`

**Produces:**
- `CHARRED_WOOD`("불탄 나무") — 불탄 숲의 `material`
- 불탄 숲에서 **나무 노드가 불탄 나무를 준다** (보통 나무가 아니라)
- `Recipe(CHARCOAL, 1, ((CHARRED_WOOD, 1),), NOWHERE, 0.0)` — 맨손, 즉시
- 도끼로 벤다 (보통 나무와 같은 등급)

**핵심 — 테스트로 못박을 것:**
- 불탄 숲에서는 보통 `WOOD`가 **안 나온다** — 탄 숲인데 멀쩡한 통나무가 나오면 말이 안 된다
- 다른 바이옴에서는 불탄 나무가 안 나온다
- 숯 전환이 화덕 경로보다 싸다 (그게 다녀올 이유다)

- [x] **Step 1~5:** 테스트 · 구현 · 검증 · 커밋 `feat(world): burn the forest's trees and let them stand in for charcoal`

---

### Task 3: 용암 웅덩이

**Files:** Create `entities/lava.py`, `world/lava.py` · Modify `systems/survival.py`, `scenes/play.py`, `config.py` · Test `test_lava.py`(신규)

**Produces:**
- `LavaPool(pos, radius)` — 가만히 있는 지형
- `place_pools(world, rng)` — 불탄 숲 안에만, 씨앗에서 재현 가능하게
- `lava.burns(pos, pools) -> bool`
- 용암 안에 있으면 초당 피해. 결계도 못 막는다 (지형이지 적이 아니다)

**핵심 — 테스트로 못박을 것:**
- 웅덩이는 **불탄 숲 안에만** 생긴다
- 같은 씨앗은 같은 웅덩이
- 겹치지 않는다
- 걸어 들어가면 아프고, 나오면 멈춘다
- **피해가 즉사가 아니다** — 보이는 위험은 건널 수도 있어야 선택이 된다

- [x] **Step 1~6:** 테스트 · 구현 · 배선 · 손으로 확인 · 검증 · 커밋 `feat(world): pour lava pools into the burnt forest`

---

### Task 4: 흑요석이 박힌 돌

**Files:** Modify `items/item_kinds.py`, `world/lava.py`, `systems/spawner.py`, `world/resources.py` · Test `test_lava.py`, `test_recipes.py`

**Produces:**
- `OBSIDIAN_STONE`("흑요석 박힌 돌") — 노드로 서고, 캐면 흑요석
- 웅덩이 **둘레 띠에만** 선다
- 흑요석은 더 이상 `node_at`에서 안 나온다
- 조합법 도달성 테스트가 이 경로를 알아야 한다

**핵심:** 흑요석을 캐려면 용암 옆에 서야 한다. 그게 이 바꿈의 전부다.

**테스트로 못박을 것:**
- 흑요석 돌은 웅덩이 가까이에만 있다
- 용암 **안에는** 안 선다 (닿을 수 없는 광맥은 없는 것과 같다)
- 평범한 `node_at`은 흑요석을 절대 안 준다
- 상급 지팡이가 여전히 도달 가능하다

- [x] **Step 1~5:** 테스트 · 구현 · 검증 · 커밋 `feat(world): put the obsidian where the lava is`

---

### Task 5: 보이게

**Files:** Modify `scenes/play.py`, `config.py` · Test `test_play_scene.py`

- 용암 웅덩이 — 밝게, 테두리로 경계가 분명하게. **밟기 전에 보여야** 한다
- 용암에 서 있는 동안 화면에 표시
- 흑요석 돌이 보통 돌과 구분되게

- [x] **Step 1~5:** 테스트 · 구현 · 손으로 확인 · 검증 · 커밋 `feat(play): show the lava before it is stepped in`

---

## 이 계획이 끝나면

첫 바이옴이 탄 숲이고, 그 안에 용암 웅덩이가 고여 있다. 나무는 숯 대신 쓰이고, 흑요석은 웅덩이 옆에서만 나온다.

---

## 실제로 끝난 뒤의 기록

**색이 늪지와 겹쳤다.** 탄 숲이니 어두운 회갈색이 맞을 것 같았는데, 늪지의 어두운 녹색과
RGB 거리 33밖에 안 떨어져서 지도에서 두 구역이 하나로 보였다. 색 충돌 테스트가 잡았다
(기준 55). 그을린 적갈색으로 옮겼다 — **구분 못 하는 바이옴은 피할 수도 없는 바이옴이다.**

**불탄 나무가 두 번 굴려졌다.** 나무 굴림(34%)과 바이옴 재료 굴림(12%) 양쪽에서 나와
40%가 됐다. **나무가 이미 주는 것은 따로 뿌리지 않는다**는 규칙을 넣어 풀었다.

**숯 전환을 맨손에 두려다 물렀다.** 5단계부터 "맨손 목록은 부트스트랩이고 그 이상은 아니다"를
지키는 테스트가 있었다. 아무것도 없는 사람에게 숯 얘기를 할 이유가 없다. 화덕으로 옮기고
대신 3초로 줄였다 (보통은 12초).

**흑요석을 옮기자 조합법이 끊겼다.** `Biome.material`에서 빼는 순간 상급 지팡이가 도달
불가가 됐고 도달성 테스트가 즉시 잡았다. 그 테스트가 이번에도 제 몫을 했다.

**새로 생긴 두 가지 개념** — 둘 다 흑요석 때문에 필요해졌고, 둘 다 일반 규칙으로 썼다:
- **노드가 자기 아닌 것을 준다** (`yield_of`). 흑요석 박힌 돌이 유일한 예다
- **노드가 지형일 수 있다** (`Fragment.fixed`). 스포너가 자기 개체수만 세게 해서, 용암밭이
  맵 전체의 광맥을 굶기지 않는다

**용암 크기가 벽이냐 건널목이냐를 정한다.** 초당 26이라 가장 작은 웅덩이(반지름 260)는
68 피해로 건널 수 있고, 가장 큰 것(620)은 161이라 못 건넌다. 의도한 건 아닌데 결과가 좋다.

**흑요석 돌이 평범한 조약돌로 보였다.** 두 번째 사다리의 관문인데. 박힌 것이 비치도록
안쪽에 밝은 점을 찍었다 — 규칙은 "자기 아닌 것을 가진 노드는 그걸 보여준다"로 일반화했다.

**용암에 서 있는 게 화면에 안 보였다.** 웅덩이는 보이는데 그 안에 있다는 사실이 안 보여서,
HP가 줄어드는 이유가 화면에 없었다. 서 있는 동안 화면이 달아오르게 했다.
