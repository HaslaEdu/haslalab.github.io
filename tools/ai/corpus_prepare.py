"""Prepare private, traceable chat and textbook corpora without network or model calls.

Example:
  python corpus_prepare.py --input records.jsonl --sources sources.json \
    --output-dir D:/haslalab-private-problem-bank/hasla-ai-corpus/v1 --dataset-version v1

The input must supply speaker roles explicitly. Plain text remains text; this module
never invents question/answer pairs from a book or turns every comment into an answer.
Only reviewed examples whose sources explicitly allow training enter split exports.
Unknown rights and pending examples remain in the private normalized inventory.
"""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import re
import unicodedata


SCHEMA_VERSION = 1
TRAIN_RIGHTS = frozenset(("user_provided", "user_authorized", "owned", "licensed", "public_domain"))
REVIEW_STATUSES = frozenset(("approved", "pending", "excluded"))
ROLES = frozenset(("system", "user", "assistant"))
NEAR_THRESHOLD = 0.92
NEAR_CANDIDATES = 48
FINGERPRINT_BUCKET = 8
REPO_ROOT = Path(__file__).resolve().parents[2]


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def clean_text(value):
    if not isinstance(value, str):
        raise ValueError("content must be a string")
    text = unicodedata.normalize("NFC", value).replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(c for c in text if c in "\n\t" or not unicodedata.category(c).startswith("C"))
    return "\n".join(line.rstrip() for line in text.split("\n")).strip()


def comparison_text(text):
    return re.sub(r"\W+", "", unicodedata.normalize("NFKC", text).casefold())


def source_map(raw):
    if isinstance(raw, dict) and isinstance(raw.get("sources"), list):
        raw = raw["sources"]
    if isinstance(raw, list):
        out = {}
        for row in raw:
            if not isinstance(row, dict) or not row.get("id"):
                raise ValueError("each source needs an id")
            key = str(row["id"])
            if key in out:
                raise ValueError("duplicate source id: " + key)
            out[key] = dict(row)
        return out
    if isinstance(raw, dict) and all(isinstance(v, dict) for v in raw.values()):
        return {str(k): {**v, "id": str(k)} for k, v in raw.items()}
    raise ValueError("sources must be an id/object mapping or an array")


