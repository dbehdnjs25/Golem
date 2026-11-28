2026-11-25 픽셀 격자 / 팔레트 수정

최종 편집 파일은 상위 assets/trees/*.aseprite, 게임 이미지는 같은 이름의 PNG입니다.
5종 모두 48x64. 기본 tree_base.aseprite와 동일한 16x16 편집 격자입니다.
1 이미지 픽셀 = 1 색상 인덱스, 투명 인덱스 0, 보간/반투명 없음.
일반 4종: 불투명 7색 + 투명 1칸. 설원: 불투명 10색 + 투명 1칸.
각 재질의 Base/Highlight/Shadow는 각각 단색 레이어이고 Outline도 별도 단색입니다.

기존 48x64 결과물의 좌표를 그대로 사용해 고립된 명암 픽셀만 같은 재질 안에서 정리했습니다.
고해상도 생성 원본을 다시 축소하거나 재생성하지 않았습니다.
기본 나무와 src/, tiles32는 수정하지 않았습니다.
게임은 기존 렌더러에서 2배 정수 확대하여 96x128로 표시합니다.

preview.png: 기본 / 늪 / 불탄 숲, 설원 / 바람 고원 / 황무지. 정확한 4배 픽셀 확대.
preview-grid.png: 같은 비교에 원본 1픽셀마다 격자를 표시했습니다. 미리보기용 선입니다.
backup-before-fix/: 교체 직전 파일의 원본 바이트와 SHA256 기록.
ready/: 검증 후 실제 경로에 복사한 수정본.
fix.lua: 이번 수정 기록. ready/에 기존 파일이 있으면 중단해 사용자 편집본을 보존합니다.

검증:
.venv\Scripts\python.exe assets/trees/pixel_grid_fix/validate.py assets/trees
