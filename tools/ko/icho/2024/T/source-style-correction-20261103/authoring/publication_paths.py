"""Use the mutable release worktree while retaining old reference worktrees."""
from pathlib import Path
import json
B=Path(__file__).resolve().parents[1]
PARENT=Path('C:/Users/andre/CodexWork/HaslaLab').resolve()
LEGACY=PARENT/'haslalab-poi-archive-publication'
ACTIVE=PARENT/'haslalab-poi-style-publication'

def active_root():
 config=B/'engine/style-publication-workspace.json'
 assert config.is_file(),'Missing isolated publication workspace configuration'
 state=json.loads(config.read_text('utf8'))
 assert state['schema']=='isolated-style-publication-worktree-v1'
 assert Path(state['original_read_only_reference_worktree']).resolve()==LEGACY
 root=Path(state['publication_root']).resolve()
 assert root==ACTIVE and root!=LEGACY,'Protected reference worktree cannot be used for publication'
 assert root.is_dir() and (root/'.git').is_file()
 return root
