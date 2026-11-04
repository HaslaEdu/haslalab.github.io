"""CPU-only bounded collection into an EXISTING verified-private W&B project.

Only abstract patterns and a report enter the artifact. No raw posts, training
pairs, model calls, GPU credentials, public Actions artifacts, or project access
changes. --preflight validates configuration only and performs no network calls.

Environment: WANDB_API_KEY; HASLA_PATTERN_EXCLUDED_URLS (JSON URL array);
HASLA_PATTERN_CURSORS (JSON source/URL mapping); HASLA_PATTERN_OBSERVED_LISTING_URLS
(JSON source/array mapping proving cursor observations). Optional SOURCES,
MAX_POSTS, MAX_PAGES, MAX_SECONDS and RUN_ID use the HASLA_PATTERN_ prefix.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib import error, request

import community_collect as collector


PROJECT = "hasla-ai-private-training"
ARTIFACT_TYPE = "dataset-pattern"
GRAPHQL = "https://api.wandb.ai/graphql"


class CollectionError(ValueError):
    """Safe fixed-category failure; never include upstream bodies or credentials."""


def configuration(env):
    if not env.get("WANDB_API_KEY"):
        raise CollectionError("missing_wandb_credential")
    if env.get("RUNPOD_API_KEY") or env.get("HF_TOKEN") or env.get("HUGGING_FACE_HUB_TOKEN"):
        raise CollectionError("cpu_collection_job_must_not_receive_gpu_or_model_credentials")
    def decoded(name, default):
        try:
            return json.loads(env.get(name, json.dumps(default)))
        except (TypeError, json.JSONDecodeError):
            raise CollectionError("invalid_configuration_json") from None
    sources = [x.strip() for x in env.get("HASLA_PATTERN_SOURCES", "orbi,dcinside").split(",") if x.strip()]
    if not sources or len(sources) != len(set(sources)) or any(x not in ("orbi", "dcinside") for x in sources):
        raise CollectionError("invalid_collection_sources_reddit_remains_previously_blocked")
    exclusions = decoded("HASLA_PATTERN_EXCLUDED_URLS", [])
    cursors = decoded("HASLA_PATTERN_CURSORS", {})
    proof = decoded("HASLA_PATTERN_OBSERVED_LISTING_URLS", {})
    if not isinstance(exclusions, list) or len(exclusions) > 10000:
        raise CollectionError("invalid_exclusion_list")
    canonical = set()
    for url in exclusions:
        if not isinstance(url, str):
            raise CollectionError("invalid_exclusion_url")
        valid = next((value for source_id, source in collector.DEFAULT_SOURCES.items()
                      if (value := collector.canonical_thread(source_id, url, source["seed"]))), None)
        if valid is None:
            raise CollectionError("invalid_exclusion_url")
        canonical.add(valid)
    if not isinstance(cursors, dict) or not isinstance(proof, dict):
        raise CollectionError("invalid_cursor_configuration")
    for source_id, url in cursors.items():
        known = proof.get(source_id, [])
        if (source_id not in sources or not isinstance(url, str) or not isinstance(known, list)
                or url not in known or not collector.observed_listing_link(source_id, url, collector.DEFAULT_SOURCES[source_id]["seed"])):
            raise CollectionError("cursor_without_observed_url_evidence")
    numbers = {}
    for name, default, lower, upper in (("MAX_POSTS", 50, 1, 50), ("MAX_PAGES", 3, 1, 3), ("MAX_SECONDS", 600, 60, 900)):
        try:
            number = int(env.get("HASLA_PATTERN_" + name, str(default)))
        except (TypeError, ValueError):
            raise CollectionError("invalid_collection_limit") from None
        if not lower <= number <= upper:
            raise CollectionError("invalid_collection_limit")
        numbers[name.lower()] = number
    run_id = env.get("HASLA_PATTERN_RUN_ID") or ("community-patterns-" + env.get("GITHUB_RUN_ID", "manual") + "-" + env.get("GITHUB_RUN_ATTEMPT", "1"))
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", run_id):
        raise CollectionError("invalid_run_identifier")
    return {"sources": sources, "exclude_urls": canonical, "listing_cursors": cursors,
            "run_id": run_id, **numbers}


class PrivateWandb:
    def __init__(self, api_key):
        self._key = api_key

    def query(self, query, variables=None):
        body = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
        auth = base64.b64encode(("api:" + self._key).encode("utf-8")).decode("ascii")
        req = request.Request(GRAPHQL, data=body,
                              headers={"Authorization": "Basic " + auth, "Content-Type": "application/json"})
        try:
            with request.urlopen(req, timeout=20) as response:
                data = json.loads(response.read(131073))
        except error.HTTPError as exc:
            status = exc.code
            exc.close()
            raise CollectionError("wandb_http_" + str(status)) from None
        except (error.URLError, OSError, ValueError):
            raise CollectionError("wandb_read_failed") from None
        if not isinstance(data, dict) or data.get("errors") or not isinstance(data.get("data"), dict):
            raise CollectionError("wandb_graphql_read_failed")
        return data["data"]

    def entity(self):
        row = self.query("{viewer{entity}}")
        entity = (row.get("viewer") or {}).get("entity")
        if not isinstance(entity, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", entity):
            raise CollectionError("wandb_viewer_entity_unavailable")
        return entity

    def require_private(self, entity):
        row = self.query("query($e:String!,$p:String!){project(name:$p,entityName:$e){name access}}",
                         {"e": entity, "p": PROJECT})
        project = row.get("project")
        if not isinstance(project, dict) or project.get("name") != PROJECT or str(project.get("access", "")).upper() != "PRIVATE":
            raise CollectionError("existing_project_not_verified_private")


class DeadlineClient(collector.BoundedClient):
    def __init__(self, seconds):
        super().__init__()
        self.deadline = time.monotonic() + seconds

    def get(self, url):
        if time.monotonic() >= self.deadline:
            return collector.Response(url, failure="collection_time_limit")
        return super().get(url)


def validate_result(result):
    if result.get("raw_content_saved") is not False or result.get("training_performed") is not False:
        raise CollectionError("unsafe_collection_payload")
    def scan(value):
        if isinstance(value, dict):
            if set(value).intersection(("text", "messages", "question", "answer", "nickname", "author", "ip", "html", "raw_body", "body_text", "content")):
                raise CollectionError("raw_content_not_allowed")
            for item in value.values():
                scan(item)
        elif isinstance(value, list):
            for item in value:
                scan(item)
    scan(result)
    for row in result.get("patterns", []):
        if (row.get("kind") != "abstract_pattern" or not isinstance(row.get("body"), dict)
                or row.get("training_eligible") is not False or
                row.get("metadata", {}).get("rights_status") != "unknown"):
            raise CollectionError("unsafe_pattern_or_fabricated_permission")
        if any(key in row for key in ("text", "messages", "question", "answer", "nickname", "author", "ip")):
            raise CollectionError("raw_content_not_allowed")


def execute(config, service, sdk=None, collect_fn=None):
    entity = service.entity()
    service.require_private(entity)  # Before collection or SDK run creation.
    collect_fn = collect_fn or collector.collect
    with tempfile.TemporaryDirectory(prefix="hasla-private-pattern-") as temporary:
        result = collect_fn(config["sources"], max_posts=config["max_posts"], max_pages=config["max_pages"],
                            exclude_urls=config["exclude_urls"], listing_cursors=config["listing_cursors"],
                            client=DeadlineClient(config["max_seconds"]))
        validate_result(result)
        result.update({"dataset_role": "pattern", "trainable": False,
                       "known_unavailable_sources": {"reddit": {"status": "blocked_robots",
                           "reason": "previously_observed_global_disallow", "rechecked_this_run": False}},
                       "execution": "remote_cpu_collection_no_gpu"})
        output = Path(temporary) / "output"
        report = collector.write_results(result, output)
        hashes = {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                  for name in ("patterns.jsonl", "collection-report.json")}
        service.require_private(entity)  # Recheck immediately before upload.
        if sdk is None:
            import wandb as sdk
        os.environ.update({"WANDB_CONSOLE": "off", "WANDB_SILENT": "true", "WANDB_DISABLE_CODE": "true",
                           "WANDB_DISABLE_GIT": "true", "WANDB_DIR": temporary,
                           "WANDB_CACHE_DIR": str(Path(temporary) / "cache")})
        settings = sdk.Settings(console="off", disable_code=True, disable_git=True, save_code=False,
                                disable_job_creation=True, x_disable_meta=True, x_disable_stats=True)
        run = sdk.init(entity=entity, project=PROJECT, id=config["run_id"], name=config["run_id"],
                       job_type="private-pattern-collection", dir=temporary, settings=settings,
                       config={"dataset_role": "pattern", "trainable": False, "gpu_used": False,
                               "sources": config["sources"], "excluded_url_count": len(config["exclude_urls"]),
                               "max_posts_per_source": config["max_posts"], "max_pages": config["max_pages"]})
        try:
            service.require_private(entity)
            artifact = sdk.Artifact(config["run_id"], type=ARTIFACT_TYPE,
                                    metadata={"dataset_role": "pattern", "trainable": False,
                                              "raw_content_saved": False, "pattern_records": report["pattern_records"]})
            for name in ("patterns.jsonl", "collection-report.json"):
                artifact.add_file(str(output / name), name=name)
            logged = run.log_artifact(artifact, aliases=[])
            logged.wait(timeout=180)
            version, qualified = logged.version, logged.qualified_name
            if not re.fullmatch(r"v[0-9]+", version) or qualified != f"{entity}/{PROJECT}/{config['run_id']}:{version}":
                raise CollectionError("artifact_immutable_version_not_verified")
            summary = {"status": "collection_saved" if report["pattern_records"] else "no_records_report_saved",
                       "pattern_records": report["pattern_records"], "training_performed": False,
                       "dataset_role": "pattern", "trainable": False, "gpu_used": False,
                       "raw_content_saved": False, "artifact": qualified, "artifact_url": logged.url,
                       "artifact_digest": logged.digest, "files_sha256": hashes,
                       "source_status": {row["source_id"]: {"status": row["status"], "reason": row.get("reason"),
                                                            "patterns": row["patterns"]} for row in report["sources"]},
                       "reddit": "previously_blocked_not_rechecked"}
            run.summary["private_collection_result"] = summary
            return summary
        finally:
            run.finish()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = configuration(os.environ)
        if args.preflight or os.environ.get("HASLA_PATTERN_PREFLIGHT_ONLY") == "true":
            print(json.dumps({"event": "private_collection_preflight", "configuration_valid": True,
                              "network_calls": 0, "privacy_verified": False, "upload_performed": False,
                              "training_performed": False, "sources": config["sources"],
                              "excluded_url_count": len(config["exclude_urls"])}))
            return 0
        summary = execute(config, PrivateWandb(os.environ["WANDB_API_KEY"]))
        print(json.dumps({"event": "private_collection_result", **summary}, ensure_ascii=True))
        return 0
    except Exception as exc:
        # SDK/upstream exception messages can contain credentials or request data.
        category = str(exc) if isinstance(exc, CollectionError) else "collection_failed_" + type(exc).__name__
        print(json.dumps({"event": "private_collection_failed", "category": category,
                          "training_performed": False, "gpu_used": False}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
