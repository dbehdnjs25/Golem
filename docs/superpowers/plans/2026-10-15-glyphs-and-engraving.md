# 7단계: 마법 — 그림을 찾아 새긴다 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 바이옴을 돌아다닐 이유를 만든다. 세계에 흩어진 구조물에서 그림을 배우고, 소모되는 새김 도구로 장비에 새기고, 지팡이로 쏜다. 탐지기가 사원 방향을 알려준다.

**Architecture:** 그림은 frozen dataclass 카탈로그. 배운 것은 집합, 새긴 것은 장비에 붙은 짧은 목록. 효과 계산은 순수 함수. 렌더링만 `scenes/play.py`에.

**Tech Stack:** pygame-ce, Python >= 3.10, pytest + pytest-cov, ruff, mypy (strict)

**Spec:** `docs/superpowers/specs/2026-08-29-world-rebuild-concept-design.md` 「마법 — 그림을 찾아 새긴다」

**선행:** 1~6단계 완료

## Global Constraints

- 로직은 순수 `update(dt, ...)`, 렌더링은 `draw(surface)`. `pygame.display` / 이벤트 펌프 / `pygame.quit`는 `core/app.py`에만.
- `config.py`는 pygame을 import하지 않는다.
- 고정 타임스텝 `FIXED_DT = 1/60`. 난수는 주입한다.
- TDD: 실패하는 테스트 → 최소 구현 → 리팩터.
- 명령어: `./.venv/Scripts/python.exe -m pytest` · `-m ruff check . && -m ruff format --check .` · `-m mypy`
- 각 작업의 마지막 단계는 커밋이다.

## 이 단계의 결정

**사다리가 둘이고 섞이지 않는다.** 등급(초원 광물)은 *무엇을 캘 수 있나*를 정하고, 속성(바이옴 재료)은 *무엇을 쏠 수 있나*를 정한다. 강철 곡괭이가 불을 뿜지 않고, 불 그림이 금 광맥을 열지 않는다.

**상성표는 없다.** 스펙이 명시적으로 거부한다 — 바이옴을 도는 이유는 숨은 배수표가 아니라 **눈에 보이는 수집품**이다. 그래서 속성은 세기와 멋이지 가위바위보가 아니다. 밸런싱할 표가 하나 줄어든다.

**칸은 장비를 더 좋게 만들어 늘린다.** 스펙이 "업그레이드로 늘린다"고만 하고 방법은 안 정했다. 등급에 묶으면 두 사다리가 섞이므로 **바이옴 재료로 더 좋은 장비를 만드는 쪽**으로 간다: 지팡이 1칸 → 상급 2칸 → 최상급 3칸. 기존 조합법 체계를 그대로 쓰고, 칸은 끝까지 바이옴 사다리에 남는다.

**새김 도구가 3회면 부서진다.** 이게 이 단계의 유일한 긴장이다. 그림은 영구히 알지만 **새기는 것은 매번 대가**라서, "이 그림을 이 장비에 새기는 게 맞나"가 판단이 된다.

**탐지기는 좌표를 주지 않는다.** 방향과 대략적 거리만. 사원을 매판 랜덤으로 놓은 의미가 여기 있다.

## 범위 밖

- **보스 사원 상자, 보스 처치 보상** — 8단계. 여기서는 최상위 그림이 카탈로그에 있되 얻을 길이 없다 (`UNOBTAINABLE` 표시).
- **보스 기믹** — 8단계.
- **무기 종류별 차이** (단검·장검·창·활) — 스펙의 "아직 안 정한 것".
- **스테미나** — 생존 절 주제.

## File Structure

| 파일 | 책임 |
|---|---|
| `items/glyphs.py` | **신규** 그림 카탈로그. 순수 표 |
| `items/engraving.py` | **신규** 새긴 것을 담는 장비, 새김 규칙 |
| `entities/structure.py` | **신규** 세계에 선 구조물 |
| `world/structures.py` | **신규** 어디에 몇 개를 놓나 |
| `systems/grimoire.py` | **신규** 배운 그림 |
| `systems/staff.py` | **신규** 지팡이 부담과 과부하 |
| `systems/detector.py` | **신규** 사원 방향 |
| `items/item_kinds.py`, `recipes.py` | 지팡이 3종, 새김 도구, 탐지기 5종 |
| `scenes/play.py` | 배선과 화면 |

