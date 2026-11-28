지역별 나무 48x64 재제작 (이전 작업 기록)

2026-11-25: 격자/팔레트 수정본은 상위 assets/trees/*.aseprite와 *.png에 적용됐습니다.
이 폴더의 source/*.png는 고해상도 생성 참고 자료이며, 최종 편집 파일이 아닙니다.
최종 미리보기: ../pixel_grid_fix/preview-grid.png

기본 나무 grassland/objects/tree_base.aseprite와 같은 48x64 캔버스입니다.
bog / burnt_forest / snowfield / wind_plateau / wasteland 각 PNG + Aseprite.
지역별 나무와 기본 나무를 이미지 참조로 제공해 새로 그렸습니다.
기존 96x128 파일은 보존했으며 게임에서 읽는 경로는 교체하지 않았습니다.

재질마다 Base / Highlight / Shadow 단색 레이어, 별도 Outline 단색 레이어.
투명도는 0/255, 1프레임 정지 이미지입니다.
권장 바닥 앵커: (24, 62). 월드 표시 크기와 원본 캔버스 크기는 별개입니다.

preview.png: 모든 나무를 같은 48x64 캔버스, 4배 정수 확대하여 비교합니다.
윗줄: 기본 나무 / 늪 / 불탄 숲
아랫줄: 설원 / 바람 고원 / 황무지

source/: 내장 image_gen 생성 원본, 실제 프롬프트, 기준 나무 스냅샷.
prepare.lua는 이번 새 파일을 위한 내보내기 기록입니다.
기존 파일이 하나라도 있으면 중단하므로 사용자 수정본을 덮어쓰지 않습니다.
수정 후에는 Aseprite에서 해당 원본의 PNG를 직접 내보내세요.

읽기 전용 검증:
.venv\Scripts\python.exe assets/trees/redrawn48x64/source/validate.py
