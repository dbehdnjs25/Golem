# 생존 — 스테미나와 보급 — 구현 계획

> 작업 단위마다 실패하는 테스트 → 구현 → 검증 4종 → 커밋. 진행은 체크박스(`- [ ]`)로 표시한다.

**Goal:** 스펙의 「생존」 절을 채운다. 스테미나가 회피·달리기·채집을 제한하고, 고기가 그것을 돌려주고, 물약이 HP를 돌려준다. 그래서 집에 가는 이유가 "치료"가 아니라 **보급**이 된다.

**Architecture:** 스테미나는 `Player`의 값이고 소모·회복은 순수 함수. 먹는 것은 `systems/consume`. 렌더링만 `scenes/play.py`에.

**Tech Stack:** pygame-ce, Python >= 3.10, pytest + pytest-cov, ruff, mypy (strict)

**Spec:** `docs/specs/2026-08-29-world-rebuild-concept-design.md` 「생존」

**선행:** 1~7단계 완료

## Global Constraints

- 로직은 순수 `update(dt, ...)`, 렌더링은 `draw(surface)`.
- `config.py`는 pygame을 import하지 않는다.
- 고정 타임스텝 `FIXED_DT = 1/60`. 난수는 주입한다.
- TDD: 실패하는 테스트 → 최소 구현 → 리팩터.
- 명령어: `./.venv/Scripts/python.exe -m pytest` · `-m ruff check . && -m ruff format --check .` · `-m mypy`
- 각 작업의 마지막 단계는 커밋이다.

## 이 단계가 고치는 것

**늑대를 잡으면 생고기가 나오는데 아무것도 못 한다.** 6단계에서 야생동물을 넣으면서 보상을 만들었는데, 그 보상이 지금 쓰레기다. 익힌 고기와 물약도 카탈로그에만 있고 조합법도 쓰임도 없다.

**귀환할 이유가 하나뿐이다.** 지금은 "가방이 찼다"와 "HP가 없다"뿐인데, 둘 다 수동적이다. 보급 — **들고 나갈 것을 만들러** 돌아오는 것 — 이 스펙이 원하는 귀환이다.

**늪지가 네 번째인 이유가 아직 없다.** 스펙은 "스테미나 소모 기믹 때문에 요리와 물약 전에는 불공평하다"고 적었는데, 스테미나가 없으니 늪지는 그냥 초록색 구역이다.

## 이 단계의 결정

**스테미나는 세 가지를 먹는다** — 회피, 달리기, 채집. 달리기는 아직 없으므로 여기서 만든다.

**바닥나면 멈추지 않고 느려진다.** 회피와 달리기는 막히지만 **채집은 절반 속도로 계속된다.** 완전히 막으면 가방 하나 채우러 나온 사람이 아무것도 못 하고 서 있게 된다 — 압박이지 벌이 아니어야 한다.

**물약은 서리 결정이 든다.** 스펙이 늪지를 네 번째에 둔 근거가 "요리와 물약이 **생긴 뒤**라야 공평하다"이므로, 물약이 늪지 재료를 요구하면 순환이다. 설원(둘째 바이옴)에서 나오는 서리 결정이 맞다 — 늪지보다 앞서고, 귀하다.

**날고기는 HP를 판다.** 스테미나는 돌아오지만 피를 깎는다. 급할 때 치르는 대가이고, 결계 안 화덕까지 가면 공짜가 되는 것 — 그게 돌아올 이유다.

## 범위 밖

- 배고픔 — 스펙이 **없다**고 못박았다
- 보스(8단계), 최종전과 엔딩(9단계)
- 타일 렌더링 — 설원 타일이 아직 없다

## File Structure

| 파일 | 책임 |
|---|---|
| `entities/player.py` | 스테미나 값, 달리기 |
| `systems/survival.py` | 회복, 소모, 늪지 |
| `systems/consume.py` | **신규** 먹고 마시는 것 |
| `items/recipes.py` | 익힌 고기, 물약 |
| `systems/mining.py` | 채집이 스테미나를 먹는다 |
| `scenes/play.py` | 배선과 막대 |

---

### Task 1: 스테미나

**Files:** Modify `entities/player.py`, `systems/survival.py`, `config.py` · Test `tests/test_player.py`, `test_survival.py`

