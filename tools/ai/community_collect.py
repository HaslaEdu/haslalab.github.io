"""Collect bounded, abstract community patterns; never save posts or train a model.

Example (output must be a new private directory outside every Git checkout):
  python tools/ai/community_collect.py --sources dcinside,orbi,reddit \
    --output-dir D:/haslalab-private-problem-bank/hasla-ai/community-probe-v1 \
    --max-posts 10

The default purpose is pattern extraction for later AI development. Explicit AI
training crawler exclusions are respected in addition to this client's own robots
rules. A blocked source still produces a truthful status report. No login,
challenge solving, API guessing, proxy rotation, raw corpus, or training occurs.
"""

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
import unicodedata
from urllib import error, parse, request, robotparser


REPO_ROOT = Path(__file__).resolve().parents[2]
USER_AGENT = "HaslaPatternResearch/0.1 (purpose=abstract-pattern-extraction-for-AI-development)"
AI_AGENTS = ("GPTBot", "ClaudeBot", "anthropic-ai", "Claude-Web", "Google-Extended",
             "Applebot-Extended", "CCBot", "Bytespider", "Amazonbot",
             "Meta-ExternalAgent", "cohere-ai", "PerplexityBot")
DEFAULT_SOURCES = {
    "dcinside": {"origin": "https://gall.dcinside.com",
                 "seed": "https://gall.dcinside.com/mgallery/board/lists/?id=physics"},
    "orbi": {"origin": "https://orbi.kr", "seed": "https://orbi.kr/list"},
    "reddit": {"origin": "https://www.reddit.com", "seed": "https://www.reddit.com/r/learnphysics/"},
}
TRAIN_RIGHTS = frozenset(("owned", "licensed", "public_domain", "user_authorized"))
BLOCKED_PATHS = re.compile(r"/(?:api|login|signin|write|submit|user|users|u|my|feed|message)(?:/|$)", re.I)


def sha256(value):
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def private_output_path(value):
    """Fail before network access, including for symlinked or nested Git outputs."""
    target = Path(value).expanduser().resolve()
    if target == REPO_ROOT or REPO_ROOT in target.parents:
        raise ValueError("output must be private and outside the source repository")
    if any((parent / ".git").exists() for parent in (target, *target.parents)):
        raise ValueError("output must be outside every Git checkout")
    if any(part.casefold() == "onedrive" for part in target.parts):
        raise ValueError("HaslaLab development output must remain outside OneDrive")
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise ValueError("output directory must be new or empty; existing results are never overwritten")
    return target


def source_metadata(source_id, supplied=None):
    """A general user instruction does not establish a site's permission."""
    supplied = supplied or {}
    rights = str(supplied.get("rights_status", "unknown"))
    uses = supplied.get("allowed_uses", [])
    if not isinstance(uses, list) or any(not isinstance(x, str) for x in uses):
        raise ValueError("allowed_uses must be a list of strings")
    reference = supplied.get("permission_reference")
    license_name = supplied.get("license")
    return {"source_id": source_id, "rights_status": rights,
            "allowed_uses": sorted(set(uses)),
            "permission_reference": str(reference)[:1000] if reference else None,
            "license": str(license_name)[:300] if license_name else None,
            "source_training_authorized": bool(rights in TRAIN_RIGHTS and "train" in uses
                                               and (reference or license_name)),
            "review_status": "pending"}


def same_origin_url(url, source):
    try:
        parts = parse.urlsplit(url)
        expected = parse.urlsplit(source["origin"])
        return (parts.scheme == "https" and parts.netloc.casefold() == expected.netloc.casefold()
                and not parts.username and not parts.password and not BLOCKED_PATHS.search(parts.path)
                and parts.port in (None, 443))
    except ValueError:
        return False


def canonical_thread(source_id, href, base):
    source = DEFAULT_SOURCES[source_id]
    url = parse.urljoin(base, href)
    if not same_origin_url(url, source):
        return None
    parts = parse.urlsplit(url)
    if source_id == "dcinside":
        if parts.path not in ("/board/view/", "/mgallery/board/view/", "/mini/board/view/"):
            return None
        query = parse.parse_qs(parts.query)
        gallery, number = query.get("id", [""])[0], query.get("no", [""])[0]
        if not re.fullmatch(r"[A-Za-z0-9_]+", gallery) or not re.fullmatch(r"[0-9]+", number):
            return None
        return source["origin"] + parts.path + "?" + parse.urlencode({"id": gallery, "no": str(int(number))})
    if source_id == "orbi":
        match = re.match(r"^/([0-9]{7,})(?:/|$)", parts.path)
        return source["origin"] + "/000" + str(int(match[1])) if match else None
    match = re.match(r"^/r/([A-Za-z0-9_]+)/comments/([A-Za-z0-9]+)(?:/[^/]*)?/?$", parts.path)
    return (source["origin"] + "/r/" + match[1] + "/comments/" + match[2] + "/") if match else None


