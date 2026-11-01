"""Local data outputs must not become public source-control content."""
from pathlib import Path
import subprocess

PUBLIC_ROOT = Path(__file__).resolve().parents[2]


def private_directory(path):
    path = Path(path).resolve()
    if path.is_relative_to(PUBLIC_ROOT):
        raise ValueError("Book content must not be written inside the public checkout")
    path.mkdir(parents=True, exist_ok=True)
    git = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"], capture_output=True)
    if git.returncode == 0:
        ignored = subprocess.run(["git", "-C", str(path), "check-ignore", "--quiet", str(path)])
        if ignored.returncode:
            raise ValueError("Private data inside a parent Git worktree must be locally ignored")
    return path
