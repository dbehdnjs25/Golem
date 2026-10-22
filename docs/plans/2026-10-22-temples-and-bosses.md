# 8단계: 사원과 보스 — 구현 계획

> 작업 단위마다 실패하는 테스트 → 구현 → 검증 4종 → 커밋. 진행은 체크박스(`- [ ]`)로 표시한다.

**Goal:** 사원 다섯 곳을 실제 장소로 만들고, 보스 다섯을 세운다. 그림 10개와 코어 레벨 50이 여기서 열린다.

**Architecture:** 보스는 `EnemyKind` 표를 물려받는 개체. 기믹은 **보스와 플레이어가 공유하는 하나의 시스템**. 렌더링만 `scenes/play.py`에.

**Tech Stack:** pygame-ce, Python >= 3.10, pytest + pytest-cov, ruff, mypy (strict)

**Spec:** `docs/specs/2026-08-29-world-rebuild-concept-design.md`

**선행:** 1~7단계 + 생존 + 다섯 지형 완료

## Global Constraints

- 로직은 순수 `update(dt, ...)`, 렌더링은 `draw(surface)`.
- `config.py`는 pygame을 import하지 않는다.
- 고정 타임스텝 `FIXED_DT = 1/60`. 난수는 주입한다.
- TDD: 실패하는 테스트 → 최소 구현 → 리팩터.
- 명령어: `./.venv/Scripts/python.exe -m pytest` · `-m ruff check . && -m ruff format --check .` · `-m mypy`
- 각 작업의 마지막 단계는 커밋이다.

## 지금 막혀 있는 것

| | 지금 | 이 단계가 끝나면 |
|---|---|---|
| 그림 | 7/17 | **17/17** |
| 코어 레벨 | 캡 10 | **50** |
| 습격 | 7일 고정 | 7 → 6 → 5 |
| 골렘 | 1종 | **6종** |
| 사원 | 빈 흰 동그라미 | 들어가는 곳 |

탐지기가 사원을 가리키는데 가보면 아무것도 없다. 이 단계가 그 약속을 지킨다.

## 이 단계의 핵심 결정

**기믹 하나를 만들면 둘이 쓴다.** 스펙의 "보스전이 곧 마법 튜토리얼" — 당해본 기믹을 최상위 그림으로 손에 넣는다. 그래서 `systems/gimmicks.py` 하나를 만들고 **보스의 공격과 플레이어의 최상위 마법이 같은 함수를 부른다.** 두 번 구현하면 두 번 틀린다.

**기믹은 지형 위에서 정한다.** 지형이 먼저 깔렸으므로, 그 땅에서 무엇이 무서운지를 보고 정한다. 아래가 제안이고 Task 1에서 확정한다.

| 바이옴 | 지형이 이미 하는 일 | 보스 기믹 제안 | 왜 |
|---|---|---|---|
| 불탄 숲 | 용암이 **가만히** 길을 막는다 | **지나간 자리가 탄다** | 멈춰 있던 위험이 쫓아온다. 화상(`status`)을 그대로 쓴다 |
| 설원 | 빙판에서 **멈출 수 없다** | **발밑을 얼린다** | 미끄러질 땅을 보스가 만든다. 피한 자리가 함정이 된다 |
| 바람 고원 | 구덩이가 **입을 벌리고** 있다 | **강하게 밀어낸다** | 이 지형을 깐 이유 그 자체 |
| 늪지 | 늪이 **숨을 빼앗는다** | **늪을 남긴다** | 한 곳에 묶여 있던 것이 전장을 따라다닌다 |
| 황무지 | **숨을 데가 없다** | **표식끼리 전기가 튄다** | 떨어져 서는 것이 답인데 그럴 땅이 없다 |

**다섯이 쓰는 상황이 다르다** — 땅을 막고(불), 발을 묶고(얼음), 밀어내고(바람), 숨을 깎고(독), 여럿을 한 번에 친다(번개). 색만 다른 데미지가 아니다.

**보스는 단계로 변한다.** HP가 줄면 패턴이 바뀐다. 첫 도전에서 배울 것이 있고 두 번째가 더 잘 된다.

**상자는 보스 전에 연다.** 사원에 들어가면 상자가 먼저 있고, 그 바이옴 **상위 그림**을 준다. 보스를 잡기 전에 그 속성을 한 번 써볼 수 있다 — 기믹에 당하기 전에 맛을 본다.

## 범위 밖

- 최종전과 엔딩 — 9단계
- 타일 렌더링 — 설원 타일 대기

## File Structure

| 파일 | 책임 |
|---|---|
| `systems/gimmicks.py` | **신규** 다섯 기믹. 보스와 플레이어가 공유 |
| `entities/temple.py` | **신규** 사원 하나 (벽·입구·상자) |
| `world/temples.py` | **신규** 배치 (`temple_sites` 위에) |
| `entities/boss.py` | **신규** 보스, 단계, 패턴 |
| `systems/boss_fight.py` | **신규** 보스 업데이트와 처치 |
| `items/item_kinds.py` | 레벨 캡 아이템 5종 |
| `entities/enemy.py` | 바이옴 골렘 5종 |
| `scenes/play.py` | 배선과 화면 |

---

### Task 1: 다섯 기믹

**Files:** Create `systems/gimmicks.py` · Modify `config.py` · Test `tests/test_gimmicks.py`(신규)

**Produces:**
- `Gimmick` — frozen 행. 바이옴마다 하나
- 다섯 효과를 **순수 함수**로. 받는 쪽(`Player`)과 세계(용암·늪·빙판 목록)를 인자로
- 플레이어의 최상위 그림과 보스가 **같은 함수**를 부른다

