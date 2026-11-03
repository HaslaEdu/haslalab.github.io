"""R4 private adapter; the original2023guard is retained byte-identically."""
from pathlib import Path
import sys
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE.parent/'common'))
from r4_guard import output_directory,validate_write,assert_all_inputs
PROOF_ROOT=output_directory(BASE,2023)
CACHE_ROOT=BASE/'composer/ortvay2023-font-cache'
def assert_protected_editions():return assert_all_inputs()
def validate_paths(page,plan,target,composer,overrides=None,layout_only=False):
    if layout_only:raise ValueError('R4 experimental authorization is only for the five reviewable proofs')
    assert Path(composer).resolve()==BASE/'composer/natural_plan_compose_ortvay2023_final.py'
    cfg,value=validate_write(BASE,plan,target,overrides)
    assert value['page']==page
    return True
