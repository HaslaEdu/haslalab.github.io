"""Bounded anonymous reads of the public DC frontend's comment-list operation.

The normal public page must supply its nonce and refer to the reviewed official
script. Only viewComments' /board/comment/ read operation exists here. No source
text, names, IPs, cookies, nonces, or guessed endpoints are written to disk.
No GPU/model/provider credentials or training/export functions are used.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib import error, parse, request

import community_collect as community

ORIGIN = "https://gall.dcinside.com"
READ_ENDPOINT = ORIGIN + "/board/comment/"
READ_FIELDS = frozenset(("id", "no", "cmt_id", "cmt_no", "focus_cno", "focus_pno", "e_s_n_o",
                         "comment_page", "sort", "prevCnt", "_GALLTYPE_", "secret_article_key", "clean", "nptest"))
POLICY_VERSION = "exclude-bugiu-v1"
# Observed from ordinary public posts on 2026-11-04; version changes fail closed.
REVIEWED_SCRIPT_SHA256 = "b2f074c6756ddb428f4ddad57679f898dac6b393ea53617bfb4b1f789ba6b99a"
MAX_POSTS = 1000
ACCESS_BLOCKS = frozenset(("http_401", "http_403", "http_429", "challenge_or_access_block", "login_required"))
DENIED_THREADS = frozenset((("physics", "391"), ("physics", "380")))


class ReadError(ValueError):
    """A fixed safe category; never an upstream response or exception string."""


def require(condition, code):
    if not condition:
        raise ReadError(code)


def private_path(value):
    path = Path(value).expanduser().resolve()
    require(not any(part.casefold().startswith("onedrive") for part in path.parts)
            and not any((parent / ".git").exists() for parent in (path, *path.parents)), "private_path_required")
    return path


def write_atomic(path, value):
    temporary = path.with_name(path.name + ".partial")
    created = False
    try:
        with temporary.open("xb") as stream:
            created = True
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if created and temporary.exists():
            temporary.unlink()


def gallery_url(url, kind, gallery_id):
    """Reject out-of-scope redirects before following them, including a denied gallery."""
    try:
        parsed = parse.urlsplit(url)
        query = parse.parse_qs(parsed.query)
        require(parsed.scheme == "https" and parsed.hostname == "gall.dcinside.com"
                and parsed.port in (None, 443) and parsed.username is None and parsed.password is None,
                "outside_public_origin")
    except (ValueError, AttributeError):
        raise ReadError("outside_public_origin") from None
    require(gallery_id != "physicalscience", "user_excluded_gallery")
    require(query.get("id") == [gallery_id] and all(len(values) == 1 for values in query.values()), "gallery_binding_mismatch")
    if kind == "listing":
        require(parsed.path.rstrip("/") in ("/board/lists", "/mgallery/board/lists", "/mini/board/lists")
                and not set(query) - {"id", "page"}, "listing_path_invalid")
        if "page" in query:
            require(re.fullmatch(r"[0-9]+", query["page"][0]) and int(query["page"][0]) >= 1, "listing_page_invalid")
    else:
        require(kind == "post" and parsed.path in ("/board/view/", "/mgallery/board/view/", "/mini/board/view/")
                and not set(query) - {"id", "no"} and re.fullmatch(r"[0-9]+", query.get("no", [""])[0]), "post_path_invalid")
        require((gallery_id, str(int(query["no"][0]))) not in DENIED_THREADS, "previously_denied_individual_url")
    return url


class Inputs(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base, self.values, self.scripts, self.identity_names = base, {}, [], []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "input" and values.get("id") in ("id", "no", "e_s_n_o", "secret_article_key", "_GALLTYPE_"):
            self.values[values["id"]] = values.get("value", "")
        if tag == "script" and values.get("src"):
            self.scripts.append(parse.urljoin(self.base, values["src"]))
        if values.get("data-nick"):
            self.identity_names.append(community.normalized_author(values["data-nick"]))


class Listing(HTMLParser):
    """Actual regular table rows; listed excluded authors are skipped before GET."""
    def __init__(self, base, gallery):
        super().__init__(convert_charrefs=True)
        self.base, self.gallery, self.rows, self.stack, self.current = base, gallery, [], [], None
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        classes = set(values.get("class", "").split())
        if tag == "tr" and "ub-content" in classes:
            self.current = {"urls": [], "number": [], "count": [], "author_checked": False, "excluded": False}
            self.rows.append(self.current)
        field = None
        if self.current is not None:
            if tag == "a" and values.get("href"):
                url = community.canonical_thread("dcinside", values["href"], self.base)
                if url and parse.parse_qs(parse.urlsplit(url).query).get("id") == [self.gallery]:
                    self.current["urls"].append(url)
            if "gall_writer" in classes and values.get("data-nick"):
                name = community.normalized_author(values["data-nick"])
                self.current.update(author_checked=bool(name), excluded=name in community.EXCLUDED_AUTHORS)
            field = "number" if "gall_num" in classes else "count" if "reply_num" in classes else None
        if tag not in ("br", "img", "input", "meta", "link", "hr", "wbr", "source"):
            self.stack.append((tag, field))
    def handle_data(self, value):
        if self.current is not None:
            for _, field in self.stack:
                if field:
                    self.current[field].append(value)
    def handle_endtag(self, tag):
        if tag == "tr": self.current = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break
    def candidates(self):
        result = []
        for row in self.rows:
            count = re.sub(r"\D", "", "".join(row["count"]))
            if ("".join(row["number"]).strip().isdecimal() and count and int(count) > 0
                    and row["urls"] and not row["excluded"]):
                result.append(row["urls"][0])
        return list(dict.fromkeys(result))


class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
    def handle_data(self, value):
        self.parts.append(value)
    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.parts.append("\n")
    def value(self):
        return re.sub(r"[^\S\n]+", " ", "".join(self.parts)).strip()


def visible_comments(rows):
    """Apply the reviewed renderer's visibility/root grouping; discard identities."""
    require(isinstance(rows, list) and len(rows) <= 500, "comment_schema_invalid")
    entries, names, bad_groups, unknown_groups, seen_ids = [], [], set(), set(), set()
    for index, row in enumerate(rows):
        require(isinstance(row, dict) and row.get("del_yn") in ("N", "Y"), "comment_visibility_unknown")
        if row["del_yn"] == "Y" or row.get("nicktype") == "COMMENT_BOY":
            continue
        depth = str(row.get("depth"))
        number, parent = str(row.get("no", "")), row.get("c_no")
        require(depth in ("0", "1") and re.fullmatch(r"[0-9]+", number), "comment_relationship_unknown")
        require(number not in seen_ids, "duplicate_comment_id")
        seen_ids.add(number)
        if depth == "0":
            require(parent in (None, "", 0, "0"), "comment_root_relationship_invalid")
            group, parent_id = number, None
        else:
            require(isinstance(parent, (str, int)) and not isinstance(parent, bool)
                    and re.fullmatch(r"[1-9][0-9]*", str(parent)), "comment_parent_unknown")
            group, parent_id = str(parent), str(parent)
        name = community.normalized_author(row.get("name") if isinstance(row.get("name"), str) else "")
        checked, excluded = bool(name), name in community.EXCLUDED_AUTHORS
        names.append(name)
        if excluded:
            bad_groups.add(group)
        if not checked:
            unknown_groups.add(group)
        memo = row.get("memo")
        require(isinstance(memo, str) and len(memo) <= 20000, "comment_text_schema_invalid")
        # Media/voice/DCcon are displayed by the frontend but are not text pairs.
        text = ""
        if not re.search(r"<(?:img|iframe|video|audio)|dccon|디시콘", memo, re.I) and not row.get("voice") and not row.get("vr_player"):
            stripped = Text()
            stripped.feed(memo)
            text = stripped.value()
        entries.append({"api_index": index, "comment_id": number, "parent_comment_id": parent_id,
                        "root_comment_id": group, "depth": int(depth), "text": text,
                        "author_checked": checked, "author_excluded": excluded})
    root_ids = {entry["comment_id"] for entry in entries if entry["depth"] == 0}
    for entry in entries:
        if entry["depth"] == 1 and entry["root_comment_id"] not in root_ids:
            unknown_groups.add(entry["root_comment_id"])
    retained = [entry for entry in entries if entry["root_comment_id"] not in bad_groups | unknown_groups]
    return retained, {"returned_rows": len(rows), "active_non_bot_rows": len(entries),
                      "excluded_author_branches": len(bad_groups), "unknown_author_or_parent_branches": len(unknown_groups)}, names