**핵심 — 테스트로 못박을 것:**
- 다섯이 **서로 다른 것**을 한다 (하나는 피, 하나는 발, 하나는 위치, 하나는 숨, 하나는 여럿)
- 밀어내기가 **구덩이로 밀어넣을 수 있다** — 바람 고원 지형과 실제로 맞물린다
- 늪 남기기가 **늪지 밖에서도** 늪을 만든다 (보스가 들고 다니는 것이지 바이옴 것이 아니다)
- 번개가 표식 **둘 이상**일 때만 튄다
- 어느 기믹도 **즉사시키지 않는다**

- [ ] **Step 1~5:** 테스트 · 구현 · 검증 · 커밋 `feat(systems): write the five gimmicks once, for both sides`

---

### Task 2: 사원

**Files:** Create `entities/temple.py`, `world/temples.py` · Modify `scenes/play.py`, `config.py` · Test `tests/test_temple.py`(신규)

**Produces:**
- `Temple(pos, biome, chest_opened, boss_killed)` — `temple_sites`가 이미 주는 자리에 선다
- 바깥은 벽, 한쪽에 **입구**. 안에 상자
- 상자를 열면 그 바이옴 **상위 그림**
- 들어가야 보스가 깨어난다

**핵심:**
- **상자가 먼저**다. 기믹에 당하기 전에 그 속성을 한 번 써볼 수 있어야 튜토리얼이 성립한다
- 사원은 **지형 위에** 선다 — 용암이나 구덩이 위에 지어지면 안 된다

- [ ] **Step 1~6:** 테스트 · 구현 · 배선 · 손으로 확인 · 검증 · 커밋 `feat(world): raise the five temples`

---

### Task 3: 보스

**Files:** Create `entities/boss.py`, `systems/boss_fight.py` · Modify `entities/enemy.py`, `config.py` · Test `tests/test_boss.py`(신규)

**Produces:**
- `BossKind` — `EnemyKind`를 물려받는 행 ×5. HP·속도·기믹
- `Boss(pos, kind)` — 단계(`phase`)가 HP를 따라 바뀐다
- 단계마다 패턴이 바뀐다: 접촉만 → 기믹 시작 → 간격 단축
- 사원 밖으로 **안 나간다** — 보스가 맵을 돌아다니면 사원이 의미를 잃는다

**핵심 — 테스트로 못박을 것:**
- 다섯 보스의 HP가 난이도 순으로 오른다
- 단계가 **되돌아가지 않는다** (회복해도 1단계로 안 돌아감)
- 1단계에서는 기믹을 안 쓴다 — 배울 시간
- 사원 밖으로 안 나간다
- 죽으면 두 번 죽지 않는다

- [ ] **Step 1~6:** 테스트 · 구현 · 검증 · 커밋 `feat(entities): stand the five bosses in their temples`

---

### Task 4: 처치가 여는 것

**Files:** Modify `items/item_kinds.py`, `entities/core.py`, `entities/enemy.py`, `systems/enemy_spawner.py`, `scenes/play.py` · Test `test_core.py`, `test_enemy_spawner.py`, `test_play_scene.py`

**Produces:**
- 보스가 죽으면 **최상위 그림**을 배우고 **레벨 캡 아이템**이 나온다
- 캡 아이템을 코어에 바치면 캡이 10 오른다
- `GOLEM_KINDS`에 **바이옴 골렘 5종**. 그 바이옴 보스를 잡으면 습격에 합류
- 잡은 보스 수가 습격 주기를 조인다 (이미 있는 표)

**핵심:**
- 캡은 **코어에 가져가야** 오른다. 그래야 보스를 잡고 집에 돌아오는 일이 생긴다
- 합류한 골렘은 **그 바이옴의 기믹을 쓰지 않는다** — 쓰면 습격이 보스 다섯 마리가 된다. 수치만 가져온다

- [ ] **Step 1~6:** 테스트 · 구현 · 검증 · 커밋 `feat(play): let a dead boss open the ladder`

---

### Task 5: 플레이어의 최상위 마법

**Files:** Modify `items/glyphs.py`, `systems/combat.py`, `scenes/play.py` · Test `test_staff.py`, `test_play_scene.py`

**Produces:**
- 최상위 그림을 새긴 지팡이·무기가 **그 기믹을 쏜다**
- 보스가 쓰던 것과 **같은 함수**를 부른다

**핵심:** 이게 이 단계의 값어치다. 당해본 것을 그대로 손에 넣는다. 두 번 구현하면 두 번 틀린다.

**테스트로 못박을 것:**
- 최상위 그림 다섯이 각각 제 기믹을 일으킨다
- 보스의 호출과 플레이어의 호출이 **같은 경로**를 지난다
- 기초·상위 그림은 기믹 없이 피해만 준다

- [ ] **Step 1~5:** 테스트 · 구현 · 검증 · 커밋 `feat(items): put the boss's own trick in the player's hand`

---

### Task 6: 보이게

**Files:** Modify `scenes/play.py`, `config.py` · Test `test_play_scene.py`

- **사원** — 벽과 입구가 멀리서 읽히게. 연 상자와 안 연 상자
- **보스 HP 바** — 화면 위쪽. 단계가 바뀌면 보이게
- **기믹이 일어난 자리** — 탄 땅, 언 땅, 남은 늪, 표식
- **처치** — 알림 줄과, 코어에 가져갈 것이 생겼다는 표시

- [ ] **Step 1~5:** 테스트 · 구현 · 손으로 확인 · 검증 · 커밋 `feat(play): show the temple, the boss and what it leaves`

---

## 이 계획이 끝나면

그림 17개가 전부 열리고, 코어가 50까지 오르고, 습격이 조여들고, 골렘이 여섯 종류가 된다. 남는 것은 **최종전과 엔딩**뿐이다.
