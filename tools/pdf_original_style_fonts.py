"""Replacement prose fonts; never subset or modify original PDF fonts."""
from pathlib import Path
import hashlib,re
from fontTools import subset
from fontTools.ttLib import TTFont

ROOT=Path(__file__).resolve().parents[1]
FONT_DIR=ROOT/'tools/ko/fonts'
FONTS={
    'serif':FONT_DIR/'NotoSerifCJKkr-Regular.otf',
    'serif-bold':FONT_DIR/'NotoSerifCJKkr-Bold.otf',
    'sans':FONT_DIR/'NotoSansCJKkr-Regular.otf',
    'sans-bold':FONT_DIR/'NotoSansCJKkr-Bold.otf',
}

def source_font_role(name,flags=0):
    """Return family/weight; original italic needs a separate text transform."""
    plain=re.sub(r'^[A-Z]{6}\+','',name).lower()
    sans=any(s in plain for s in ['arial','calibri','helvetica','sans','simhei','heiti','黑体','ºúìå'])
    serif=any(s in plain for s in ['times','cambria','simsun','song','serif','georgia','宋体','ëîìå'])
    if not(sans or serif):serif=bool(flags&4)
    family='serif' if serif and not sans else 'sans'
    bold=bool(flags&16) or bool(re.search('bold|black|semibold|demi',plain))
    return family+('-bold' if bold else '')

def subset_font(font_path,texts,cache_dir=None):
    """Subset only a newly embedded replacement font, preserving its names."""
    font_path=Path(font_path)
    text=texts if isinstance(texts,str) else ''.join(texts)
    chars=''.join(sorted(set(text)))
    digest=hashlib.sha256(b'retain-cid-gids-v1'+font_path.read_bytes()+chars.encode('utf8')).hexdigest()[:16]
    cache=Path(cache_dir) if cache_dir else ROOT/'tmp/original-style-repair/fonts'
    cache.mkdir(parents=True,exist_ok=True)
    target=cache/(font_path.stem+'-'+digest+font_path.suffix)
    if target.exists():return target
    font=TTFont(font_path)
    cmap=font.getBestCmap();missing=[c for c in chars if not c.isspace() and ord(c)not in cmap]
    if missing:raise ValueError(f'{font_path.name}: unsupported characters {missing}')
    options=subset.Options();options.name_IDs=['*'];options.name_legacy=True;options.name_languages=['*']
    options.retain_gids=True
    worker=subset.Subsetter(options=options);worker.populate(text=chars);worker.subset(font)
    font.save(target);font.close();return target

def korean_font(source_name,flags,texts,override=None,cache_dir=None):
    role=override or source_font_role(source_name,flags)
    return role,subset_font(FONTS[role],texts,cache_dir)