---

### Task 1: 그림 카탈로그

**Files:** Create `items/glyphs.py` · Modify `config.py` · Test `tests/test_glyphs.py`(신규)

**Produces:**
- `Glyph(key, name, biome, tier, power, fits, source)` — frozen
- `tier`: `BASIC` / `GREATER` / `SUPREME`
- `fits`: 새길 수 있는 장비 종류 집합 (`WEAPON` / `STAFF` / `ARMOUR`)
- 초원 그림 2개(속성 없음, 유틸) + 바이옴당 3개 = 17개
- `GLYPHS`, `GLYPH_BY_KEY`, `glyphs_of(biome)`

**핵심 — 테스트로 못박을 것:**
- 모든 그림은 적어도 한 곳에 새길 수 있다 (아무 데도 못 새기는 그림은 죽은 행이다)
- 같은 바이옴 안에서 tier가 오를수록 `power`가 오른다
- 초원 그림만 `biome is None`
- key가 안 겹친다

- [ ] **Step 1~5:** 테스트 · 실패 확인 · 구현 · 검증 · 커밋 `feat(items): write down the glyphs`

---

### Task 2: 배운 그림과 새긴 그림

**Files:** Create `systems/grimoire.py`, `items/engraving.py` · Modify `item_kinds.py`, `recipes.py`, `config.py` · Test `tests/test_grimoire.py`, `tests/test_engraving.py`(둘 다 신규)

**Produces:**
- `Grimoire` — 배운 그림의 집합. `learn(glyph) -> bool`(처음이면 True), `knows(glyph)`
- `Engraved` — 장비 하나에 붙은 것: `slots: int`, `glyphs: list[Glyph]`
- `can_engrave(engraved, glyph, grimoire) -> str | None` — 안 되는 이유를 말로 돌려준다
- `CHISEL`("새김 도구") 아이템, 제작대에서. `CHISEL_USES = 3`
- 같은 그림을 두 번 새길 수 없다

**핵심:**
- 배우는 것은 **영구**이고 공짜다. 대가는 **새길 때** 치른다
- `can_engrave`가 bool이 아니라 **이유**를 돌려준다 — 화면에 그대로 띄울 말이 필요하고, 안 되는 이유가 네 가지(모르는 그림/칸 참/안 맞는 장비/이미 새김)나 된다

- [ ] **Step 1~6:** 테스트 · 구현 · 검증 · 커밋 `feat(items): learn glyphs for good, pay to engrave them`

---

### Task 3: 세계에 선 구조물

**Files:** Create `entities/structure.py`, `world/structures.py` · Modify `scenes/play.py`, `config.py` · Test `tests/test_structures.py`(신규)

**Produces:**
- `Structure(pos, kind, glyph, opened)` — 열면 그림을 하나 준다
- 세 종류: **초원 작은**(무방비, 기초) / **초원 큰**(골렘이 지킨다, 같은 기믹 더 셈) / **바이옴 작은**(그 바이옴 기초)
- `place_structures(world, rng)` — 씨앗에서 재현 가능하게 배치
- 열려면 가까이 가서 `E`

**핵심 — 테스트로 못박을 것:**
- 바이옴 구조물은 **자기 바이옴 그림만** 준다
- 초원 구조물은 초원 그림만 준다
- 같은 씨앗은 같은 배치
- 한 번 열면 다시 안 준다
- 모든 **기초** 그림이 적어도 한 구조물에서 나온다 — 하나라도 빠지면 그 바이옴이 막힌다

- [ ] **Step 1~6:** 테스트 · 구현 · 배선 · 손으로 확인 · 검증 · 커밋 `feat(world): scatter the structures that hold the glyphs`

