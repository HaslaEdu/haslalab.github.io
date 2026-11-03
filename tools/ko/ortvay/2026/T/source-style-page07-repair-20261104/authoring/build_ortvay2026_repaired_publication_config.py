"""Build only a new private config after actual repaired READY and final assembly."""
from pathlib import Path
import argparse,json,shutil

from publication_paths import active_root
from build_ortvay_r4_publication_config import Pins,sha,read
import ortvay2026_repaired_publication as publication

def json_aliases(pins,year,aliases,forced):
    """Share only proven identical aliases across explicit origin/copy paths."""
    selected=sorted(pins.evidence);groups={}
    for source in selected:groups.setdefault(source.name.casefold(),set()).add(pins.rows[source]['sha256'])
    redirects={};created=[];allocated={}
    for source in selected:
        row=pins.rows[source];digest=row['sha256'];name=forced.get(source)
        if name is None and len(groups[source.name.casefold()])>1:
            name=f'ortvay-{year}-{source.stem}-{digest[:16]}.json'
        if name:
            aliases.mkdir(parents=True,exist_ok=True);target=aliases/name
            shared=target in allocated
            if shared:
                assert allocated[target]==digest and sha(target)==digest
                assert target.read_bytes()==source.read_bytes(),'An origin/copy alias has different actual bytes'
            else:
                assert not target.exists(),('Unexpected pre-existing alias',target)
                shutil.copy2(source,target);allocated[target]=digest
            redirects[source]=pins.add(target,digest,row['bytes'])
            created.append(dict(original=str(source),alias=redirects[source],shared_identical_origin_copy_alias=shared))
        else:redirects[source]=pins.add(source,digest,row['bytes'])
    evidence=[];names={}
    for source in selected:
        value=redirects[source];key=Path(value['path']).name.casefold()
        if key in names:assert names[key]==value['sha256'];continue
        names[key]=value['sha256'];evidence.append(value)
    return redirects,evidence,created

def build(pdf, ready_path, output):
    publication.assert_production_go_available()
    output=Path(output).resolve();pdf=Path(pdf).resolve()
    assert output.suffix=='.json'and not output.exists()
    assert output.is_relative_to(publication.BASE/'staged')
    aliases=output.parent/(output.stem+'-json-evidence');assert not aliases.exists()
    pins=Pins();qa=read(pdf.with_suffix('.qa.json'))
    result=publication.collect(pdf,qa,ready_path,pins,active_root())
    forced={}
    for row in result['pages']:
        for key in ('independent_audit','machine_result','visual_review'):
            forced[Path(row[key]['path'])]=f'ortvay-2026-page{row["page"]:02}-{key.replace("_","-")}.json'
    source_programs=[Path(__file__).resolve(),Path(publication.__file__).resolve(),
        publication.BASE/'engine/ortvay_source_style_publication.py',
        publication.BASE/'engine/ortvay_full_ctm_publication.py']
    for path in source_programs:pins.add(path)
    redirects,evidence,created=json_aliases(pins,2026,aliases,forced)
    pages=[]
    for source in result['pages']:
        row=dict(source)
        for key in ('independent_audit','machine_result','visual_review'):
            row[key]=redirects[Path(source[key]['path'])]
        pages.append(row)
    config=dict(schema=publication.CONFIG_SCHEMA,year=2026,
        publication_subdir='source-style-page07-repair-20261104',
        source_sha256=qa['source_sha256'],output_sha256=qa['sha256'],
        original_ready=result['ready_pin'],ready=redirects[Path(result['ready_pin']['path'])],
        pages=pages,runtime_files=result['base_runtime'],evidence=evidence,JSON_aliases=created,
        builder=dict(path=str(Path(__file__).resolve()),sha256=sha(__file__)),
        protection_counts=dict(original_entries=1536,unique_original_files=1534,private_inputs=597,
                               original_runtime_Python=46,additional_page_repair_Python=3),
        joined_qa=result['joined_pin'])
    for key,pin in result['binding']['profile'].items():config[key]=redirects[Path(pin['path'])]
    config['pins']=pins.export()
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf8')as stream:stream.write(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(status='REPAIRED_YEAR_PUBLICATION_CONFIG_WRITTEN_NOT_STAGED',path=str(output),
                         sha256=sha(output),pages=10,runtime_files=46,additional_programs=3,
                         pins=len(config['pins']),JSON_evidence=len(evidence))))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdf',type=Path,required=True);parser.add_argument('--ready',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    build(a.pdf,a.ready,a.output)
