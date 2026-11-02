"""Local data outputs must not become public source-control content."""
from pathlib import Path
import json
import subprocess

PUBLIC_ROOT = Path(__file__).resolve().parents[2]


def source_path(value, mapping_file=None):
    """Map historical input prefixes at read time without rewriting manifests."""
    original = Path(value)
    if mapping_file is None or not Path(mapping_file).exists():
        return original
    mapping = json.loads(Path(mapping_file).read_text(encoding="utf-8-sig"))
    if mapping.get("version") != 1 or not isinstance(mapping.get("prefixes"), list):
        raise ValueError("Invalid runtime source-path mapping")
    normalized = str(value).replace("\\", "/")
    for item in sorted(mapping["prefixes"], key=lambda item: len(item["from"]), reverse=True):
        prefix = str(item["from"]).replace("\\", "/").rstrip("/")
        target = Path(item["to"])
        if not prefix or not target.is_absolute():
            raise ValueError("Runtime path mappings require explicit absolute roots")
        if normalized.casefold() == prefix.casefold() or normalized.casefold().startswith(prefix.casefold() + "/"):
            tail = normalized[len(prefix):].lstrip("/")
            resolved = (target / tail).resolve()
            if not resolved.is_relative_to(target.resolve()):
                raise ValueError("Mapped source path escapes its configured root")
            return resolved
    return original


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