def robots_decision(text, url):
    parser = robotparser.RobotFileParser()
    parser.parse(text.splitlines())
    if not parser.can_fetch(USER_AGENT, url):
        return {"allowed": False, "reason": "robots_denied", "denied_agents": ["HaslaPatternResearch"]}
    explicit = {match[1].strip().casefold()
                for match in re.finditer(r"(?im)^\s*user-agent\s*:\s*([^#\r\n]+)", text)}
    denied = [agent for agent in AI_AGENTS
              if agent.casefold() in explicit and not parser.can_fetch(agent, url)]
    if denied:
        return {"allowed": False, "reason": "ai_training_crawler_excluded", "denied_agents": denied}
    return {"allowed": True, "reason": "robots_allowed", "denied_agents": []}


@dataclass
class Response:
    url: str
    status: int = 0
    body: bytes = b""
    headers: dict = field(default_factory=dict)
    failure: str = ""
    oversized: bool = False

    def text(self):
        charset = re.search(r"charset=([\w-]+)", self.headers.get("content-type", ""), re.I)
        encoding = charset[1] if charset else "utf-8"
        try:
            return self.body.decode(encoding, "replace")
        except LookupError:
            return self.body.decode("utf-8", "replace")


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class BoundedClient:
    """Sequential requests with global spacing, bounded reads, and no auto redirects."""
    def __init__(self, interval=5.0, max_bytes=524288, timeout=15.0,
                 opener=None, clock=time.monotonic, sleep=time.sleep):
        if interval < 5:
            raise ValueError("request interval must be at least five seconds")
        if not 1024 <= max_bytes <= 2097152:
            raise ValueError("max response bytes must be between 1024 and 2097152")
        self.interval, self.max_bytes, self.timeout = interval, max_bytes, timeout
        self.opener = opener or request.build_opener(NoRedirect())
        self.clock, self.sleep, self.last_request = clock, sleep, None
        self.requests = []

    def get(self, url):
        if self.last_request is not None:
            remaining = self.interval - (self.clock() - self.last_request)
            if remaining > 0:
                self.sleep(remaining)
        self.last_request = self.clock()
        req = request.Request(url, headers={"User-Agent": USER_AGENT,
                                           "Accept": "text/html,text/plain;q=0.9",
                                           "Accept-Encoding": "identity"})
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                body = response.read(self.max_bytes + 1)
                result = Response(url, response.status, body[:self.max_bytes],
                                  {k.casefold(): v for k, v in response.headers.items()},
                                  oversized=len(body) > self.max_bytes)
        except error.HTTPError as exc:
            # Error pages are neither parsed nor retained. Never retry 403/429.
            result = Response(url, exc.code, headers={k.casefold(): v for k, v in exc.headers.items()})
            exc.close()
        except (error.URLError, TimeoutError, OSError):
            result = Response(url, failure="network_error")
        self.requests.append({"url": url, "status": result.status,
                              "failure": result.failure, "oversized": result.oversized,
                              "response_sha256": sha256(result.body) if result.body else None})
        return result


def response_block_reason(response):
    if response.failure:
        return response.failure
    if response.status != 200:
        return "http_" + str(response.status)
    if response.oversized:
        return "response_size_limit"
    text = response.text()
    if re.search(r"just a moment|cf-chl-|verify (?:you are|you're) human|"
                 r"blocked by network security|whoa there[,! ]|access denied|"
                 r"you(?:'ve| have) been blocked", text, re.I):
        return "challenge_or_access_block"
    if re.search(r"<input\b[^>]*\btype\s*=\s*['\"]?password", text, re.I):
        return "login_required"
    return None


class Page(HTMLParser):
    """Transient HTML parser. Only numerical features and canonical URLs escape."""
    SKIP = frozenset(("script", "style", "nav", "footer", "aside", "form", "textarea", "button"))

    def __init__(self, source_id):
        super().__init__(convert_charrefs=True)
        self.source_id = source_id
        self.links, self.stack, self.captures = [], [], []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
        classes = set(values.get("class", "").split())
        role = None
        if tag == "h1" or "title_subject" in classes:
            role = "title"
        if (values.get("itemprop") == "articleBody" or
                classes.intersection(("write_div", "content-text", "post-content", "article-content", "content-body"))):
            role = "body"
        elif tag == "article":
            role = "article_fallback"
        if classes.intersection(("usertxt", "comment-content", "comment-body", "comment-text")):
            role = "comment"
        capture = {"role": role, "parts": []} if role else None
        if capture:
            self.captures.append(capture)
        # Void elements must not corrupt the capture stack.
        if tag not in ("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"):
            self.stack.append((tag, capture))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if any(tag in self.SKIP for tag, _ in self.stack):
            return
        for _, capture in self.stack:
            if capture:
                capture["parts"].append(data)

    def texts(self, role):
        values = []
        for capture in self.captures:
            if capture["role"] == role:
                text = re.sub(r"\s+", " ", " ".join(capture["parts"])).strip()
                if text and text not in values:
                    values.append(text)
        return values


