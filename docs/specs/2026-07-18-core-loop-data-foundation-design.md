# 코어 디펜더 — 핵심 루프 & 데이터 기반 설계 (Spec)

- **작성일:** 2026-07-18
- **대상 서브시스템:** 핵심 루프(채굴 → 귀환 → 동기화)와 그 데이터 기반
- **아키텍처 방향:** A안 — 기존 스캐폴딩 관례(OOP 엔티티 + 시스템 모듈, `update`/`draw` 분리)
- **상태:** 설계 확정 대기 (구현 전)

이 문서는 **계획**입니다. 코드는 포함하지 않으며, 승인 후 구현 계획(plan)으로 넘어갑니다.

---

## 1. 목표와 범위

### 이번 spec이 만드는 것
포맷된 빈 드라이브에서 시작하는 게임의 **가장 바닥 루프**를 end-to-end로 돌린다:

> 필드에서 데이터 파편을 캔다 → 가방이 찬다 → 코어로 돌아온다 → 자원이 창고로 자동 입고된다 → 반복.

구체 포함 항목:

- 화면보다 큰 **월드**(경계만; 타일 데이터 구조는 제외 — 아래 참조)
- **카메라**: 자유 시점 + `Y` 키로 캐릭터 고정 토글 (롤 스타일)
- **플레이어**: `WASD` 8방향 직접 이동
- **핫바 선택(최소)**: 활성 도구 개념. 채굴 도구가 슬롯에 들어감
- **채굴 도구 + 데이터 파편**: 조준 + 좌클릭 홀드로 파편 HP를 깎아 획득
- **파편 스포너**: 시간에 따라 파편 생성(결정론적)
- **저장 데이터 모델**: 필드 배낭(carry) + `/Documents`(창고), 둘 다 용량 제한
- **코어 + 동기화**: 코어 근처에서 배낭 → 창고 자동 이체
- 위 전부를 엮는 **`PlayScene`**

### 이번 spec이 만들지 않는 것 (후속 spec)
- 바이러스 4종·전투(무기 도구)
- 봇 생산·방화벽·방어선
- 파일탐색기 인벤토리 UI(`E` 키), 핫바 해금 경제
- **바닥 타일 오염** 및 그에 필요한 **타일 데이터 구조**
- `Drivers` 칩셋, `Trash` 휴지통

> **데이터 모델은 이 후속 기능들을 수용하도록 설계**하되, 로직 구현은 미룬다.

---

## 2. 저장 구조 (핵심)

저장 공간은 **두 단계**다. 비유하면 "가방"과 "집 창고".

| 이름 | 역할 | 용량 | 언제 채워지나 | 가득 차면 |
|---|---|---|---|---|
| **필드 배낭 (carry)** | 필드에서 캘 때 자원이 담기는 임시 버퍼. 원본 기획엔 이름이 없던 개념 | 작음, 제한 있음 | 채굴 중 | **채굴 불가 → 강제 귀환** |
| **`/Documents` (창고/보관함)** | 드라이브의 실제 저장소. 파일탐색기에 표시되고, 업그레이드·생산이 여기서 자원을 꺼내 씀 | 큼, 제한 있음(업그레이드 대상) | 코어 복귀 시 배낭에서 이체 | 이체가 들어갈 만큼만 되고 나머지는 배낭에 잔류 + "창고 용량 부족" 경고 |

- 원본 *Core Loop 2단계*의 "수집 자원을 **창고로 전송**"과 인벤토리의 "`/Documents`(코어 복귀 시 자동 입고)"는 **같은 것**을 가리킨다 → `/Documents`가 곧 그 창고다.
- **동기화(sync)** = 코어 복귀 시 배낭 → `/Documents` 이체 동작.
- 자원은 **단일 종류(데이터 파편)**. 파편 1개 = 고정 MB(`FRAGMENT_MB`). 사용량 = 개수 × `FRAGMENT_MB`.
- **폴더 모델**(`mb_cap`을 가진 일반형)은 이번에 정의하되, 이번 루프에서 가동하는 건 배낭 + `/Documents`뿐. `Downloads/Drivers/Trash`는 UI spec에서 인스턴스화.

---

## 3. 모듈 구조

기존 관례를 따른다: `pygame`을 import하지 않는 로직은 전부 헤드리스 테스트 가능. `pygame.display`/이벤트 펌프/`pygame.quit`은 `core/app.py`에만.