**Produces:**
- `Player.stamina`, `Player.max_stamina`
- `Player.spend(amount) -> bool` — 모자라면 False, 깎지 않는다
- `survival.update_stamina(dt, player)` — 쓰지 않을 때 차오른다
- `Player.winded` — 바닥났는가

**핵심 — 테스트로 못박을 것:**
- 모자랄 때 `spend`가 **부분 지불을 하지 않는다** — 반쯤 회피하는 건 없다
- 0 아래로 안 내려간다
- 최대를 안 넘는다
- 쓴 직후에는 잠깐 안 찬다 (`STAMINA_DELAY`) — 아니면 연타로 무한 회피가 된다

- [x] **Step 1~5:** 테스트 · 실패 확인 · 구현 · 검증 · 커밋 `feat(player): give the player stamina`

---

### Task 2: 달리기

**Files:** Modify `entities/player.py`, `scenes/play.py`, `config.py` · Test `test_player.py`

**Produces:**
- `Shift`를 누르면 `PLAYER_SPRINT_MULT`배로 달린다
- 초당 `SPRINT_DRAIN`을 먹는다
- 스테미나가 없으면 그냥 안 달린다 (버벅이지 않는다)

**핵심:** 맵이 걸어서 6분이다. 달리기는 **거리를 줄여주는 대신 싸울 여력을 가져간다** — 그게 이 기능의 전부다.

**테스트로 못박을 것:**
- 달리면 더 멀리 간다
- 달리면 스테미나가 준다
- 바닥나면 보통 속도로 돌아간다
- 회피 중에는 달리기가 끼어들지 않는다

- [x] **Step 1~5:** 테스트 · 구현 · 검증 · 커밋 `feat(player): let the player run, and charge for it`

---

### Task 3: 회피와 채집이 값을 치른다

**Files:** Modify `entities/player.py`, `systems/mining.py`, `scenes/play.py`, `config.py` · Test `test_player.py`, `test_mining.py`

**Produces:**
- 회피에 `DODGE_COST`. 모자라면 **회피가 아예 안 나간다**
- 채집에 초당 `MINING_DRAIN`
- 스테미나가 0이면 채집이 `WINDED_MINING_RATE`배로 느려진다

**핵심:** 채집은 **막지 않는다.** 완전히 막으면 가방 하나 채우러 나온 사람이 아무것도 못 하고 서 있는다. 압박이어야지 벌이면 안 된다.

- [x] **Step 1~5:** 테스트 · 구현 · 검증 · 커밋 `feat(systems): make dodging and digging cost wind`

---

### Task 4: 고기

**Files:** Create `systems/consume.py` · Modify `items/recipes.py`, `scenes/play.py`, `config.py` · Test `tests/test_consume.py`(신규)

**Produces:**
- `Recipe(COOKED_MEAT, 1, ((RAW_MEAT, 1),), HEARTH_S, 6.0)` — 결계 안 화덕에서만
- `consume.eat(kind, player) -> bool` — 먹을 수 없는 것이면 False
- 익힌 고기: 스테미나만
- **날고기: 같은 스테미나, HP를 깎는다**
- `F`로 든 것을 먹는다

**핵심 — 테스트로 못박을 것:**
- 날고기가 피를 깎고, 익힌 것은 안 깎는다
- 날고기로는 **죽지 않는다** — 1 아래로는 안 내려간다. 먹어서 죽는 건 버그로 읽힌다
- 스테미나가 꽉 찼으면 먹히지 않는다 (아이템 낭비 방지)
- 곡괭이는 먹을 수 없다

- [x] **Step 1~6:** 테스트 · 구현 · 배선 · 검증 · 커밋 `feat(systems): let meat buy back wind, raw meat at a price`

---

### Task 5: 물약

**Files:** Modify `items/recipes.py`, `systems/consume.py`, `config.py` · Test `test_consume.py`, `test_recipes.py`

**Produces:**
- `Recipe(POTION, 1, ((GRASS, 10), (FROST_CRYSTAL, 1)), HEARTH_S, 8.0)`
- 마시면 HP가 즉시 `POTION_HEAL`만큼
- HP가 꽉 찼으면 안 마신다

**핵심:** **설원 재료**다. 늪지 재료였다면 순환이 된다 — 스펙이 늪지를 네 번째에 둔 근거가 "물약이 생긴 뒤라야 공평하다"이기 때문이다.

