"""Package the original atlas into a dependency-free HTML asset browser."""
import base64
import json
from pathlib import Path

ROOT = Path(__file__).parent
NAMES = [
    '밝은 잔디', '짙은 잔디', '성긴 잔디', '클로버 잔디', '꽃 잔디', '마른 잔디',
    '가로 흙길', '세로 흙길', '우하단 굽이', '좌하단 굽이', '우상단 굽이', '좌상단 굽이',
    '데이지', '노란 들꽃', '파란 들꽃', '분홍 들꽃', '키 큰 풀', '고사리',
    '작은 돌', '큰 바위', '이끼 바위', '조약돌 무리', '빨간 버섯', '갈색 버섯',
    '둥근 덤불', '열매 덤불', '어린 나무', '둥근 활엽수', '길쭉한 활엽수', '침엽수',
    '작은 연못', '부들', '쓰러진 통나무', '그루터기', '넓은 울타리', '좁은 울타리',
]
CATEGORIES = ['잔디', '길', '꽃과 풀', '바위와 버섯', '나무와 덤불', '물과 목재']
data = [dict(id=f'meadow_{i+1:02}', name=name, category=CATEGORIES[i//6], column=i%6, row=i//6) for i,name in enumerate(NAMES)]
(ROOT/'atlas.json').write_text(json.dumps(dict(image='grassland-atlas.png', columns=6, rows=6, assets=data, note='Source atlas cells are proportional; generated terrain is not guaranteed seamless. Game tile size is 32px; rescale after selecting assets.'), ensure_ascii=False, indent=2), encoding='utf-8')
template = (ROOT/'preview.template.html').read_text(encoding='utf-8')
template = template.replace('__ASSET_DATA__', json.dumps(data, ensure_ascii=False)).replace('__IMAGE_DATA__', base64.b64encode((ROOT/'grassland-atlas.png').read_bytes()).decode())
(ROOT/'preview.html').write_text(template, encoding='utf-8')