def split_text(text, size=6000, overlap=300):
    if size < 100 or overlap < 0 or overlap >= size:
        raise ValueError("chunk size must be >=100 and 0 <= overlap < size")
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = text.rfind("\n\n", start + size // 2, end)
            if boundary > start:
                end = boundary
        part = text[start:end]
        if part.strip():
            yield start, end, part
        if end == len(text):
            break
        start = max(start + 1, end - overlap)


def _messages(row):
    messages = row.get("messages")
    if messages is None and "question" in row and "answer" in row:
        # An explicit question/answer schema is different from an untyped comment tree.
        messages = [{"role": "user", "content": row["question"]},
                    {"role": "assistant", "content": row["answer"]}]
    if not isinstance(messages, list) or not messages:
        raise ValueError("chat input needs explicit messages or question/answer")
    out = []
    for i, message in enumerate(messages):
        if not isinstance(message, dict) or message.get("role") not in ROLES:
            raise ValueError("invalid or missing speaker role")
        role, content = message["role"], clean_text(message.get("content"))
        if not content:
            raise ValueError("empty message")
        if role == "system" and i != 0:
            raise ValueError("system message is permitted only at the beginning")
        if out and out[-1]["role"] == role:
            raise ValueError("consecutive messages have the same role; resolve the thread explicitly")
        out.append({"role": role, "content": content})
    dialogue = [m for m in out if m["role"] != "system"]
    if not dialogue or dialogue[0]["role"] != "user" or dialogue[-1]["role"] != "assistant":
        raise ValueError("training dialogue must start with user and end with assistant")
    return out


def normalize(records, sources, dataset_version, chunk_chars=6000, overlap=300):
    """Return validated records; no source text is discarded for unknown usage rights."""
    sources = source_map(sources)
    result, seen_ids = [], set()
    for row in records:
        if not isinstance(row, dict):
            raise ValueError("each record must be an object")
        metadata = row.get("metadata") or {}
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be an object")
        ids = row.get("source_ids", metadata.get("source_ids"))
        if ids is None:
            sid = row.get("source_id", metadata.get("source_id"))
            ids = [sid] if sid is not None else []
        if not isinstance(ids, list) or not ids or any(not isinstance(x, (str, int)) for x in ids):
            raise ValueError("each record needs nonempty source_ids or source_id")
        ids = sorted(set(map(str, ids)))
        for sid in ids:
            if sid not in sources:
                sources[sid] = {"id": sid, "rights_status": "unknown", "allowed_uses": []}
        review = row.get("review_status", metadata.get("review_status", "pending"))
        if review not in REVIEW_STATUSES:
            raise ValueError("unknown review_status: " + str(review))
        has_chat = "messages" in row or "question" in row or "answer" in row
        if has_chat and "text" in row:
            raise ValueError("record cannot contain both chat and textbook text")
        if has_chat:
            messages = _messages(row)
            payload = {"messages": messages}
            content = "\n".join(m["role"] + ":" + m["content"] for m in messages)
            parts = [(None, None, payload, content)]
            role = row.get("role", metadata.get("role", "chat"))
            if role not in ("chat", "solver"):
                raise ValueError("chat role must be chat or solver")
        else:
            text = clean_text(row.get("text"))
            if not text:
                raise ValueError("empty textbook text")
            parts = [(start, end, {"text": part}, part) for start, end, part in split_text(text, chunk_chars, overlap)]
            role = "text"
        parent_id = str(row.get("id") or digest(json.dumps({"sources": ids, "parts": parts}, ensure_ascii=False, sort_keys=True))[:24])
        namespace = str(row.get("source", metadata.get("source", sources[ids[0]].get("source", ""))))
        for i, (start, end, payload, content) in enumerate(parts):
            record_id = parent_id if len(parts) == 1 else parent_id + ":chunk:" + str(i)
            if record_id in seen_ids:
                raise ValueError("duplicate record id: " + record_id)
            seen_ids.add(record_id)
            meta = {**metadata, "source_ids": ids, "dataset_version": str(dataset_version),
                    "review_status": review, "role": role, "style": row.get("style", metadata.get("style", "default")),
                    "source": namespace, "parent_record_id": parent_id,
                    "content_hash": digest(content), "rights": [
                        {"source_id": sid, "rights_status": sources[sid].get("rights_status", "unknown"),
                         "allowed_uses": sources[sid].get("allowed_uses", []),
                         "permission_reference": sources[sid].get("permission_reference")}
                        for sid in ids]}
            for key in ("thread_id", "conversation_id", "document_id"):
                if row.get(key, metadata.get(key)) is not None:
                    meta[key] = str(row.get(key, metadata.get(key)))
            if start is not None:
                meta.update({"document_id": meta.get("document_id", parent_id), "char_start": start, "char_end": end})
            result.append({"id": record_id, **payload, "metadata": meta})
    return sorted(result, key=lambda r: r["id"]), sources


class Groups:
    def __init__(self, n):
        self.parents = list(range(n))

    def find(self, x):
        while self.parents[x] != x:
            self.parents[x] = self.parents[self.parents[x]]
            x = self.parents[x]
        return x

    def join(self, a, b):
        a, b = self.find(a), self.find(b)
        self.parents[max(a, b)] = min(a, b)


def record_text(row):
    return row.get("text") if "text" in row else "\n".join(m["role"] + ":" + m["content"] for m in row["messages"])


def quality(text):
    nonspace = [c for c in text if not c.isspace()]
    bad = sum(c in "\ufffd\ufffe\uffff" for c in nonspace)
    alpha = sum(c.isalpha() for c in nonspace)
    symbols = sum(unicodedata.category(c).startswith(("S", "N")) for c in nonspace)
    return {"characters": len(text), "nonspace_characters": len(nonspace),
            "replacement_ratio": round(bad / max(1, len(nonspace)), 5),
            "letter_ratio": round(alpha / max(1, len(nonspace)), 5),
            "math_number_symbol_ratio": round(symbols / max(1, len(nonspace)), 5)}


def fingerprints(text):
    """Bounded candidate generation; actual similarity is checked before grouping.

    Sampling intentionally favors precision over exhaustive near-duplicate recall.
    Shared boilerplate cannot create unbounded pairwise comparison work.
    """
    if len(text) < 80:
        return ()
    width = 48
    return {digest(text[(len(text) - width) * i // 11: (len(text) - width) * i // 11 + width])[:20]
            for i in range(12)}


def assign_splits(records, seed="hasla-corpus-v1", ratios=(0.8, 0.1, 0.1), sources=None):
    """Keep sources, threads, documents, conversations and near duplicates together."""
    if len(ratios) != 3 or any(x < 0 for x in ratios) or abs(sum(ratios) - 1) > 1e-9:
        raise ValueError("split ratios must sum to one")
    records = sorted(records, key=lambda r: r["id"])
    groups, key_owner = Groups(len(records)), {}
    canonical, index = [], defaultdict(list)
    for i, row in enumerate(records):
        meta = row["metadata"]
        keys = ["source:" + sid for sid in meta["source_ids"]]
        for key in ("thread_id", "conversation_id", "document_id"):
            if meta.get(key):
                keys.append(key + ":" + meta.get("source", "") + ":" + meta[key])
        text = comparison_text(record_text(row))
        canonical.append(text)
        keys.append("exact:" + digest(text))
        for key in keys:
            if key in key_owner:
                groups.join(i, key_owner[key])
            else:
                key_owner[key] = i
        keys = sorted(fingerprints(text))
        candidates = sorted({j for key in keys for j in index[key]})[:NEAR_CANDIDATES]
        grams = None
        for j in candidates:
            if groups.find(i) == groups.find(j):
                continue
            previous = canonical[j]
            if min(len(text), len(previous)) / max(len(text), len(previous)) < NEAR_THRESHOLD:
                continue
            if grams is None:
                grams = {text[k:k + 5] for k in range(len(text) - 4)}
            other = {previous[k:k + 5] for k in range(len(previous) - 4)}
            if len(grams & other) / max(1, len(grams | other)) >= NEAR_THRESHOLD:
                groups.join(i, j)
        for key in keys:
            if len(index[key]) < FINGERPRINT_BUCKET:
                index[key].append(i)
    members = defaultdict(list)
    for i, row in enumerate(records):
        members[groups.find(i)].append(row)
    for rows in members.values():
        # Stable under record ordering and new examples from an existing source.
        source_ids = sorted({sid for row in rows for sid in row["metadata"]["source_ids"]})
        group_id = digest("\n".join(source_ids))[:24]
        n = int(digest(seed + ":" + group_id)[:16], 16) / 2**64
        split = "train" if n < ratios[0] else "validation" if n < sum(ratios[:2]) else "test"
        for row in rows:
            row["metadata"].update({"group_id": group_id, "split": split, "split_seed": seed})
    # Exact duplicate decisions do not depend on input order and prefer approved rows.
    duplicate_groups = defaultdict(list)
    for row, text in zip(records, canonical):
        duplicate_groups[digest(text)].append(row)
    for rows in duplicate_groups.values():
        winner = min(rows, key=lambda r: (export_reason(r, sources) is not None if sources else
                                         r["metadata"]["review_status"] != "approved", r["id"]))
        for row in rows:
            if row is not winner:
                row["metadata"]["duplicate_of"] = winner["id"]
    return records


def export_reason(row, sources):
    meta = row["metadata"]
    if meta["review_status"] != "approved":
        return "review_" + meta["review_status"]
    if meta.get("duplicate_of"):
        return "exact_duplicate"
    if "text" in row:
        q = meta.get("text_quality", quality(row["text"]))
        if q["nonspace_characters"] < 80:
            return "text_too_short"
        if q["replacement_ratio"] > 0.02:
            return "text_encoding_damage"
    for sid in meta["source_ids"]:
        source = sources[sid]
        if source.get("deleted_at") or source.get("excluded"):
            return "source_removed"
        if source.get("rights_status", "unknown") not in TRAIN_RIGHTS:
            return "rights_unknown"
        uses = source.get("allowed_uses", [])
        if not isinstance(uses, list) or "train" not in uses:
            return "training_not_in_allowed_uses"
    return None


def patterns(records):
    """Aggregate fixed linguistic features, never snippets copied from a corpus."""
    roles, styles, turns, endings = Counter(), Counter(), Counter(), Counter()
    lengths = []
    for row in records:
        meta = row["metadata"]
        roles[meta["role"]] += 1
        styles[str(meta["style"])] += 1
        if "messages" not in row:
            continue
        turns[str(len([m for m in row["messages"] if m["role"] != "system"]))] += 1
        for msg in row["messages"]:
            if msg["role"] != "assistant":
                continue
            content = msg["content"]
            lengths.append(len(content))
            for label, regex in (("casual_im_ham", r"(?:임|함)[.!?…\s]*$"),
                                 ("casual_directive", r"(?:하셈|해봐|해 봐)[.!?…\s]*$"),
                                 ("polite", r"(?:요|니다)[.!?…\s]*$"),
                                 ("laughter", r"ㅋ{2,}|ㅎ{2,}"), ("followup_question", r"[?？]")):
                if re.search(regex, content):
                    endings[label] += 1
    return {"records": len(records), "roles": dict(sorted(roles.items())), "styles": dict(sorted(styles.items())),
            "dialogue_turns": dict(sorted(turns.items())), "assistant_features": dict(sorted(endings.items())),
            "assistant_length": {"count": len(lengths), "mean": round(sum(lengths) / len(lengths), 2) if lengths else 0,
                                 "max": max(lengths, default=0)}}


def prepare_corpus(records, sources, dataset_version, seed="hasla-corpus-v1", chunk_chars=6000, overlap=300):
    rows, sources = normalize(records, sources, dataset_version, chunk_chars, overlap)
    for row in rows:
        if "text" in row:
            row["metadata"]["text_quality"] = quality(row["text"])
    rows = assign_splits(rows, seed, sources=sources)
    exports = {split + "." + role: [] for split in ("train", "validation", "test") for role in ("chat", "solver", "text")}
    reasons = Counter()
    for row in rows:
        reason = export_reason(row, sources)
        row["metadata"]["training_eligible"] = reason is None
        if reason:
            row["metadata"]["export_exclusion"] = reason
            reasons[reason] += 1
        else:
            exports[row["metadata"]["split"] + "." + row["metadata"]["role"]].append(row)
    manifest = {"schema_version": SCHEMA_VERSION, "dataset_version": str(dataset_version), "split_seed": seed,
                "split_ratios": {"train": 0.8, "validation": 0.1, "test": 0.1},
                "records": len(rows), "groups": len({r["metadata"]["group_id"] for r in rows}),
                "near_duplicates": {"method": "bounded_fingerprints_then_character_shingle_jaccard",
                                    "minimum_jaccard": NEAR_THRESHOLD, "max_candidates_per_record": NEAR_CANDIDATES,
                                    "exhaustive": False},
                "exports": {k: len(v) for k, v in exports.items()}, "exclusions": dict(sorted(reasons.items())),
                "sources": [sources[k] for k in sorted(sources)]}
    return {"records": rows, "exports": exports, "manifest": manifest, "patterns": patterns(rows)}


def write_corpus(prepared, output_dir, forbidden_root=REPO_ROOT):
    output = Path(output_dir).resolve()
    if output == Path(forbidden_root).resolve() or Path(forbidden_root).resolve() in output.parents:
        raise ValueError("private corpus output must be outside the source repository")
    if output.exists() and any(output.iterdir()):
        raise ValueError("output directory must be empty; choose a new dataset version")
    output.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, rows in {"normalized": prepared["records"], **prepared["exports"]}.items():
        path = output / (name + ".jsonl")
        payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
        path.write_text(payload, encoding="utf-8", newline="\n")
        files[path.name] = {"sha256": digest(payload), "records": len(rows)}
    manifest = {**prepared["manifest"], "files": files}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "patterns.json").write_text(json.dumps(prepared["patterns"], ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="private JSONL with explicit messages or textbook text")
    parser.add_argument("--sources", required=True, help="source provenance and usage JSON")
    parser.add_argument("--output-dir", required=True, help="new private output directory outside this repository")
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--split-seed", default="hasla-corpus-v1")
    parser.add_argument("--chunk-chars", type=int, default=6000)
    parser.add_argument("--overlap", type=int, default=300)
    args = parser.parse_args(argv)
    with open(args.input, encoding="utf-8-sig") as stream:
        records = [json.loads(line) for line in stream if line.strip()]
    sources = json.loads(Path(args.sources).read_text(encoding="utf-8-sig"))
    prepared = prepare_corpus(records, sources, args.dataset_version, args.split_seed, args.chunk_chars, args.overlap)
    manifest = write_corpus(prepared, args.output_dir)
    # Safe summary: never print source text or local source filenames.
    print(json.dumps({"output_dir": str(Path(args.output_dir).resolve()), "records": manifest["records"],
                      "groups": manifest["groups"], "exports": manifest["exports"], "exclusions": manifest["exclusions"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