def abstract_features(text):
    # Identifiers influence neither stored features nor content fingerprints.
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"https?://\S+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|"
                  r"\b(?:\d{1,3}\.){3}\d{1,3}\b|\b01[016789][ -]?\d{3,4}[ -]?\d{4}\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    sentences = [part.strip() for part in re.split(r"[.!?。！？]+|\n+", text) if part.strip()]
    lengths = [len(part) for part in sentences]
    features = {}
    for label, regex in (("polite_ending", r"(?:요|니다)[.!?…\s]*$"),
                         ("casual_im_ham", r"(?:임|함)[.!?…\s]*$"),
                         ("casual_directive", r"(?:하셈|해봐|해 봐)[.!?…\s]*$"),
                         ("laughter", r"ㅋ{2,}|ㅎ{2,}|\blol\b"),
                         ("question_mark", r"[?？]")):
        features[label] = len(re.findall(regex, text, re.I))
    questions = []
    for label, regex in (("explanation", r"왜|이유|원리|설명|\bwhy\b|\bexplain\b"),
                         ("solution_request", r"풀[어이]|풀이|구하|계산|\bsolve\b|\bcalculate\b"),
                         ("verification", r"맞[나아는을]|틀[리린렸]|확인|\bcorrect\b|\bcheck\b"),
                         ("resource_recommendation", r"추천|교재|인강|\brecommend|\btextbook"),
                         ("comparison", r"차이|비교|\bversus\b|\bcompare\b|\bvs\.?\b")):
        if re.search(regex, text, re.I):
            questions.append(label)
    return {"content_sha256": sha256(text), "character_count": len(text),
            "sentence_count": len(lengths),
            "sentence_length": {"mean": round(sum(lengths) / len(lengths), 2) if lengths else 0,
                                "max": max(lengths, default=0)},
            "fixed_style_features": features, "question_types": questions or ["other"],
            "has_math": bool(re.search(r"\$|\\(?:frac|sqrt|begin|\(|\[)|[∫∑√]|"
                                       r"\b\d+\s*[=+*/^]|\b[A-Za-z]\s*[=^]", text))}


def extract_pattern(source_id, url, html, metadata):
    page = Page(source_id)
    page.feed(html)
    bodies = page.texts("body")
    extraction = "body_selector"
    if not bodies:
        bodies, extraction = page.texts("article_fallback"), "article_fallback_unverified"
    if not bodies:
        return None
    comments = page.texts("comment")
    body = "\n".join(bodies)
    # Comments remain comments; neither usernames nor guessed assistant roles are emitted.
    return {"kind": "abstract_pattern", "source_id": source_id, "source_url": url,
            "metadata": dict(metadata), "extraction": extraction,
            "structure": {"body_blocks": len(bodies), "visible_comment_blocks": len(comments),
                          "comment_roles": "unassigned", "comments_are_answers": False},
            "body": abstract_features(body),
            "comment_features": [abstract_features(value) for value in comments[:100]],
            "training_eligible": False, "export_exclusion": "pattern_only_no_training_text"}


def fetch_public(client, url, source, robots_text):
    for _ in range(4):
        if not same_origin_url(url, source):
            return None, "redirect_outside_public_source"
        decision = robots_decision(robots_text, url)
        if not decision["allowed"]:
            return None, decision["reason"]
        response = client.get(url)
        if response.status in (301, 302, 303, 307, 308):
            location = response.headers.get("location")
            if not location:
                return response, "redirect_without_location"
            url = parse.urljoin(url, location)
            continue
        return response, response_block_reason(response)
    return None, "redirect_limit"