---

### Task 4: 새기기

**Files:** Modify `scenes/play.py`, `items/recipes.py`, `config.py` · Test `tests/test_play_scene.py`

**Produces:**
- 장비(무기·지팡이)가 `Engraved`를 들고 다닌다
- 새김 화면(`G`): 아는 그림 목록 + 고른 장비 + 새기기
- 새길 때마다 도구가 1회 닳고, 3회째에 부서진다
- 효과가 실제로 붙는다 — 새긴 그림의 `power`가 피해에 더해진다

**핵심:** 효과가 안 붙으면 전부 장식이다. 새긴 무기가 **실제로 더 아프게** 때려야 한다.

- [ ] **Step 1~6:** 테스트 · 구현 · 검증 · 커밋 `feat(play): engrave glyphs, and spend the chisel doing it`

---

### Task 5: 지팡이

**Files:** Create `systems/staff.py` · Modify `items/tools.py`, `item_kinds.py`, `recipes.py`, `systems/combat.py`, `config.py` · Test `tests/test_staff.py`(신규)

**Produces:**
- `STAFF` / `GREATER_STAFF` / `SUPREME_STAFF` — 칸 1/2/3, 바이옴 재료로 만든다
- `Staff` — 자체 공격 없음. 새긴 그림이 곧 공격
- `strain` — 센 마법일수록 많이 쌓인다. `STRAIN_MAX`를 넘으면 `overloaded`
- 과부하되면 `STAFF_LOCKOUT`초 동안 못 쓴다. 그동안 부담이 식는다

**핵심 — 테스트로 못박을 것:**
- 그림 없는 지팡이는 **아무것도 못 쏜다** (몽둥이가 아니다)
- 약한 마법은 계속 쏠 수 있고, 센 마법은 금방 과부하된다
- 과부하 중에는 쏴도 안 나간다
- 부담은 안 쏠 때 식는다

- [ ] **Step 1~6:** 테스트 · 구현 · 배선 · 검증 · 커밋 `feat(items): make the staff nothing but what is carved on it`

---

### Task 6: 탐지기

**Files:** Create `systems/detector.py` · Modify `item_kinds.py`, `recipes.py`, `scenes/play.py`, `config.py` · Test `tests/test_detector.py`(신규)

**Produces:**
- 바이옴당 탐지기 아이템 5종, 그 바이옴 재료로 만든다
- `bearing(from_pos, temple) -> float` 방향(도)
- `rough_distance(from_pos, temple) -> str` — "아주 가까움 / 가까움 / 멂 / 아주 멂"
- 핫바에 들고 있으면 화면에 나온다

**핵심:** **좌표를 주지 않는다.** 거리는 띠로 뭉뚱그린다 — 숫자를 주면 사원을 랜덤으로 놓은 의미가 없어진다.

- [ ] **Step 1~5:** 테스트 · 구현 · 검증 · 커밋 `feat(systems): point at a temple without giving it away`

---

### Task 7: 보이게

**Files:** Modify `scenes/play.py`, `config.py` · Test `tests/test_play_scene.py`

- **`G` 새김 화면** — 아는 그림(바이옴별로 묶어서), 못 새기는 것은 이유와 함께 흐리게
- **지팡이 부담 막대** — 과부하되면 붉게
- **탐지기 읽기** — 방향 화살표와 거리 말
- **구조물** — 안 연 것과 연 것이 구분되게

- [ ] **Step 1~5:** 테스트 · 구현 · 손으로 확인 · 검증 · 커밋 `feat(play): show the glyphs, the strain and the bearing`

---

## 이 계획이 끝나면

바이옴에 갈 이유가 생긴다. 구조물을 열어 그림을 배우고, 아껴 쓰는 새김 도구로 장비에 새기고, 지팡이로 쏜다. 탐지기가 사원 방향을 가리키지만 거기 있는 보스는 아직 없다.

**남는 것:** 보스 5마리와 사원 상자(8단계), 최종전과 엔딩(9단계), 스테미나.
