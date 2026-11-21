엔티티 기본 자세 7종

player: 48x64
wolf: 64x48
rabbit: 32x32
golem, burnt_forest_golem, snowfield_golem, wind_plateau_golem: 64x80

각 이름의 PNG와 Aseprite 파일이 한 쌍입니다.
모두 남동쪽을 바라보는 기본 자세 1프레임이며, 걷기/공격 애니메이션은 없습니다.
게임 연결 코드는 수정하지 않았습니다. 식별자와 권장 발 위치는 manifest.json에 있습니다.
원본 크기와 게임 표시 크기는 별도로 선택할 수 있습니다. 확대 시 nearest-neighbor를 사용하세요.

기준: grassland/objects/tree_base.aseprite의 현재 첫 프레임.
재질별 Base / Highlight / Shadow 단색 레이어와 Outline 단색 레이어로 나뉩니다.
투명도는 0/255만 사용하며, PNG는 Aseprite 레이어 합성과 동일합니다.

preview.png는 3배 확대 비교판입니다.
윗줄: 기준 나무 / 플레이어 / 늑대 / 토끼
아랫줄: 기본 골렘 / 불탄 숲 골렘 / 설원 골렘 / 바람 고원 골렘
나무는 48x64 원본 비교용이며 게임의 96x128 표시 크기를 나타내지는 않습니다.

source/에는 내장 image_gen 생성 원본, 실제 프롬프트, 기준 나무 스냅샷을 보존했습니다.
prepare.lua는 새 산출물 제작 기록이며, 기존 PNG나 Aseprite가 있으면 전체 작업을 중단합니다.
사용자 수정 후 prepare.lua를 재실행해서 덮어쓰지 마세요.
수정한 Aseprite의 PNG 내보내기는 해당 파일에서 직접 수행하세요.

읽기 전용 검증:
.venv\Scripts\python.exe assets/entities/source/validate.py