def collect(sources, max_posts=10, metadata=None, client=None):
    if not 1 <= max_posts <= 10:
        raise ValueError("max-posts must be between one and ten")
    if not sources or any(source not in DEFAULT_SOURCES for source in sources):
        raise ValueError("sources must contain dcinside, orbi, or reddit")
    client, metadata = client or BoundedClient(), metadata or {}
    # Invalid metadata is rejected before any site is contacted.
    rights_by_source = {source_id: source_metadata(source_id, metadata.get(source_id))
                        for source_id in dict.fromkeys(sources)}
    reports, patterns, attempted, seen = [], [], 0, set()
    for source_id in dict.fromkeys(sources):
        source = DEFAULT_SOURCES[source_id]
        rights = rights_by_source[source_id]
        report = {"source_id": source_id, "seed_url": source["seed"], "permission": rights,
                  "patterns": 0, "thread_requests": 0, "status": "not_started"}
        reports.append(report)
        robots = client.get(source["origin"] + "/robots.txt")
        reason = response_block_reason(robots)
        report["robots"] = {"url": robots.url, "http_status": robots.status,
                            "sha256": sha256(robots.body) if robots.body else None}
        robots_text = robots.text()
        valid_robots = bool(re.search(r"(?im)^\s*user-agent\s*:", robots_text)) and not re.search(r"<html\b", robots_text, re.I)
        if reason or not valid_robots:
            report["status"] = "robots_unavailable"
            report["reason"] = reason or "unrecognized_robots_response"
            continue
        decision = robots_decision(robots_text, source["seed"])
        report["robots"].update(decision)
        if not decision["allowed"]:
            report["status"], report["reason"] = "blocked_robots", decision["reason"]
            report["listing_http_status"] = None
            continue
        listing, reason = fetch_public(client, source["seed"], source, robots_text)
        report["listing_http_status"] = listing.status if listing else None
        if reason:
            report["status"], report["reason"] = "listing_blocked", reason
            continue
        page = Page(source_id)
        page.feed(listing.text())
        links = list(dict.fromkeys(url for href in page.links
                                  if (url := canonical_thread(source_id, href, listing.url))))
        report["discovered_thread_urls"] = links[:max_posts]
        report["discovered_thread_count"] = len(links)
        report["thread_results"] = []
        for url in links:
            if attempted >= max_posts:
                break
            if url in seen:
                continue
            seen.add(url)
            decision = robots_decision(robots_text, url)
            if not decision["allowed"]:
                report["thread_results"].append({"url": url, "status": decision["reason"]})
                continue
            attempted += 1
            report["thread_requests"] += 1
            response, reason = fetch_public(client, url, source, robots_text)
            if reason:
                report["thread_results"].append({"url": url, "status": reason})
                report["reason"] = reason
                # Stop the source on any failed/access-controlled thread, without retries.
                break
            record = extract_pattern(source_id, url, response.text(), rights)
            if record:
                patterns.append(record)
                report["patterns"] += 1
            report["thread_results"].append({"url": url, "status": "pattern_extracted" if record else "no_body_selector"})
        report["status"] = ("partial_patterns_source_stopped" if report["patterns"] and report.get("reason") else
                            "patterns_collected" if report["patterns"] else
                            "source_stopped" if report.get("reason") else
                            "empty_listing" if not links else
                            "post_budget_exhausted" if attempted >= max_posts else "no_usable_patterns")
    return {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
            "purpose": "abstract_pattern_extraction_for_ai_development",
            "collection_status": "patterns_collected" if patterns else "no_records",
            "raw_content_saved": False, "training_performed": False,
            "training_status": "not_started", "train_export_records": 0,
            "pattern_records": len(patterns), "max_posts": max_posts,
            "thread_requests": attempted, "sources": reports,
            "requests": client.requests, "patterns": patterns}


def write_results(result, output_dir):
    output = private_output_path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    patterns = result["patterns"]
    payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in patterns)
    (output / "patterns.jsonl").write_text(payload, encoding="utf-8")
    report = {key: value for key, value in result.items() if key != "patterns"}
    report["files"] = {"patterns.jsonl": {"records": len(patterns), "sha256": sha256(payload)}}
    (output / "collection-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", default="dcinside,orbi,reddit", help="comma-separated source IDs")
    parser.add_argument("--output-dir", required=True, help="new private directory outside every Git checkout")
    parser.add_argument("--max-posts", type=int, default=10, help="global thread request cap, 1..10")
    parser.add_argument("--source-metadata", help="optional private JSON source permission metadata; unknown by default")
    parser.add_argument("--max-response-bytes", type=int, default=524288)
    args = parser.parse_args(argv)
    try:
        output = private_output_path(args.output_dir)
        metadata = json.loads(Path(args.source_metadata).read_text(encoding="utf-8-sig")) if args.source_metadata else {}
        if not isinstance(metadata, dict):
            raise ValueError("source metadata must be an object keyed by source ID")
        source_ids = [source.strip() for source in args.sources.split(",") if source.strip()]
        result = collect(source_ids, args.max_posts, metadata, BoundedClient(max_bytes=args.max_response_bytes))
        report = write_results(result, output)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({"output_dir": str(output), "pattern_records": report["pattern_records"],
                      "collection_status": report["collection_status"], "training_performed": False,
                      "sources": {row["source_id"]: row["status"] for row in report["sources"]}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
