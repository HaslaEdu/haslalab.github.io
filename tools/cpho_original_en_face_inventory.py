"""Collect only hash-matched, fully checked same-face English repair results."""
from pathlib import Path
import hashlib, importlib, json
import pymupdf as fitz
from fontTools.ttLib import TTFont
from cpho_original_latin_fonts import BUILD_ROOT, simsun, face, SIMSUN_TTC_SHA, SIMSUN_TTF_SHA

ROOT = Path(__file__).resolve().parents[1]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf8'))
def save(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf8')


def collect():
    assert sha(simsun()) == SIMSUN_TTF_SHA
    result = dict(status='READY', scope='English-only same-original-prose-family repair, 2006/2007/2022 problem papers, 12 pages. Existing Korean PDFs are byte-identical.',
                  files=[], authoring_files=['tools/cpho_original_en_face_inventory.py','tools/cpho_original_latin_fonts.py','tools/cpho_original_en_face_qa.py'])
    for year in [2006,2007,2022]:
        b = importlib.import_module(f'cpho_{year}_original_build'); author = b.AUTHOR
        pdf = BUILD_ROOT/str(year)/'editions'/f'CPhO_{year}_T_EN.pdf'; digest = sha(pdf)
        mupdf = read(BUILD_ROOT/str(year)/'qa'/pdf.stem/'audit.json')
        poppler = read(author/'qa-en-same-face-poppler.json')
        assert mupdf['passed'] and poppler['passed'] and mupdf['sha256']==poppler['sha256']==digest
        assert sha(b.SOURCE)==b.SOURCE_SHA
        data = read(b.BASE/'slots.json'); texts = b.translations(data); build = read(pdf.with_suffix('.build.json'))
        slots = {s['id']:s for p in data['pages'][:4] for s in p['slots']}
        for row in build['fit_report']:
            assert row['text']==b.translated_text(slots[row['id']],texts[row['id']]['en'])
            assert row['overflow']<=.02
        inventory_path = ROOT/f'tools/cpho_{year}_original_inventory.json'; inventory = read(inventory_path)
        korean = dict(next(e for e in inventory['files'] if e['language']=='ko'))
        assert sha(ROOT/korean['path'])==korean['sha256']
        qa_path = author/'qa-en-same-face.json'; save(qa_path,mupdf)
        donors = {}
        for role in ['serif']+(['sans'] if year!=2006 else []):
            path = face(year,role)
            with TTFont(path) as font:
                donors[role] = dict(family=font['name'].getDebugName(1),version=font['name'].getDebugName(5),weight=font['OS/2'].usWeightClass,
                                    sha256=sha(path),local_full_face=str(path),full_font_distributed=False)
        selection = ('All new English prose uses the installed original SimSun family.' if year==2006 else
                     'Body: installed original SimSun. Source SimHei heading/date/section-label prose has no complete embedded Unicode face, installed same-face font or same-run Latin counterpart; explicitly declared final fallback Arial400.' if year==2007 else
                     'Body: installed original SimSun. Source SimHei title/date has no complete embedded or installed same-face font; Calibri400 is the original actual same-run Latin counterpart.')
        policy = dict(priority=['Complete actual original prose face','Installed same family','Proven same-run Latin counterpart','Explicit last fallback'],
                      source_sha256=b.SOURCE_SHA,new_english_faces=donors,selection=selection,simsun_collection_face=0,simsun_collection_sha256=SIMSUN_TTC_SHA,
                      embedded_ascii_evidence='embedded-latin-coverage.json',new_prose_word_space='0.25em for SimSun native prose before explicit reviewed local adjustments. No letter scaling. Original unselected whitespace operators unchanged.',
                      local_adjustments='english-face-spacing.json',native_preservation='Original mathematical glyphs/font programs and figures retained. Fixed point sizes/baselines and render states. No equation images, diagram replacement, reflow, shrinking, new edition labels or printed notes.',
                      korean_artifact_unchanged=korean)
        if year==2007: policy['title_abbreviation']='CPhO is the existing proper-name abbreviation for the Chinese national physics olympiad for secondary-school students. It retains the original one-line heading width and point size.'
        if year in [2006,2022]: policy['raster_limit']='Original raster labels have no recoverable font metadata. Same-document Song-family/size/baseline inference remains documented in the caption/label plans.'
        save(author/'english-face-policy.json',policy)
        files = b.prepare_fonts(data,texts,'en',False,[1,2,3,4]); fonts = {k:fitz.Font(fontfile=str(v)) for k,v in files.items()}; gaps=[]
        for row in build['fit_report']:
            if ' ' not in row['text']: continue
            slot=slots[row['id']];gap=fonts[(slot['family'],slot['bold'])].text_length(' ',fontsize=slot['size'])+row['word_gap_adjustment']
            assert gap>0; gaps.append(gap)
        save(author/'fixed-slot-fit-en-same-face.json',dict(language='en',pdf_sha256=digest,source_sha256=b.SOURCE_SHA,all_fixed_slots_fit=True,min_effective_word_gap_pt=min(gaps),rows=build['fit_report']))
        entry=next(e for e in inventory['files'] if e['language']=='en')
        entry.update(path=str(pdf),bytes=pdf.stat().st_size,sha256=digest,qa=qa_path.relative_to(ROOT).as_posix(),additional_qa=(author/'qa-en-same-face-poppler.json').relative_to(ROOT).as_posix())
        if isinstance(inventory.get('translation_fonts'),dict): inventory['translation_fonts']['en']=selection
        if isinstance(inventory.get('typography'),dict): inventory['typography']['english']=selection
        elif isinstance(inventory.get('typography'),str): inventory['typography']=inventory['typography'].replace('Times New Roman Latin serif in EN','installed original SimSun5.24 family in EN')
        inventory['english_same_face_repair']=dict(policy=(author/'english-face-policy.json').relative_to(ROOT).as_posix(),sha256=digest,font_size_reduction=False,
                   all4_mupdf_and_poppler_pages_passed=True,real_glyph_outline_failures=0,min_effective_word_gap_pt=min(gaps),korean_pdf_unchanged=True)
        newfiles=[f'tools/cpho_{year}_original_build.py',f'tools/cpho_{year}_original_qa.py',f'tools/cpho_{year}_original_inventory.json']
        newfiles += [f'tools/ko/cpho/{year}/original/page{n:02}.tsv' for n in range(1,5)]
        newfiles += [f'tools/ko/cpho/{year}/original/{name}' for name in ['english-face-spacing.json','english-face-policy.json','embedded-latin-coverage.json','qa-en-same-face.json','qa-en-same-face-poppler.json','fixed-slot-fit-en-same-face.json']]
        if year==2022: newfiles += ['tools/cpho_2022_original_labels.py','tools/ko/cpho/2022/original/raster-labels.json']
        notes_path=author/'source-notes.json'
        if notes_path.exists():
            notes=read(notes_path);notes['english_same_face_repair']='english-face-policy.json'
            if isinstance(notes.get('typography'),dict): notes['typography']['english']=selection
            if year==2006:
                edge=mupdf['pages'][1]['inherited_footer_prose_at_image_antialias_edge']
                notes['notes']=[s if not s.startswith('15 KO / 7 EN') else f'Existing KO artifact has15 original footer-edge pixels; current same-face EN has{edge} at4x with a one-raster-pixel edge classification. These are changed underlying footer prose at original fractional image edges, not changes to opaque diagram interiors.' for s in notes['notes']]
            save(notes_path,notes);newfiles.append(notes_path.relative_to(ROOT).as_posix())
        if year==2007:
            inventory['limitations']=[s for s in inventory.get('limitations',[]) if not s.startswith(('Two English ASCII','English label vacuum'))]
            inventory['limitations'].append('English uses documented technical abbreviations and explicit positive word gaps; original point sizes, baselines and mathematical glyphs remain fixed.')
        inventory['authoring_files']=list(dict.fromkeys(inventory.get('authoring_files',[])+result['authoring_files'][:3]+newfiles))
        assert next(e for e in inventory['files'] if e['language']=='ko')==korean
        save(inventory_path,inventory)
        result['authoring_files']+=newfiles
        result['files'].append(dict(year=year,file=pdf.name,path=str(pdf),pages=4,bytes=pdf.stat().st_size,sha256=digest,source_filename=b.SOURCE.name,source_sha256=b.SOURCE_SHA,
                    mupdf_qa=qa_path.relative_to(ROOT).as_posix(),poppler_and_actual_outline_qa=(author/'qa-en-same-face-poppler.json').relative_to(ROOT).as_posix(),
                    policy=(author/'english-face-policy.json').relative_to(ROOT).as_posix(),korean_unchanged=korean,
                    review_mupdf_contact=str(BUILD_ROOT/str(year)/'qa'/pdf.stem/('contact.png' if year==2022 else 'contact-mupdf.png'))))
        print(year,digest,pdf.stat().st_size,'READY',flush=True)
    result['authoring_files']=list(dict.fromkeys(result['authoring_files']))
    result['authoring_file_sha256']={p:sha(ROOT/p) for p in result['authoring_files']}
    save(ROOT/'tools/cpho_original_en_face_inventory.json',result)
    return result


if __name__=='__main__': collect()