def redact(text, names=()):
    value = re.sub(r"https?://\S+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b(?:\d{1,3}\.){3}\d{1,3}\b|\b01[016789][ -]?\d{3,4}[ -]?\d{4}\b|@\S+", "[identifier omitted]", text)
    for name in names:
        if len(name) >= 3:
            value = value.replace(name, "[source identity omitted]")
    return value


class PublicReader:
    def __init__(self, *, client=None, stop_file=None, access_stop_file=None, expected_script_sha256=REVIEWED_SCRIPT_SHA256):
        self.stop_file = private_path(stop_file) if stop_file else None
        self.access_stop_file = private_path(access_stop_file) if access_stop_file else None
        self.blocked = False
        self.client = client or community.BoundedClient(interval=5, max_bytes=2097152, timeout=15,
            opener=request.build_opener(community.NoRedirect(), request.HTTPCookieProcessor(CookieJar())))
        self.expected_script_sha256 = expected_script_sha256
        self.verified_scripts = set()
        self.before_request()
        robots = self.client.get(ORIGIN + "/robots.txt")
        # 404/410 are unavailable robots files, per RFC9309 2.3.1.3. Access
        # denials still stop immediately; network/server errors fail closed.
        if robots.status in (404, 410) and not robots.failure:
            self.robots = ""
        else:
            self.check(robots)
            self.robots = robots.text()
        require(community.robots_decision(self.robots, READ_ENDPOINT)["allowed"], "robots_denied")

    def before_request(self):
        require(not self.blocked, "source_already_stopped")
        require(not self.access_stop_file or not self.access_stop_file.exists(), "previous_source_access_block")
        require(not self.stop_file or not self.stop_file.exists(), "training_collection_window_ended")

    def check(self, response):
        reason = community.response_block_reason(response)
        if reason:
            if reason in ACCESS_BLOCKS or reason == "robots_denied":
                self.blocked = True
                if self.access_stop_file:
                    write_atomic(self.access_stop_file, json.dumps({"source": ORIGIN, "reason": reason,
                        "http_status": response.status, "no_retry_or_alternate_route": True}).encode())
            raise ReadError(reason)

    def get(self, url, *, gallery_id=None, kind=None, script=False):
        for _ in range(4):
            self.before_request()
            if script:
                parsed = parse.urlsplit(url)
                require(parsed.scheme == "https" and parsed.netloc == "gall.dcinside.com"
                        and parsed.path == "/_js/comment.js" and set(parse.parse_qs(parsed.query)) <= {"v"}, "script_url_invalid")
            else:
                gallery_url(url, kind, gallery_id)
            require(community.robots_decision(self.robots, url)["allowed"], "robots_denied")
            response = self.client.get(url)
            if response.status in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                require(location, "redirect_without_location")
                url = parse.urljoin(url, location)
                continue
            self.check(response)
            return response
        raise ReadError("redirect_limit")

    def _read_comment_json(self, payload, referer):
        """There is no generic HTTP mutation interface or configurable endpoint."""
        self.before_request()
        require(isinstance(payload, dict) and set(payload) == READ_FIELDS
                and all(isinstance(value, str) for value in payload.values()), "public_read_payload_invalid")
        gallery_url(referer, "post", payload["id"])
        query = parse.parse_qs(parse.urlsplit(referer).query)
        require(payload["no"] == query["no"][0] and payload["cmt_id"] == payload["id"]
                and payload["cmt_no"] == payload["no"], "public_read_payload_binding_mismatch")
        require(payload["comment_page"] == "1" and payload["sort"] == "D"
                and payload["_GALLTYPE_"] in ("G", "M") and 0 < len(payload["e_s_n_o"]) <= 4096
                and all(payload[key] == "" for key in ("focus_cno", "focus_pno", "prevCnt", "secret_article_key", "clean", "nptest")),
                "public_read_payload_invalid")
        require(community.robots_decision(self.robots, READ_ENDPOINT)["allowed"], "robots_denied")
        if hasattr(self.client, "post_read_fixture"):
            # Explicit dependency injection for offline fixtures only.
            response = self.client.post_read_fixture(READ_ENDPOINT, payload, referer)
        else:
            if self.client.last_request is not None:
                wait = 5 - (self.client.clock() - self.client.last_request)
                if wait > 0:
                    self.client.sleep(wait)
            self.before_request()
            self.client.last_request = self.client.clock()
            req = request.Request(READ_ENDPOINT, data=parse.urlencode(payload).encode(), method="POST", headers={
                "User-Agent": community.USER_AGENT, "Accept": "application/json", "Accept-Encoding": "identity",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Origin": ORIGIN,
                "Referer": referer, "X-Requested-With": "XMLHttpRequest"})
            try:
                with self.client.opener.open(req, timeout=15) as incoming:
                    raw = incoming.read(2097153)
                    response = community.Response(READ_ENDPOINT, incoming.status, raw[:2097152],
                        {key.lower(): value for key, value in incoming.headers.items()}, oversized=len(raw) > 2097152)
            except error.HTTPError as exc:
                response = community.Response(READ_ENDPOINT, exc.code)
                exc.close()
            except Exception:
                raise ReadError("comment_transport_failure_no_retry") from None
            self.client.requests.append({"method": "POST_READ", "url": READ_ENDPOINT, "status": response.status,
                "failure": response.failure, "response_sha256": community.sha256(response.body) if response.body else None})
        self.check(response)
        try:
            decoded = json.loads(response.text())
        except Exception:
            raise ReadError("comment_json_invalid") from None
        require(isinstance(decoded, dict) and (decoded.get("comments") is None or isinstance(decoded["comments"], list)), "comment_schema_invalid")
        return decoded.get("comments") or [], community.sha256(response.body)

    def read_post(self, url, gallery_id):
        post = self.get(url, gallery_id=gallery_id, kind="post")
        page = community.Page("dcinside")
        page.feed(post.text())
        post_filter = page.author_filter()
        require(post_filter["post_author_checked"], "post_author_unverified")
        require(not post_filter["excluded_author_present"], "excluded_post_author")
        fields = Inputs(post.url)
        fields.feed(post.text())
        query = parse.parse_qs(parse.urlsplit(post.url).query)
        require(fields.values.get("id") == query["id"][0] and fields.values.get("no") == query["no"][0], "article_binding_mismatch")
        require(not fields.values.get("secret_article_key"), "secret_article_not_supported")
        nonce = fields.values.get("e_s_n_o", "")
        require(0 < len(nonce) <= 4096 and fields.values.get("_GALLTYPE_") in ("G", "M"), "public_read_parameters_unavailable")
        # The official function prefers document-bound IDs over URL fallback.
        # Do not silently read the wrong thread when a public cross-post aliases it.
        for key, expected in (("article_id", gallery_id), ("comment_id", gallery_id),
                              ("article_no", query["no"][0]), ("comment_no", query["no"][0])):
            marker = re.search(r"\$\(document\)\.data\(\s*['\"]" + key + r"['\"]\s*,", post.text())
            if marker:
                literal = re.match(r"\s*(?:'([^']*)'|\"([^\"]*)\"|([0-9]+))\s*\)", post.text()[marker.end():])
                bound = next((value for value in literal.groups() if value is not None), None) if literal else None
                require(bound is not None and bound in ("", expected), "public_comment_alias_not_supported")
        scripts = [url for url in fields.scripts if parse.urlsplit(url).path == "/_js/comment.js"]
        require(len(scripts) == 1, "official_comment_script_unavailable")
        script_url = scripts[0]
        if script_url not in self.verified_scripts:
            script = self.get(script_url, script=True)
            require(community.sha256(script.body) == self.expected_script_sha256, "official_script_changed_requires_review")
            require(all(value in script.text() for value in ("var viewComments = function(nPage, sType, bScroll)", "url:'/board/comment/'", "var comments = data.comments;")), "official_read_semantics_unverified")
            self.verified_scripts.add(script_url)
        payload = {"id": gallery_id, "no": query["no"][0], "cmt_id": gallery_id, "cmt_no": query["no"][0],
                   "focus_cno": "", "focus_pno": "", "e_s_n_o": nonce, "comment_page": "1", "sort": "D", "prevCnt": "",
                   "_GALLTYPE_": fields.values["_GALLTYPE_"], "secret_article_key": "", "clean": "", "nptest": ""}
        try:
            raw_comments, response_hash = self._read_comment_json(payload, post.url)
        finally:
            payload.clear()
            fields.values.clear()
        comments, counts, names = visible_comments(raw_comments)
        body, title = "\n".join(page.texts("body")), "\n".join(page.texts("title"))
        metadata = {"canonical_url": post.url, "collected_at": datetime.now(timezone.utc).isoformat(),
            "body": community.abstract_features(body), "question_sha256": community.abstract_features(title + "\n" + body)["content_sha256"],
            "comment_response_sha256": response_hash, "comments": [{key: value for key, value in comment.items() if key != "text"} |
                {"content_sha256": community.abstract_features(comment["text"])["content_sha256"], "features": community.abstract_features(comment["text"])} for comment in comments],
            "comment_counts": counts, "official_script_url": script_url, "official_script_sha256": self.expected_script_sha256,
            "read_operation": "official_viewComments_public_comment_list", "comment_read_method": "POST_READ",
            "source_terms_permission_status": "unknown", "training_eligible": False, "raw_content_saved": False,
            "author_filter": {"policy_version": POLICY_VERSION, "post_author_checked": True,
                "selected_reply_authors_checked": bool(comments), "reply_branch_checked": bool(comments), "excluded_author_present": False}}
        metadata["body_has_semantic_text"] = bool(re.sub(r"-\s*dc\s+(?:official\s+)?App\s*$", "", body, flags=re.I).strip())
        names.extend(fields.identity_names)
        preview = {"canonical_url": post.url, "title": redact(title, names)[:180], "body": redact(body, names)[:1200],
            "body_truncated": len(body) > 1200, "root_comments": [{"api_index": comment["api_index"], "text": redact(comment["text"], names)[:400]}
                for comment in comments if comment["depth"] == 0 and comment["text"]][:8]}
        return metadata, preview


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--gallery", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stop-file", required=True)
    parser.add_argument("--max-posts", type=int, default=10)
    parser.add_argument("--exclude-urls", action="append", default=[])
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args(argv)
    require(1 <= args.max_posts <= 50, "finite_batch_limit_invalid")
    catalog_path = private_path(args.catalog)
    require(catalog_path.stat().st_size <= 2097152, "catalog_size_limit")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
    gallery = next((row for row in catalog.get("gallery_catalog", []) if row.get("gallery_id") == args.gallery), None)
    require(gallery is not None, "gallery_not_observed_in_catalog")
    gallery_url(gallery["observed_url"], "listing", args.gallery)
    output = community.private_output_path(private_path(args.output_dir))
    output.mkdir(parents=True, exist_ok=True)
    excluded = community.load_excluded_urls(args.exclude_urls)
    # Exclusion counts are a conservative ceiling, not a claim of corpus size.
    budget = min(args.max_posts, max(0, MAX_POSTS - len(excluded)))
    reader = PublicReader(stop_file=args.stop_file, access_stop_file=output.parent / "dc-access-stop.json")
    listing = reader.get(gallery["observed_url"], gallery_id=args.gallery, kind="listing")
    page = Listing(listing.url, args.gallery)
    page.feed(listing.text())
    urls = [url for url in page.candidates() if url not in excluded]
    navigation = community.Page("dcinside")
    navigation.feed(listing.text())
    observed_pages = []
    for href in navigation.links:
        url = parse.urljoin(listing.url, href)
        try:
            gallery_url(url, "listing", args.gallery)
        except ReadError:
            continue
        if "page" in parse.parse_qs(parse.urlsplit(url).query) and url not in observed_pages:
            observed_pages.append(url)
    report = {"source_gallery": gallery, "batch_limit": budget, "thread_results": [], "new_abstract_records": 0,
              "raw_posts_saved": False, "raw_names_or_ips_saved": False, "nonces_or_cookies_saved": False,
              "training_export_records": 0, "training_performed": False, "source_terms_permission_status": "unknown",
              "observed_listing_url": listing.url, "observed_pagination_urls": observed_pages,
              "listing_response_sha256": community.sha256(listing.body), "listed_excluded_author_rows":sum(row["excluded"] for row in page.rows)}
    stored, consecutive_transport = [], 0
    for url in urls[:budget]:
        status = {"url": url}
        try:
            metadata, preview = reader.read_post(url, args.gallery)
            stored.append(metadata)
            write_atomic(output / "observations.jsonl", "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in stored).encode("utf-8"))
            report["new_abstract_records"] += 1
            consecutive_transport = 0
            status["status"] = "public_body_and_comment_structure_observed"
            if args.preview:
                print(json.dumps({"transient_source_preview_not_saved": preview}, ensure_ascii=True), flush=True)
        except ReadError as exc:
            status["status"] = str(exc)
            transport = str(exc) in community.TRANSPORT_THREAD_FAILURES or str(exc) == "comment_transport_failure_no_retry"
            consecutive_transport = consecutive_transport + 1 if transport else 0
            if (reader.blocked or consecutive_transport >= 3 or str(exc) in
                    ("training_collection_window_ended", "robots_denied", "official_script_changed_requires_review", "official_read_semantics_unverified", "comment_json_invalid", "comment_schema_invalid", "comment_visibility_unknown", "comment_relationship_unknown")):
                report["thread_results"].append(status)
                report["stop_reason"] = "three_consecutive_transport_failures" if consecutive_transport >= 3 else str(exc)
                break
        report["thread_results"].append(status)
        write_atomic(output / "collection-report.json", (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        print(json.dumps({"event": "public_community_collection_progress", "attempted": len(report["thread_results"]),
                          "stored_abstract_records": report["new_abstract_records"], "training_export_records": 0}), flush=True)
    report["request_metadata"] = reader.client.requests
    write_atomic(output / "collection-report.json", (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReadError as exc:
        print(json.dumps({"event": "public_community_collection_stopped", "reason": str(exc), "raw_content_saved": False}), flush=True)
        raise SystemExit(1)
    except Exception:
        print(json.dumps({"event": "public_community_collection_stopped", "reason": "local_configuration_or_reader_failure", "raw_content_saved": False}), flush=True)
        raise SystemExit(1)
