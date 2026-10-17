# 남은 세 바이옴의 지형 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 설원·바람 고원·황무지에 각자의 지형을 준다. 불탄 숲의 용암과 늪지의 늪은 이미 있다. 다섯 곳에서 **움직이는 방식이 각각 달라야** 한다는 스펙의 약속을 마저 지킨다.

**Architecture:** 지형은 세계가 씨앗에서 만드는 고정물. 효과는 순수 함수. 렌더링만 `scenes/play.py`에.

**Tech Stack:** pygame-ce, Python >= 3.10, pytest + pytest-cov, ruff, mypy (strict)

**Spec:** `docs/superpowers/specs/2026-08-29-world-rebuild-concept-design.md` 「다섯 바이옴」

**선행:** 1~7단계 + 생존 완료

## Global Constraints

- 로직은 순수 `update(dt, ...)`, 렌더링은 `draw(surface)`.
- `config.py`는 pygame을 import하지 않는다.
- 고정 타임스텝 `FIXED_DT = 1/60`. 난수는 주입한다.
- TDD: 실패하는 테스트 → 최소 구현 → 리팩터.
- 명령어: `./.venv/Scripts/python.exe -m pytest` · `-m ruff check . && -m ruff format --check .` · `-m mypy`
- 각 작업의 마지막 단계는 커밋이다.

## 왜 지금인가

스펙은 다섯 지형이 **겹치지 않는다**고 약속했다 — 정적 위험 / 시야 제한 / 낙하 / 이동 저하 / 엄폐 없음. 둘만 있으면 그건 약속이 아니라 두 가지 사례다.

그리고 **보스전이 지형 위에서 벌어진다.** 바람 보스의 밀어내기는 절벽이 있어야 무섭고, 번개 보스의 표식은 숨을 데가 없어야 위협이다. 지형을 먼저 깔아야 보스를 거기에 맞춰 설계할 수 있다. 나중에 깔면 보스를 다시 잡아야 한다.

## 이미 있는 것 (본보기)

| 바이옴 | 지형 | 꼴 |
|---|---|---|
| 불탄 숲 | 용암 웅덩이 | 원 N개, 씨앗 재현, 안에 있으면 초당 피해 |
| 늪지 | 늪 | 원 N개, 씨앗 재현, 움직이면 스테미나·바닥나면 피 |

세 번째도 같은 꼴(바람 고원의 절벽)로 가고, 나머지 둘은 **원이 아니다** — 눈보라는 바이옴 전체에 걸리고, 황무지는 **없음**이 지형이다.

## File Structure

| 파일 | 책임 |
|---|---|
| `entities/chasm.py` | **신규** 절벽 구멍 하나 |
| `world/chasms.py` | **신규** 바람 고원에 배치 |
| `systems/falling.py` | **신규** 떨어짐 |
| `systems/weather.py` | **신규** 눈보라의 세기 |
| `world/resources.py` | 황무지에는 나무가 없다 |
| `systems/enemy_spawner.py`, `beast_spawner.py` | 황무지에서는 더 멀리서 더 많이 |
| `scenes/play.py` | 배선과 그리기 |

---

### Task 1: 설원 — 눈보라

**Files:** Create `systems/weather.py` · Modify `scenes/play.py`, `config.py` · Test `tests/test_weather.py`(신규), `test_play_scene.py`

**Produces:**
- `weather.blizzard_at(elapsed) -> float` — 0~1, 시계에서 나오는 순수 함수. 돌풍이 왔다 간다
- 설원 안에 있으면 플레이어 주위 `SIGHT_RADIUS`를 넘어서는 흰 장막
- 세기에 따라 반경이 줄었다 늘었다 한다

**핵심:**
- 시계에서 나오므로 **씨앗 없이도 재현된다**. 난수를 쓰면 돌풍이 매 프레임 튄다
- 피해도 소모도 없다. **보이지 않는 것만으로** 충분하다 — 골렘이 코앞에서 나타난다
- 가장자리 나침반은 계속 보인다. 그게 눈보라의 대응책이다

**테스트로 못박을 것:**
- 설원 밖에서는 장막이 없다
- 세기가 0~1을 벗어나지 않는다
- 같은 시각이면 같은 세기
- 돌풍이 실제로 오르내린다 (상수가 아니다)

- [ ] **Step 1~5:** 테스트 · 구현 · 손으로 확인 · 검증 · 커밋 `feat(world): blow a blizzard across the snowfield`

---

### Task 2: 바람 고원 — 절벽

