"""Private repair of one authored-space token; source/baselines are read-only."""
from pathlib import Path
import json,hashlib,os
import cpho_2023_natural_spacing as build
from pdf_memory_gate import page_worker
ROOT=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab')
HERE=Path(__file__).resolve().parent
build.ROOT=ROOT;build.SLOTS=ROOT/'tmp/original-style-repair/2023/slots.json';build.FIGURES=ROOT/'tools/ko/cpho/2023/original-labels/source-survey.json';build.OUT=HERE/'pages'
if __name__=='__main__':
 print('PRIVATE PAGE11 PID',os.getpid(),flush=True)
 with page_worker():path,report=build.build(11,'ko')
 print(json.dumps(dict(output=str(path),sha256=report['output_sha256'],native_qa=report['native_move_qa']['passed']),ensure_ascii=False),flush=True)
