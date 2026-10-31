"""Serialize memory-heavy PDF page workers without changing system settings."""
from pathlib import Path
from contextlib import contextmanager
import os,sys,time,subprocess

LOCK=Path('D:/CodexBuilds/Hasla-original-style-20261031/pdf-render-memory.lock')

@contextmanager
def page_worker():
    LOCK.parent.mkdir(parents=True,exist_ok=True)
    with LOCK.open('a+b')as handle:
        if handle.tell()==0:handle.write(b'0');handle.flush()
        handle.seek(0)
        if os.name=='nt':
            import msvcrt
            while True:
                try:msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1);break
                except OSError:time.sleep(.25)
        else:
            import fcntl
            fcntl.flock(handle.fileno(),fcntl.LOCK_EX)
        try:yield
        finally:
            handle.seek(0)
            if os.name=='nt':msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(handle.fileno(),fcntl.LOCK_UN)

if __name__=='__main__':
    command=sys.argv[1:]
    if command[:1]==['--']:command=command[1:]
    if not command:raise SystemExit('Usage: python tools/pdf_memory_gate.py -- python page_worker.py ...')
    with page_worker():raise SystemExit(subprocess.run(command).returncode)
