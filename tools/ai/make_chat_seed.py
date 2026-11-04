"""Prepare a PRIVATE, assistant-authored chat bootstrap review set.

This file deliberately contains no dialogue examples. Supply an independently
authored private JSON input; never place source conversations in this repository.
The result is synthetic, human-review-pending pilot candidates, not scraped
community data and not approved training exports. No network or model is called.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import corpus_prepare as corpus


def prepare(examples, version="chat-seed-v1-20261104", train_size=64, validation_size=16, test_size=16):
    if not isinstance(examples, list) or not 80 <= len(examples) <= 120:
        raise ValueError("input must contain 80..120 independently authored examples")
    if len(examples) != train_size + validation_size + test_size or not 32 <= train_size <= 64:
        raise ValueError("pilot must have 32..64 train candidates and the requested held-out sizes")
    records, sources, ids, scenarios = [], {}, set(), set()
    for example in examples:
        key = example.get("id")
        scenario = example.get("scenario_id")
        family = example.get("intent_family")
        messages = example.get("messages")
        if not all(isinstance(value, str) and value for value in (key, scenario, family)) or key in ids:
            raise ValueError("each example needs unique id, scenario_id and intent_family")
        if not isinstance(messages, list) or len(messages) not in (2, 4, 6):
            raise ValueError("each conversation needs 2, 4 or 6 explicit user/assistant messages")
        for i, message in enumerate(messages):
            if message.get("role") != ("user" if i % 2 == 0 else "assistant"):
                raise ValueError("dialogue must alternate user and assistant without invented comment roles")
            content = message.get("content")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("messages must contain nonempty authored text")
            if "http://" in content or "https://" in content:
                raise ValueError("bootstrap examples must not invent or embed external links")
        if example.get("style") not in ("polite", "community_casual"):
            raise ValueError("style must be polite or community_casual")
        if example.get("source") != "assistant_authored_bootstrap" or example.get("synthetic") is not True:
            raise ValueError("input must explicitly identify assistant-authored synthetic provenance")
        if example.get("external_quoted_records") != 0:
            raise ValueError("this bootstrap cannot contain external quotations")
        ids.add(key)
        scenarios.add(scenario)
        source_id = "assistant_bootstrap:" + scenario
        sources[source_id] = {"id": source_id, "source": "assistant_authored_bootstrap",
                              "rights_status": "user_authorized", "allowed_uses": ["analysis", "train"],
                              "permission_reference": "session:requested-assistant-authored-bootstrap",
                              "synthetic": True, "human_review_pending": True,
                              "external_quoted_records": 0}
        records.append({"id": key, "source_id": source_id, "source": "assistant_authored_bootstrap",
                        "conversation_id": "intent_family:" + family, "messages": messages,
                        "style": example["style"], "role": "chat", "review_status": "pending",
                        "metadata": {"scenario_id": scenario, "intent_family": family,
                                     "category": example.get("category", "unspecified"),
                                     "synthetic": True, "human_review_pending": True,
                                     "external_quoted_records": 0, "pilot_only": True}})
    if len(scenarios) < 60:
        raise ValueError("at least 60 independently authored scenarios are required")
    normalized, sources = corpus.normalize(records, sources, version)
    expected = {"train": train_size, "validation": validation_size, "test": test_size}
    ratios = tuple(expected[key] / len(examples) for key in ("train", "validation", "test"))
    seed = "assistant-bootstrap-pilot-stratified-v1"
    # Reuse corpus_prepare's source/scenario/family/near-duplicate grouping first.
    # Then stratify WHOLE groups so all eight learning categories are evaluated.
    split_rows = corpus.assign_splits(normalized, seed, ratios, sources)
    grouped = defaultdict(list)
    for row in split_rows:
        grouped[row["metadata"]["group_id"]].append(row)
    by_category = defaultdict(list)
    for group_id, members in grouped.items():
        categories = {row["metadata"]["category"] for row in members}
        if len(categories) != 1:
            raise ValueError("a grouped scenario crosses categories; resolve its intent family explicitly")
        by_category[next(iter(categories))].append(group_id)
    category_count = len(by_category)
    if any(size % category_count for size in expected.values()):
        raise ValueError("requested splits must permit equal category coverage")
    def pick_subset(group_ids, target):
        possibilities = {0: []}
        for group_id in group_ids:
            weight = len(grouped[group_id])
            for total, chosen in list(possibilities.items()):
                if total + weight <= target and total + weight not in possibilities:
                    possibilities[total + weight] = chosen + [group_id]
        if target not in possibilities:
            raise ValueError("cannot stratify while preserving source and intent groups")
        return possibilities[target]
    for category, group_ids in by_category.items():
        remaining = sorted(group_ids, key=lambda key: corpus.digest(seed + ":" + category + ":" + key))
        if sum(len(grouped[key]) for key in remaining) != len(examples) // category_count:
            raise ValueError("authored bootstrap categories must have equal sizes")
        for split in ("test", "validation", "train"):
            chosen = pick_subset(remaining, expected[split] // category_count)
            for group_id in chosen:
                for row in grouped[group_id]:
                    row["metadata"]["split"] = split
            remaining = [key for key in remaining if key not in chosen]
        if remaining:
            raise ValueError("unassigned groups remain")
    candidate = {split: [] for split in expected}
    group_splits, source_splits, scenario_splits, family_splits = defaultdict(set), defaultdict(set), defaultdict(set), defaultdict(set)
    for row in split_rows:
        meta = row["metadata"]
        meta.update({"training_eligible": False, "export_exclusion": "human_review_pending"})
        candidate[meta["split"]].append(row)
        group_splits[meta["group_id"]].add(meta["split"])
        family_splits[meta["intent_family"]].add(meta["split"])
        scenario_splits[meta["scenario_id"]].add(meta["split"])
        for source_id in meta["source_ids"]:
            source_splits[source_id].add(meta["split"])
    if any(len(values) != 1 for mapping in (group_splits, source_splits, scenario_splits, family_splits) for values in mapping.values()):
        raise ValueError("source, scenario or intent family leakage detected")
    manifest = {"schema_version": 1, "dataset_version": version, "source": "assistant_authored_bootstrap",
                "synthetic": True, "human_review_pending": True, "training_performed": False,
                "approved_training_exports": 0, "community_collected_records": 0,
                "community_collection_replaced_or_completed": False, "external_quoted_records": 0,
                "pilot_only": True, "records": len(examples), "independent_scenarios": len(scenarios),
                "intent_families": len(family_splits), "groups": len(group_splits),
                "split_seed": seed, "candidate_splits": expected,
                "source_scenario_family_leakage": 0,
                "categories": dict(sorted(Counter(row["metadata"]["category"] for row in split_rows).items())),
                "styles": dict(sorted(Counter(row["metadata"]["style"] for row in split_rows).items())),
                "dialogue_turns": dict(sorted(Counter(str(len(row["messages"])) for row in split_rows).items())),
                "split_strategy": "corpus_prepare_groups_then_category_stratification",
                "split_categories": {split: dict(sorted(Counter(row["metadata"]["category"] for row in rows).items()))
                                     for split, rows in candidate.items()},
                "sources": list(sources.values())}
    return {"records": split_rows, "candidates": candidate, "manifest": manifest,
            "patterns": corpus.patterns(split_rows)}


def write(prepared, output_dir):
    output = Path(output_dir).expanduser().resolve()
    if output == corpus.REPO_ROOT or corpus.REPO_ROOT in output.parents:
        raise ValueError("authored dialogue output must stay outside the public repository")
    if any((parent / ".git").exists() for parent in (output, *output.parents)):
        raise ValueError("private output must be outside every Git checkout")
    if any(part.casefold() == "onedrive" for part in output.parts):
        raise ValueError("HaslaLab private development output must remain outside OneDrive")
    if output.exists() and any(output.iterdir()):
        raise ValueError("choose a new or empty output directory")
    output.mkdir(parents=True, exist_ok=True)
    files = {}
    datasets = {"normalized.review-pending": prepared["records"],
                **{"pilot-candidate." + key: values for key, values in prepared["candidates"].items()}}
    for name, rows in datasets.items():
        payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
        path = output / (name + ".jsonl")
        path.write_text(payload, encoding="utf-8")
        files[path.name] = {"records": len(rows), "sha256": corpus.digest(payload)}
    # Empty approved exports preserve the existing review gate.
    for split in ("train", "validation", "test"):
        name = split + ".chat.jsonl"
        (output / name).write_text("", encoding="utf-8")
        files[name] = {"records": 0, "sha256": corpus.digest("")}
    manifest = {**prepared["manifest"], "files": files}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "patterns.json").write_text(json.dumps(prepared["patterns"], ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="private JSON array with authored examples")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--dataset-version", default="chat-seed-v1-20261104")
    args = parser.parse_args(argv)
    examples = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    prepared = prepare(examples, args.dataset_version)
    manifest = write(prepared, args.output_dir)
    print(json.dumps({key: manifest[key] for key in ("records", "independent_scenarios", "intent_families",
                     "candidate_splits", "human_review_pending", "approved_training_exports",
                     "community_collected_records", "training_performed")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