**Files:** Create `entities/chasm.py`, `world/chasms.py`, `systems/falling.py` · Modify `scenes/play.py`, `config.py` · Test `tests/test_chasm.py`(신규)

**Produces:**
- `Chasm(pos, radius)` — 바람 고원 안에만, 씨앗 재현, 겹치지 않음
- `falling.update_fall(dt, player, chasms)` — 떨어지면 `FALL_DAMAGE`를 입고 **가장자리로 되돌려진다**
- 짐은 잃지 않는다

**핵심:**
- **돌려놓는다, 죽이지 않는다.** 구덩이는 밀려 떨어지는 것이 무서운 거지 즉사가 무서운 게 아니다. 바람 보스의 밀어내기가 들어오면 이게 진짜 위협이 된다
- 가장자리가 멀리서 보여야 한다. 밟기 전에 읽혀야 한다
- 용암·늪과 같은 꼴이라 세 번째 지형은 빠르다

**테스트로 못박을 것:**
- 바람 고원 안에만 생긴다
- 떨어지면 피해를 입고 **구덩이 밖**으로 나온다
- 되돌아간 자리가 또 구덩이가 아니다
- 한 번 떨어지면 피해는 한 번이다 (가장자리에서 계속 덜덜 떨지 않는다)
- 짐은 그대로다

- [ ] **Step 1~6:** 테스트 · 구현 · 배선 · 손으로 확인 · 검증 · 커밋 `feat(world): open chasms in the wind plateau`

---

### Task 3: 황무지 — 숨을 데가 없다

**Files:** Modify `world/resources.py`, `systems/enemy_spawner.py`, `systems/beast_spawner.py`, `config.py` · Test `test_world_resources.py`, `test_enemy_spawner.py`, `test_beast.py`

**Produces:**
- 황무지에는 **나무가 안 난다** — 완전히 트인 땅
- 거기서는 적이 **더 멀리서** 나타난다 (`WASTELAND_SPAWN_REACH`)
- 그리고 **더 많이** 선다 (`WASTELAND_SPAWN_BONUS`)

**핵심:** 다른 넷은 뭔가가 **있는** 지형이고 황무지는 **없는** 지형이다. 그걸 "아무 일도 안 일어난다"로 두면 다섯째 바이옴이 제일 심심해진다 — 트여 있다는 것이 **먼저 보이고 먼저 보인다**는 뜻이 되게 한다.

**테스트로 못박을 것:**
- 황무지에서 나무가 안 나온다 (불탄 숲이 불탄 나무를 내듯, 여기선 아무것도)
- 그래도 광맥과 부스러기는 나온다 — 못 쓰는 땅이 아니라 트인 땅이다
- 적이 다른 바이옴보다 멀리서 나타난다
- 동시에 서 있는 수가 더 많다

- [ ] **Step 1~5:** 테스트 · 구현 · 검증 · 커밋 `feat(world): leave the wasteland nothing to hide behind`

---

### Task 4: 다섯이 다른지 확인한다

**Files:** Test `tests/test_biome_terrain.py`(신규)

**Produces:** 다섯 바이옴을 **나란히 놓고** 비교하는 테스트 한 묶음.

- 다섯이 각각 다른 것을 한다 (한 바이옴의 지형이 다른 바이옴에 새지 않는다)
- 용암은 불탄 숲에만, 늪은 늪지에만, 구덩이는 바람 고원에만
- 눈보라는 설원에서만 걸린다
- 황무지에만 나무가 없다
- **초원은 다섯 중 아무것도 하지 않는다** — 안전한 땅이 안전한 채로 남는다

**핵심:** 각 작업의 테스트는 자기 지형만 본다. 이 묶음은 **겹치지 않는다**는 스펙의 약속 자체를 지킨다 — 나중에 지형을 하나 더 넣을 때 새는 것을 여기서 잡는다.

- [ ] **Step 1~4:** 테스트 · 실패하면 고치기 · 검증 · 커밋 `test(world): hold the five terrains apart`

---

## 이 계획이 끝나면

다섯 바이옴에서 움직이는 방식이 각각 다르다. 그 위에 사원과 보스를 올릴 수 있다 — 바람 보스의 밀어내기는 설 절벽이 있고, 번개 보스의 표식은 숨을 데가 없다.

**남는 것:** 사원과 보스 5마리(상위·최상위 그림 10개, 레벨 캡), 최종전과 엔딩, 타일 렌더링(설원 타일 대기).