```
src/game/
  config.py            # 상수 추가(아래 §8). pygame 미import 유지(색상은 튜플)
  entities/
    player.py          # 위치·속도, 이동벡터로 update. 로직 전용
    fragment.py        # 데이터 파편: 위치, hp, mb_value, "고갈 시" 훅. 로직 전용
    core.py            # 중앙 코어: 위치, sync_radius. 로직 전용
  systems/
    camera.py          # 월드<->화면 변환, 자유팬 + 잠금 토글. 순수 수학
    mining.py          # 조준점 + 활성 도구 + 홀드 -> 파편 hp 감소 -> 배낭 적재 판정
    spawner.py         # 파편 스폰(주입된 seed rng로 결정론적)
  inventory/
    storage.py         # Folder(mb_cap), Backpack(carry), Documents 이체 로직
    hotbar.py          # 슬롯들, unlocked_count(=2), selected_index, 활성 도구 해석
  items/
    tools.py           # MiningTool(range, dps). (무기는 후속 spec)
  scenes/
    play.py            # 이벤트->상태 축적, update(dt), draw(surface)
```

> **월드/타일**: 이번 spec은 자유 이동·픽셀 공간이라 타일 **데이터 구조**의 소비자가 없다(오염·경로탐색은 적 spec). 따라서 `world/tilemap.py`는 **만들지 않는다**. 월드는 `config`의 `WORLD_W/H` 경계로 정의하고, 바닥은 시각적 타일 패턴으로만 렌더한다. 타일 데이터 구조는 **적/오염 spec에서 도입**한다.

---

## 4. 입력 처리 원칙 (update를 순수하게 유지)

- `update` 내부에서 `pygame.key.get_pressed()` 같은 **폴링 금지**.
- `PlayScene.handle_event`가 이벤트에서 상태를 **축적**한다:
  - `KEYDOWN/KEYUP` → 눌린 이동키 집합(WASD), 도구 선택(1/2), 카메라 잠금 토글(Y)
  - `MOUSEMOTION` → 마우스 화면 좌표
  - `MOUSEBUTTONDOWN/UP` → 좌클릭 홀드 여부
- 엔티티/시스템의 `update(dt, ...)`는 전부 **명시 인자**를 받는다 → 헤드리스 테스트 가능. `PlayScene`만 `pygame`과 맞닿는 경계.

---

## 5. 프레임당 흐름

### 5.1 로직 (`PlayScene.update(dt)` — `dt = FIXED_DT`)
1. 축적된 이동키 → 이동벡터(대각선 정규화) → `player.update(dt, move_dir, world_bounds)` (경계 클램프)
2. `camera.update(dt, player_pos, mouse_screen, view_size, world_bounds, mining_held)`
   - `LOCKED`: 플레이어 중심으로 offset(경계 클램프)
   - `FREE`: 마우스가 화면 가장자리면 그 방향으로 팬. **단, `mining_held`면 가장자리 팬 억제** (마우스 이중 역할 충돌 방지)
3. **채굴** (`mining.update`): 활성 도구가 `MiningTool`이고 좌클릭 홀드면
   - `camera.screen_to_world(mouse)`로 조준점 산출
   - **대상 = 조준점이 가리키는(최근접) 파편이면서 `플레이어`로부터 `MINING_RANGE` 이내**인 파편 (커서는 "어느 파편"만 고름, 거리 판정은 플레이어 기준)
   - 대상 hp를 `dps * dt`만큼 감소 → hp ≤ 0이면 배낭에 적재 시도
   - **배낭이 꽉 차면**: 채굴 무효 + "용량 부족" 경고, 파편 보존
4. `spawner.update(dt, 현재_파편_수, rng)` → 상한까지 새 파편 스폰(코어 반경·기존 파편과 겹침 회피, 시도 횟수 상한)
5. **동기화**: 플레이어가 `core.sync_radius` 안에 있으면 배낭 → `/Documents` 이체(창고 여유만큼). 창고가 꽉 차면 부분 이체 + 경고.

### 5.2 렌더 (`PlayScene.draw(surface)`)
- **월드 레이어**(카메라 변환 적용): 바닥 타일 패턴 → 파편 → 코어 → 플레이어
- **HUD**(화면 좌표 고정): 핫바 2칸(선택 슬롯 강조), 배낭 MB 게이지, 카메라 잠금 상태 표시

---

## 6. 엔티티/시스템 책임

- **`Player`**: 위치·속도·반지름. `update(dt, move_dir, bounds)` — 이동 적분 + 경계 클램프. `pygame` 미사용(벡터 수학은 `Vector2` 허용, 헤드리스 OK).
- **`Fragment`**: 위치·`hp`·`mb_value`. `damage(amount) -> depleted: bool`. **"고갈 시" 훅**을 열어둬, 후속 spec에서 **트로이 목마(위장 파편)**가 폭발 이벤트를 끼울 수 있게 한다.
- **`Core`**: 위치·`sync_radius`. `is_in_sync_range(pos) -> bool`. (코어 HP는 방어 spec에서)
- **`Camera`**: `offset`, `mode(FREE|LOCKED)`. `world_to_screen`/`screen_to_world`(서로 역변환), `toggle_lock()`(FREE→LOCKED 시 플레이어로 스냅), `update(...)`. 순수 수학 → 테스트 용이.
- **`MiningSystem`**: 활성 도구·조준·홀드·파편 목록·플레이어 위치·배낭을 입력받아 채굴 1스텝 처리.
- **`FragmentSpawner`**: `spawn_interval`, `max_fragments`, 누적기. 주입된 `random.Random(seed)`로 위치 생성 → 결정론적 테스트.
- **`Backpack` / `Folder`**: `mb_cap`, 사용량, `is_full`, `add() -> bool`, 이체.
- **`Hotbar`**: `slots[MAX=7]`, `unlocked_count=2`, `selected_index`. `select(n)`(unlocked 범위로 제한), `active_tool` 해석. slot0 = `MiningTool`, slot1 = 비움(None).
- **`MiningTool`**: `range`, `dps` (데이터).

