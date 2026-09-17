"""Build a portable, offline HTML editor with the project WebP tiles embedded."""
import base64
import json
from pathlib import Path

root = Path(__file__).parent
tiles = root.parent / 'grassland' / 'tiles32'
meta = json.loads((tiles / 'tileset.json').read_text(encoding='utf-8'))
meta['url'] = 'data:image/webp;base64,' + base64.b64encode((tiles / meta['image']).read_bytes()).decode()
html = (root / 'editor.template.html').read_text(encoding='utf-8')
for key, value in {
    '__CSS__': (root / 'editor.css').read_text(encoding='utf-8'),
    '__MODEL__': (root / 'model.js').read_text(encoding='utf-8'),
    '__APP__': (root / 'editor.js').read_text(encoding='utf-8'),
    '__ASSETS__': json.dumps(meta, ensure_ascii=False),
}.items():
    html = html.replace(key, value)
(root / 'index.html').write_text(html, encoding='utf-8')
print('Built assets/map-editor/index.html (standalone)')