- [x] **Step 1~5:** 테스트 · 구현 · 검증 · 커밋 `feat(items): brew a potion out of the snowfield`

---

### Task 6: 늪지가 숨을 앗아간다

**Files:** Modify `systems/survival.py`, `scenes/play.py`, `config.py` · Test `test_survival.py`

**Produces:**
- 늪지에 서 있으면 초당 `BOG_DRAIN`만큼 스테미나가 준다
- 다른 바이옴에서는 아무 일도 없다

**핵심:** 이게 늪지가 네 번째인 이유다. 피해가 아니라 **숨**을 앗아가므로, 요리와 물약을 갖춘 플레이어에게는 성가신 일이고 없는 플레이어에게는 함정이다.

- [x] **Step 1~5:** 테스트 · 구현 · 검증 · 커밋 `feat(world): let the bog take the breath out of you`

---

### Task 7: 보이게

**Files:** Modify `scenes/play.py`, `config.py` · Test `test_play_scene.py`

- **스테미나 막대** — HP 아래. 바닥나면 색이 바뀐다
- 달리는 중인 것이 보이게
- 늪지에서 빠지고 있는 것이 보이게
- 먹고 마신 것은 알림 줄로

- [x] **Step 1~5:** 테스트 · 구현 · 손으로 확인 · 검증 · 커밋 `feat(play): show the wind and what spends it`

---

## 이 계획이 끝나면

늑대 드랍이 쓸모를 갖고, 화덕이 두 번째 일거리를 갖고, 늪지가 위험해진다. 집에 가는 이유가 "치료"가 아니라 보급이 된다.

**남는 것:** 보스 5마리와 사원 상자(8단계), 최종전과 엔딩(9단계), 타일 렌더링(설원 타일 대기).

---

## 실제로 끝난 뒤의 기록

**늪지에서는 쉴 수 없다 — 쓰지 않았는데 그렇게 됐다.** `drain`이 회복 대기(`STAMINA_DELAY`)를
거는데 늪지는 매 프레임 `drain`을 부르므로, 가만히 서 있어도 회복이 영영 안 걸린다. 9초면
바닥난다. 두 규칙에서 저절로 나온 결과인데 **이게 정확히 늪지의 기믹**이다 — 스펙의
"고기로 회복"이 거기서 편의가 아니라 유일한 수단이 된다. 어디에도 안 적혀 있던 성질이라
테스트로 박았다. 안 그러면 나중에 수치 만지다 모르고 없앤다.

**달리기는 지속할 수 없어야 의미가 있다.** 5.6초 달리고 8.2초 회복. 끊어 달리면 전체적으로
약 28% 빠른데, 중요한 건 속도가 아니라 **달리면 회피할 여력이 없다**는 것이다. 같은
통에서 나오므로 도망과 싸움 중 하나를 고르게 된다.

**채집은 막지 않고 느리게 했다.** 완전히 막으면 가방 하나 채우러 나온 사람이 곡괭이를 든 채
서 있게 된다. 45% 속도면 압박이지 벌이 아니다.

**물약을 늪 이끼로 만들면 순환이었다.** 스펙이 늪지를 넷째에 둔 근거가 "요리와 물약이 생긴
뒤라야 공평하다"인데, 물약이 늪지 재료를 요구하면 늪지에 가야 늪지를 갈 수 있게 된다.
설원(둘째)의 서리 결정이라야 순서가 맞는다. 테스트로 박았다.

**날고기로 죽지 않게 바닥을 1로 뒀다.** 간식 먹고 죽는 건 어려운 선택이 아니라 버그로 읽힌다.

**`을(를)`이 네 군데 있었다.** 양식에나 쓰는 표기다. 한글 음절은 `(코드 - 0xAC00) % 28`이
받침 유무를 알려주므로 마지막 글자에서 골랐다. 한글이 아니면 `를` — 외래어를 소리 내 읽을 때
더 안전한 쪽이다.

**죽은 아이템이 전부 살아났다.** 6단계부터 늑대가 떨구던 생고기, 그리고 익힌 고기와 물약.
이제 카탈로그에서 "만들 수도 쓸 수도 없는" 것은 코어 파편과 흑요석 박힌 돌뿐인데, 둘 다
조합 재료가 아니라 **캐는 대상**이라 정상이다.
