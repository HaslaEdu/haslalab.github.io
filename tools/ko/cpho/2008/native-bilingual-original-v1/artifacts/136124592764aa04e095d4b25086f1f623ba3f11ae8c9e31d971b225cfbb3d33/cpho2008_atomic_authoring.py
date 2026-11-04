"""Atomic private authoring writes; retain an existing plan on disk failure."""
import os
from pathlib import Path

def atomic_text(path, text, encoding='utf8'):
    path=Path(path)
    raw=text.encode(encoding)
    temp=path.with_name(path.name+'.atomic-writing')
    with temp.open('wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if temp.read_bytes()!=raw:
        raise IOError('Private authoring temporary file differs')
    os.replace(temp,path)
    return len(text)