---

## 7. 엣지케이스

- 플레이어·카메라는 **월드 경계로 클램프**(맵 밖 공허 안 보임)
- 조준 아래 파편이 여럿 → **최근접 1개**만
- 스폰은 코어 반경 및 다른 파편과 **겹치지 않게**(거절 샘플링 + 시도 횟수 상한 → 월드 포화 시 무한루프 방지)
- `FREE → LOCKED` 전환 시 카메라가 플레이어로 **스냅**
- 채굴 홀드 중에는 카메라 가장자리 팬 **억제**
- 이체 시 창고 여유 < 배낭 잔량 → **부분 이체 + 경고**
- 배낭 만재 → 채굴 무효(파편 손실 없음)

---

## 8. 제안 초기값 (튜닝 가능)

| 상수 | 제안값 | 비고 |
|---|---|---|
| `SCREEN_SIZE` | 960 × 540 | 기존 유지 |
| `WORLD_W / WORLD_H` | 2400 × 1600 | 화면보다 큼 → 자유 카메라 의미 |
| `TILE_SIZE` | 32 | **렌더 전용**(데이터 구조 아님) |
| `PLAYER_SPEED` | 220 px/s | |
| `PLAYER_RADIUS` | 14 | |
| `FRAGMENT_HP` | 60 | |
| `MINING_DPS` | 40 hp/s | → 파편 1개 ≈ 1.5초 채굴 |
| `MINING_RANGE` | 96 px | 플레이어–파편 거리 |
| `FRAGMENT_MB` | 5 MB | 파편 1개 크기 |
| `BACKPACK_CAP_MB` | 50 MB | ≈ 파편 10개 → 자주 귀환 |
| `DOCUMENTS_CAP_MB` | 500 MB | ≈ 파편 100개 |
| `CAMERA_PAN_SPEED` | 400 px/s | 자유 시점 팬 속도 |
| `CAMERA_EDGE_MARGIN` | 40 px | 화면 끝 팬 감지 폭 |
| `SPAWN_INTERVAL` | 2.0 s | |
| `SPAWN_MAX` | 30 | 동시 최대 파편 수 |
| `CORE_RADIUS` | 40 px | |
| `CORE_SYNC_RADIUS` | 120 px | 이 안에 들어오면 자동 이체 |

---

## 9. 테스트 계획 (헤드리스, 로직 중심)

| 대상 | 검증 |
|---|---|
| `Player.update` | 이동 적분, 대각선 정규화, 경계 클램프 |
| `Camera` | world↔screen 역변환 일치, 잠금 추적, 가장자리 팬, 채굴 중 팬 억제, 경계 클램프, 전환 스냅 |
| `MiningSystem` | 홀드 시 hp 감소(dps×dt), 고갈 시 배낭 적재, 플레이어 거리 밖이면 무효, 배낭 만재 시 차단, 파편 보존 |
| `Fragment` | `damage` 누적·고갈 판정, "고갈 시" 훅 호출 |
| `Backpack/Folder` | 용량 계산, `is_full`, `add` 성공/실패 |
| `동기화(Core+이체)` | 반경 내 이체·배낭 비움, 반경 밖 무동작, 창고 만재 시 부분 이체 |
| `FragmentSpawner` | 주기 누적, 상한, seed rng 결정론성, 코어 회피, 시도 상한 |
| `Hotbar` | 선택이 `unlocked_count`로 제한, 활성 도구 해석 |

렌더(`draw`)는 로직 테스트로 커버되지 않는 최소한만 확인(예: 코어/파편이 화면에 그려지는지). 픽셀 정밀 테스트는 지양.

---

## 10. 열린 질문 / 후속 연결점

- 배낭·창고의 **업그레이드 곡선**(용량 확장 비용)은 경제 spec에서.
- 핫바 **해금 경제**(칸 순차 해금)는 UI/경제 spec에서. 이번엔 `unlocked_count=2` 고정.
- 파편의 "고갈 시" 훅 → **트로이 목마** 위장 파편(적 spec).
- 월드 **타일 데이터 구조** → 오염·경로탐색(적 spec).
- 파일탐색기 인벤토리 UI(`E`) → UI spec. 이번엔 데이터 모델만.
