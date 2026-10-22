# 6단계: 적 재분류와 습격 — 구현 계획

> 작업 단위마다 실패하는 테스트 → 구현 → 검증 4종 → 커밋. 진행은 체크박스(`- [ ]`)로 표시한다.

**Goal:** 적을 골렘과 야생동물로 나누고, 코어에 HP를 주고, 정해진 밤마다 결계가 뚫리는 습격을 만든다. 습격의 주기와 구성이 플레이어의 진행도를 따라가게 한다.

**Architecture:** 적 종류는 frozen dataclass 표, 습격 일정은 순수 계산이다. 코어 피해와 수리는 순수 함수. 렌더링만 `scenes/play.py`에.

**Tech Stack:** pygame-ce, Python >= 3.10, pytest + pytest-cov, ruff, mypy (strict)

**Spec:** `docs/specs/2026-08-29-world-rebuild-concept-design.md`
**구조를 물려받는 곳:** `docs/specs/2026-07-30-core-defense-design.md` (코어 HP·수리·패배 신호의 구조는 유효, 이름과 수치는 교체)

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

- [x] **Step 1~5:** 테스트 · 실패 확인 · 구현 · 검증 · 커밋 `refactor(enemy): put golem stats in a kind table`

---

### Task 2: 거리에 따른 강화

**Files:** Modify `systems/enemy_spawner.py`, `config.py` · Test `tests/test_enemy_spawner.py`

**Produces:** 스폰되는 골렘의 HP와 속도가 **코어에서의 거리**를 따라 오른다. `config.GOLEM_SCALE_AT_EDGE`가 맵 가장자리에서의 배율

스펙의 "코어에서 멀어질수록 강한 골렘"이다. 거리는 이미 `WorldMap.distance_fraction`이 답한다.

**핵심 — 테스트로 못박을 것:**
- 결계 근처에서 나온 골렘과 맵 끝에서 나온 골렘의 HP가 다르다
- 배율은 거리에 대해 단조 증가한다
- 코어 바로 옆(`fraction == 0`)에서는 표의 기본값 그대로다

- [x] **Step 1~5:** 테스트 · 구현 · 검증 · 커밋 `feat(enemy): make golems harder the further out they spawn`

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

- [x] **Step 1~6:** 테스트 · 구현 · 배선 · 가죽 배낭 조합법 · 검증 · 커밋 `feat(world): put wild animals out at night`

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

- [x] **Step 1~5:** 테스트 · 실패 확인 · 구현 · 검증 · 커밋 `feat(systems): work out which nights are raids`

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

- [x] **Step 1~6:** 테스트 · 구현 · 배선 · 검증 · 커밋 `feat(core): give the core hit points and let raids through the ward`

---

### Task 6: 습격이 보이게

**Files:** Modify `scenes/play.py`, `config.py` · Test `tests/test_play_scene.py`

- **코어 HP 바** — 왼쪽 위 막대에 한 줄 추가. 깎였을 때만 보이게 할지는 구현하면서 판단
- **습격 밤 표시** — 밤 막대가 붉게, 결계 테두리가 끊기거나 붉게. 뚫려 있다는 것이 눈에 보여야 한다
- **오늘이 며칠이고 습격까지 며칠인지** — 글자로. 제작 메뉴에 쓴 글꼴을 그대로
- 야생동물과 골렘이 **색으로 구분**되어야 한다

**핵심:** 습격은 예고 없이 오면 안 된다. 스펙의 주기는 플레이어가 **셀 수 있어야** 의미가 있고, 셀 수 없으면 그냥 가끔 벌어지는 사고다.

- [x] **Step 1~5:** 테스트 · 구현 · 손으로 확인 · 검증 · 커밋 `feat(play): show the day, the next raid and the core's health`

---

## 이 계획이 끝나면

밤에 늑대가 돌아다니고, 며칠마다 결계가 뚫려 골렘이 코어로 몰려오고, 코어가 깎이고 수리된다. 습격 주기는 보스를 잡을수록 짧아지는데, 보스가 아직 없으므로 지금은 7일 고정이다.

**남는 것:** 바이옴 골렘 5종과 그 합류(8단계), 패배 화면(9단계), 스테미나.

---

## 실제로 끝난 뒤의 기록

계획에 없었는데 하면서 드러난 것들. 전부 **헤드리스로 돌려보다가** 나왔다.

**`target` 칸이 장식이었다.** 표에 `TARGET_CORE`를 넣었지만 `combat`은 여전히
`enemy.update(dt, player.pos, ...)`를 불렀다. 밤에 결계 밖에 플레이어를 세워두고
그려보니 **골렘 7마리가 플레이어 위에 겹쳐** 있었다. 분류라는 건 표에 적는 게 아니라
읽는 쪽이 있어야 생긴다.

**습격에 아무도 안 왔다.** 골렘 스폰이 "플레이어 근처, 결계 밖"이었는데 플레이어가
반지름 4,000짜리 결계 한가운데 서 있으면 합법적인 자리가 한 곳도 없다. 첫 습격을
끝까지 돌려보니 **골렘 0마리**로 밤이 끝났다. 그래서 밤에 따라 나눴다 — 평소엔
플레이어 근처(거리만큼 강하게), 습격엔 결계 밖에서 파도로.

**결계가 늑대에게 열려 있었다.** 코어 옆에 가만히 서 있던 플레이어가 죽었다. 결계
안이 안전하지 않으면 3단계의 회복 설계가 통째로 무의미해진다. 골렘과 똑같이 막는다.

**토끼가 플레이어보다 빨랐다.** 영원히 못 잡는 동물은 수줍은 게 아니라 고장 난 걸로
읽힌다. 200 아래로 내렸다.

**밤이 플레이어까지 덮었다.** 장막을 모든 것 위에 깔아서 플레이어가 늑대와 같은 회색이
됐다. 이제 장막은 **땅까지만** — 살아있는 것, 날아가는 것, 시간 재는 것(짐 더미)은
그 위에 그린다.

**코어가 2분 만에 무너졌다.** 20마리가 한 점에 붙으면 레벨 50이어도 6분짜리 밤을
못 버틴다. 사람을 할퀴는 것과 돌덩이를 깎는 것을 다른 수치로 나눴다
(`CORE_CONTACT_DPS`). 지금은 무방비일 때 레벨 1에서 50초, 레벨 50에서 174초.

**습격이 글자로만 보였다.** 결계가 화면보다 크니 붉은 테두리도 몰려오는 골렘도 전부
화면 밖이다. 카메라가 어딜 보든 상관없는 신호가 필요해서, 습격 밤엔 어둠에 안전지대를
안 뚫고 화면 가장자리를 붉게 맥동시켰다.

**덤으로 생긴 것:** 습격자가 결계 반지름에 비례한 자리에서 출발하므로, **결계를 키우면
행군 거리가 길어진다.** 첫 타격이 31초(갓 점화) → 83초(레벨 35)로 밀린다. 따로 규칙을
쓴 게 아니라 비율로 잡아서 저절로 나왔다.
