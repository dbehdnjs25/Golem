# Meadow Studio

`index.html`을 더블클릭하면 열리는 오프라인 맵 에디터입니다. HTML 하나에 타일과 코드를 포함하므로 서버와 설치가 필요 없습니다.

- 왼쪽에서 타일을 고르고 드래그해 그립니다.
- 브러시 B / 사각형 R / 영역 채우기 F / 기본 잔디로 지우기 E / 스포이트 I / 화면 이동 H.
- Space + 드래그로 이동, 휠로 확대·축소, 우클릭으로 타일을 추출합니다.
- Ctrl+Z 실행 취소, Ctrl+Shift+Z 다시 실행, Ctrl+S JSON 저장. 최대 80개 작업을 되돌립니다.
- 브라우저 로컬 저장소에 자동 저장합니다. 안정적인 보관과 다른 컴퓨터 이동에는 JSON 다운로드를 사용하세요.
- JSON 불러오기, 새 맵, 크기 변경도 실행 취소할 수 있습니다. 크기 변경은 왼쪽 위를 기준으로 유지합니다.
- WebP 내보내기는 격자와 편집 표시를 제외한 원래 해상도의 맵 이미지입니다. 브라우저 WebP 인코더의 최고 품질 설정이며, 타일 원본의 무손실 WebP와는 별개입니다.

## 맵 데이터

JSON의 `data`는 왼쪽 위부터 행 우선 순서로 저장한 0~15 타일 ID입니다. `(x, y)`의 타일은 `data[y * width + x]`입니다. 타일 크기는 32px이며 `tileset`은 이 에디터 폴더 기준의 프로젝트 시트 경로입니다. 파일 위치를 바꾸더라도 에디터는 내장 타일을 사용합니다.

이 에디터는 시각적인 지형 배치 데이터를 만듭니다. 기존 게임의 원형 월드/바이옴 생성기에는 자동 적용하지 않습니다. 충돌·자원·스폰 데이터는 포함하지 않습니다.

Pygame에서 타일을 그리는 예시:

```python
import json
from pathlib import Path
import pygame

data = json.loads(Path('my-map.json').read_text(encoding='utf-8'))
atlas = pygame.image.load('assets/grassland/tiles32/grassland-32.webp')
for i, tile_id in enumerate(data['data']):
    source = pygame.Rect((tile_id % 4) * 32, (tile_id // 4) * 32, 32, 32)
    screen.blit(atlas, ((i % data['width']) * 32, (i // data['width']) * 32), source)
```

## 수정 및 검증

소스는 `editor.template.html`, `editor.css`, `editor.js`, `model.js`입니다.

```powershell
.venv/Scripts/python.exe assets/map-editor/build.py
node assets/map-editor/model.test.cjs
```
