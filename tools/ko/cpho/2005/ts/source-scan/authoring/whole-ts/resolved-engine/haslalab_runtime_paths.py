"""Read-time mapping of historical HaslaLab repository paths after migration.

Frozen manifests and unrelated OneDrive projects are never modified.
"""
from pathlib import Path
OLD_BASE='C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술'
NEW_BASE=Path('C:/Users/andre/CodexWork/HaslaLab')
REPOSITORIES={'haslalab','haslalab-translations','haslalab-design-release','haslalab-chem-kmo-exams'}
def map_repository_path(value):
 normalized=str(value).replace('\\','/');prefix=OLD_BASE+'/'
 if normalized.casefold().startswith(prefix.casefold()):
  relative=normalized[len(prefix):];parts=relative.split('/')
  if parts[0].casefold()in REPOSITORIES:
   if '..'in parts:raise ValueError('Historical repository path traversal')
   return NEW_BASE.joinpath(*parts)
 return Path(value)
