"""Serialize memory-heavy local jobs without services or automatic retries.

The lock file is deliberately retained: deleting it could give waiting processes
different file identities. The operating system releases the lock on process exit.
"""
import argparse
import errno
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from private_paths import private_directory

if os.name == 'nt':
    import msvcrt
else:
    import fcntl


def acquire(handle):
    handle.seek(0)
    if os.name == 'nt':
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def release(handle):
    handle.seek(0)
    if os.name == 'nt':
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def run_locked(lock_file, command, *, label='local-job', wait_seconds=1800):
    if not command or not 0 <= wait_seconds <= 7200:
        raise ValueError('A command and a wait limit in 0..7200 seconds are required')
    lock_file = private_directory(lock_file.parent) / lock_file.name
    if lock_file.is_symlink():
        raise ValueError('Refusing a resource-lock symlink')
    started = time.monotonic()
    next_notice = started + 20
    with lock_file.open('a+b', buffering=0) as handle:
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b'\0')
        while True:
            try:
                acquire(handle)
                break
            except OSError as error:
                if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                now = time.monotonic()
                if now - started >= wait_seconds:
                    raise TimeoutError('Timed out waiting for the shared resource lock') from error
                if now >= next_notice:
                    print(json.dumps({'resource_lock': 'waiting', 'label': label}), flush=True)
                    next_notice = now + 20
                time.sleep(min(.2, max(.001, wait_seconds - (now - started))))
        print(json.dumps({'resource_lock': 'acquired', 'label': label,
                          'waited_seconds': round(time.monotonic() - started, 2)}), flush=True)
        try:
            # No shell interpolation, hidden provider calls, or failure retries.
            return subprocess.run(command, check=False).returncode
        finally:
            release(handle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock-file', required=True, type=Path)
    parser.add_argument('--label', default='local-job')
    parser.add_argument('--wait-seconds', type=float, default=1800)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    return run_locked(args.lock_file, command, label=args.label,
                      wait_seconds=args.wait_seconds)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, TimeoutError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
