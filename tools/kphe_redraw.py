"""Resolve manually reconstructed 2023 diagrams; no scan-contour fallback."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from kphe_figures import crop_key

ROOT=Path(__file__).resolve().parents[1]

@lru_cache(None)
def records():
    result={}
    for group in ('ab','cd'):
        path=ROOT/'tools/kphe_redraw'/group/'manifest.json'
        if not path.exists():continue
        data=json.loads(path.read_text(encoding='utf8'))
        for key,item in data['figures'].items():
            if key in result:raise ValueError(f'Duplicate native diagram: {key}')
            result[key]=item
    return result

def native_figure(source,page,rect):
    name=Path(str(source)).name
    if not name.startswith('KPhE_2023_'):return None
    key=crop_key(name,page,rect)
    if key not in records():raise ValueError(f'Native diagram not yet reconstructed: {name} page {page} / {key}')
    item=records()[key]
    if item['status']!='verified':raise ValueError(f'Unverified native diagram: {key}')
    use_pdf=bool(item.get('pdf'))
    path=(ROOT/item['pdf'] if use_pdf else ROOT/item['file']).resolve()
    if not path.is_relative_to((ROOT/'tools/kphe_redraw').resolve()):raise ValueError('Invalid diagram path')
    if not path.is_file():raise FileNotFoundError(path)
    expected=item.get('pdf_sha256') if use_pdf else item.get('sha256')
    if expected and hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
        raise ValueError(f'Native diagram changed after verification: {key}')
    return path,item

def dimensions(item,available_width):
    width=float(item.get('recommended_width_pt',item['width_pt']))
    width=min(width,available_width)
    return width,float(item['height_pt'])*width/float(item['width_pt'])
