"""Collect bounded, abstract community patterns; never save posts or train a model.

Example (output must be a new private directory outside every Git checkout):
  python tools/ai/community_collect.py --sources dcinside,orbi,reddit \
    --output-dir D:/haslalab-private-problem-bank/hasla-ai/community-probe-v1 \
    --max-posts 10

The default purpose is pattern extraction for later AI development. Robots rules
are matched against this client's truthful, consistent User-Agent. Exclusions for
other named bots are observations, not rules automatically applied to this agent.
A blocked source still produces a truthful status report. No login,
challenge solving, API guessing, proxy rotation, raw corpus, or training occurs.
"""

import argparse
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from http.client import HTTPException, IncompleteRead
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import ssl
import time
import unicodedata
from urllib import error, parse, request, robotparser


REPO_ROOT = Path(__file__).resolve().parents[2]
USER_AGENT = "HaslaPatternResearch/0.1 (purpose=abstract-pattern-extraction-for-AI-development)"
AUTHOR_FILTER_POLICY = "exclude-bugiu-v1"
# User-provided exclusion policy, not a nickname discovered from a source.
EXCLUDED_AUTHORS = frozenset(("부기우",))
AI_AGENTS = ("GPTBot", "ClaudeBot", "anthropic-ai", "Claude-Web", "Google-Extended",
             "Applebot-Extended", "CCBot", "Bytespider", "Amazonbot",
             "Meta-ExternalAgent", "cohere-ai", "PerplexityBot")
SKIPPABLE_THREAD_FAILURES = frozenset(("http_404", "http_410", "redirect_outside_public_source"))
TRANSPORT_THREAD_FAILURES = frozenset(("network_incomplete_response", "network_timeout", "network_error", "network_protocol_error"))
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
            "site_terms_permission_status": str(supplied.get("site_terms_permission_status", "unknown")),
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


def observed_listing_link(source_id, href, base):
    """Validate an actual page link; never manufacture pagination/API URLs."""
    source = DEFAULT_SOURCES[source_id]
    url = parse.urljoin(base, href)
    if source_id == "reddit" or not same_origin_url(url, source):
        return None
    parts, seed = parse.urlsplit(url), parse.urlsplit(source["seed"])
    if parts.path != seed.path:
        return None
    query = parse.parse_qs(parts.query)
    if any(len(values) != 1 for values in query.values()):
        return None
    page = query.get("page", [""])[0]
    if not re.fullmatch(r"[0-9]+", page) or int(page) < 2:
        return None
    allowed = {"page"}
    if source_id == "dcinside":
        allowed.add("id")
        if query.get("id") != parse.parse_qs(seed.query).get("id"):
            return None
    if set(query) - allowed:
        return None
    return parse.urlunsplit(parts._replace(fragment=""))


def load_excluded_urls(paths):
    """Read prior reports/pattern JSONL or explicit URL lists without raw output."""
    candidates = []
    def visit(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ("source_url", "url") and isinstance(item, str):
                    candidates.append(item)
                elif isinstance(item, (dict, list)):
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, (dict, list)):
                    visit(item)
    for filename in paths or []:
        raw = Path(filename).read_text(encoding="utf-8-sig")
        if len(raw) > 16777216:
            raise ValueError("exclusion file is too large")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            for line in raw.splitlines():
                if not line.strip():
                    continue
                if line.strip().startswith("https://"):
                    candidates.append(line.strip())
                else:
                    visit(json.loads(line))
        else:
            if isinstance(value, list) and all(isinstance(item, str) for item in value):
                candidates.extend(value)
            else:
                visit(value)
    result = set()
    for url in candidates:
        for source_id, source in DEFAULT_SOURCES.items():
            canonical = canonical_thread(source_id, url, source["seed"])
            if canonical:
                result.add(canonical)
                break
    return result


def observed_cursors(paths):
    """Recover only pagination URLs recorded as observed in earlier reports."""
    found = {source_id: set() for source_id in DEFAULT_SOURCES}
    for filename in paths or []:
        try:
            value = json.loads(Path(filename).read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict):
            continue
        for source in value.get("sources", []):
            source_id = source.get("source_id")
            if source_id not in found:
                continue
            for listing in source.get("listing_results", []):
                for url in listing.get("observed_pagination_urls", []):
                    valid = observed_listing_link(source_id, url, DEFAULT_SOURCES[source_id]["seed"])
                    if valid:
                        found[source_id].add(valid)
    return found


def robots_decision(text, url):
    parser = robotparser.RobotFileParser()
    parser.parse(text.splitlines())
    explicit = {match[1].strip().casefold()
                for match in re.finditer(r"(?im)^\s*user-agent\s*:\s*([^#\r\n]+)", text)}
    observations = [agent for agent in AI_AGENTS
                    if agent.casefold() in explicit and not parser.can_fetch(agent, url)]
    allowed = parser.can_fetch(USER_AGENT, url)
    return {"allowed": allowed, "reason": "robots_allowed" if allowed else "robots_denied",
            "matched_user_agent": "HaslaPatternResearch",
            "denied_agents": [] if allowed else ["HaslaPatternResearch"],
            "observed_exclusions": observations,
            "robots_is_site_permission": False}


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
        except IncompleteRead:
            # A partial chunked response is not a complete page and is discarded.
            result = Response(url, failure="network_incomplete_response")
        except HTTPException:
            result = Response(url, failure="network_protocol_error")
        except (error.URLError, TimeoutError, OSError) as exc:
            cause = exc.reason if isinstance(exc, error.URLError) else exc
            if isinstance(cause, ssl.SSLCertVerificationError):
                failure = "network_certificate_error"
            elif isinstance(cause, ssl.SSLError):
                failure = "network_tls_error"
            elif isinstance(cause, TimeoutError):
                failure = "network_timeout"
            else:
                failure = "network_error"
            result = Response(url, failure=failure)
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
        # Public DC posts contain password fields for nonmember comment deletion.
        # Such a field alone is not evidence of a login wall.
        public_body = re.search(r'class\s*=\s*[\'"][^\'"]*\bwrite_div\b', text, re.I)
        public_body = public_body or ("layout-board-read" in text and
                                     re.search(r'class\s*=\s*[\'"][^\'"]*\bcontent-wrap\b', text, re.I))
        if not public_body or re.search(r"/(?:login|signin)(?:/|$)", parse.urlsplit(response.url).path, re.I):
            return "login_required"
    return None


def normalized_author(value):
    """Compare in memory only; IP display suffixes are never persisted."""
    value = unicodedata.normalize("NFKC", value or "").strip()
    value = re.sub(r"\s*[([]\s*(?:\d{1,3}\.){1,3}(?:\d{1,3}|\*+)\s*[)\]]\s*$", "", value)
    return re.sub(r"\s+", "", value)


class Page(HTMLParser):
    """Transient HTML parser. Only numerical features and canonical URLs escape."""
    SKIP = frozenset(("script", "style", "nav", "footer", "aside", "form", "textarea", "button"))

    def __init__(self, source_id):
        super().__init__(convert_charrefs=True)
        self.source_id = source_id
        self.links, self.stack, self.captures = [], [], []
        self.anchors, self.active_anchors = [], []
        self._post_author_states, self._comment_nodes, self._comment_contexts = [], [], []

    def _author(self, value, target):
        name = normalized_author(value)
        state = {"checked": bool(name), "excluded": bool(name) and name in EXCLUDED_AUTHORS}
        if target == "post":
            self._post_author_states.append(state)
        elif isinstance(target, dict):
            target["author_states"].append(state)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
            anchor = {"href": values["href"], "parts": [], "title": values.get("title", "")}
            self.anchors.append(anchor)
            self.active_anchors.append(anchor)
        classes = set(values.get("class", "").split())
        ancestors = set().union(*(entry[2] for entry in self.stack)) if self.stack else set()
        if tag == "li" and ((self.source_id == "orbi" and "comment" in classes and "comment-wrap" in ancestors)
                            or (self.source_id == "dcinside" and "ub-content" in classes and
                                ancestors.intersection(("comment_wrap", "comment_box", "cmt_list")))):
            depth = next((int(match[1]) for value in classes
                          if (match := re.fullmatch(r"comment-rank-(\d+)", value))), None)
            node = {"author_states": [], "depth": depth,
                    "dom_parent": self._comment_contexts[-1][1] if self._comment_contexts else None}
            self._comment_nodes.append(node)
            self._comment_contexts.append((len(self.stack), node))
        node = self._comment_contexts[-1][1] if self._comment_contexts else None
        role = None
        if tag == "h1" or "title_subject" in classes:
            role = "title"
        if self.source_id == "dcinside" and "write_div" in classes:
            role = "body"
        elif self.source_id == "orbi" and "content-wrap" in classes and "layout-board-read" in ancestors:
            role = "body"
        if ((self.source_id == "dcinside" and "usertxt" in classes and
             ancestors.intersection(("comment_wrap", "comment_box", "cmt_list"))) or
            (self.source_id == "orbi" and classes.intersection(("comment-content", "comment-text")) and
             "comment-wrap" in ancestors)):
            role = "comment"
        if role == "comment" and any(active and active["role"] == "comment" for _, active, _ in self.stack):
            # Orbi nests .comment-text within .comment-content. Capture that
            # displayed comment once, while retaining identical separate replies.
            role = None
        rank = next((int(match[1]) for group in [classes] + [entry[2] for entry in reversed(self.stack)]
                     for value in group if (match := re.fullmatch(r"comment-rank-(\d+)", value))), None)
        capture = {"role": role, "parts": [], "depth": rank} if role else None
        if capture:
            if role == "comment":
                capture["author_node"] = node
            self.captures.append(capture)
        # Identity text has a private capture on the stack only. It is reduced
        # to booleans when its tag closes, never added to captures/feature rows.
        identity_target = None
        if self.source_id == "orbi" and tag == "a" and "nickname" in classes:
            if node is not None and "meta-wrap" in ancestors:
                identity_target = node
            elif "author-wrap" in ancestors and "layout-board-read" in ancestors:
                identity_target = "post"
        elif self.source_id == "dcinside" and classes.intersection(("gall_writer", "ub-writer")):
            if node is not None:
                identity_target = node
            elif "gallview_head" in ancestors:
                identity_target = "post"
        if identity_target is not None:
            if self.source_id == "dcinside" and values.get("data-nick"):
                self._author(values["data-nick"], identity_target)
            elif capture is None:
                capture = {"role": "author_private", "parts": [], "target": identity_target}
        # Void elements must not corrupt the capture stack.
        if tag not in ("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"):
            self.stack.append((tag, capture, classes))
        if tag == "br":
            for _, active, _ in self.stack:
                if active:
                    active["parts"].append("\n")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "a" and self.active_anchors:
            self.active_anchors.pop()
        if tag in ("p", "div", "li"):
            for _, capture, _ in self.stack:
                if capture:
                    capture["parts"].append("\n")
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for _, active, _ in self.stack[i:]:
                    if active and active["role"] == "author_private":
                        self._author("".join(active["parts"]), active["target"])
                        active["parts"].clear()
                del self.stack[i:]
                self._comment_contexts = [(position, node) for position, node in self._comment_contexts
                                          if position < len(self.stack)]
                break

    def handle_data(self, data):
        if any(tag in self.SKIP for tag, _, _ in self.stack):
            return
        for anchor in self.active_anchors:
            anchor["parts"].append(data)
        for _, capture, _ in self.stack:
            if capture:
                capture["parts"].append(data)

    def texts(self, role):
        values = []
        blocked, _ = self._excluded_comment_nodes()
        for capture in self.captures:
            if capture["role"] == role:
                if role == "comment" and id(capture.get("author_node")) in blocked:
                    continue
                text = re.sub(r"[^\S\n]+", " ", " ".join(capture["parts"])).strip()
                text = re.sub(r"\n\s*\n+", "\n", text)
                if text and (role == "comment" or text not in values):
                    values.append(text)
        return values

    def _excluded_comment_nodes(self):
        excluded = {id(node) for node in self._comment_nodes
                    if any(state["excluded"] for state in node["author_states"])}
        if not excluded:
            # If all authors are checked and none match, even a flattened
            # comment hierarchy cannot contain an excluded-author ancestor.
            return set(), True
        if not any(node["dom_parent"] is not None for node in self._comment_nodes):
            # A CSS rank alone is not verified parentage. On a flattened list,
            # discard all comments if any excluded author could be their context.
            return {id(node) for node in self._comment_nodes}, False
        blocked = set()
        for node in self._comment_nodes:
            ancestor = node
            while ancestor is not None:
                if id(ancestor) in excluded:
                    blocked.add(id(node))
                    break
                ancestor = ancestor["dom_parent"]
        return blocked, True

    def author_filter(self, selected_comment_indices=None):
        """Metadata for actual observed authors, with no names/IDs/IPs/hashes."""
        captures = [capture for capture in self.captures if capture["role"] == "comment"]
        selected = captures if selected_comment_indices is None else [captures[index] for index in selected_comment_indices
                                                                     if type(index) is int and 0 <= index < len(captures)]
        post_checked = bool(self._post_author_states) and all(state["checked"] for state in self._post_author_states)
        post_excluded = any(state["excluded"] for state in self._post_author_states)
        all_checked = bool(self._comment_nodes) and all(node["author_states"] and
                      all(state["checked"] for state in node["author_states"]) for node in self._comment_nodes)
        selected_checked = bool(selected) and all(capture.get("author_node") is not None and
                           capture["author_node"]["author_states"] and
                           all(state["checked"] for state in capture["author_node"]["author_states"])
                           for capture in selected)
        blocked, hierarchy_checked = self._excluded_comment_nodes()
        present = post_excluded or any(id(capture.get("author_node")) in blocked for capture in selected)
        return {"policy_version": AUTHOR_FILTER_POLICY, "post_author_checked": post_checked,
                "selected_reply_authors_checked": bool(selected_checked),
                "reply_branch_checked": bool(all_checked and hierarchy_checked),
                "excluded_author_present": present}


def prioritized_threads(page, source_id, base):
    """Transient title cues prioritize questions; titles are never saved/logged."""
    links = list(dict.fromkeys(url for href in page.links
                              if (url := canonical_thread(source_id, href, base))))
    scores, promotional, outside_board = {}, set(), set()
    if source_id == "dcinside":
        wanted = parse.parse_qs(parse.urlsplit(DEFAULT_SOURCES[source_id]["seed"]).query).get("id")
        outside_board = {url for url in links if parse.parse_qs(parse.urlsplit(url).query).get("id") != wanted}
    for anchor in page.anchors:
        url = canonical_thread(source_id, anchor["href"], base)
        if not url:
            continue
        title = anchor["title"] or " ".join(anchor["parts"])
        if re.search(r"공지|이용\s*약관|프리패스|할인|이벤트|운세|광고|강사\s*모집|교재\s*판매", title):
            promotional.add(url)
        score = len(re.findall(r"질문|왜|어떻게|추천|공부|[?？]|\bvs\b|\bhow\b|\bwhy\b", title, re.I))
        scores[url] = max(scores.get(url, 0), score)
    eligible = [url for url in links if url not in promotional and url not in outside_board]
    eligible.sort(key=lambda url: -scores.get(url, 0))
    return eligible, len(set(links) & promotional), len(outside_board)


def abstract_features(text):
    # Identifiers influence neither stored features nor content fingerprints.
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"https?://\S+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|"
                  r"\b(?:\d{1,3}\.){3}\d{1,3}\b|\b01[016789][ -]?\d{3,4}[ -]?\d{4}\b", " ", text)
    text = re.sub(r"[^\S\n]+", " ", text).strip()
    sentences = [part.strip() for part in re.split(r"[.!?。！？]+|\n+", text) if part.strip()]
    lengths = [len(part) for part in sentences]
    features = {}
    for label, regex in (("polite_ending", r"(?:요|니다)[.!?…\s]*$"),
                         ("casual_im_ham", r"(?:임|함)[.!?…\s]*$"),
                         ("casual_directive", r"(?:하셈|해봐|해 봐)[.!?…\s]*$"),
                         ("laughter", r"ㅋ{2,}|ㅎ{2,}|\blol\b"),
                         ("question_mark", r"[?？]")):
        features[label] = len(re.findall(regex, text, re.I))
    endings = Counter()
    # A fixed allowlist of short grammar markers, never learned phrases/snippets.
    for sentence in sentences:
        sentence = sentence.rstrip(' \t\r\n"\'”’)]}')
        for marker in ("하셈", "니다", "임", "함", "요", "죠", "까", "다", "해", "어", "야"):
            if sentence.endswith(marker):
                endings[marker] += 1
                break
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
            "fixed_style_features": features, "ending_markers": dict(endings.most_common()),
            "question_types": questions or ["other"],
            "has_math": bool(re.search(r"\$|\\(?:frac|sqrt|begin|\(|\[)|[∫∑√]|"
                                       r"\b\d+\s*[=+*/^]|\b[A-Za-z]\s*[=^]", text))}


def extract_pattern(source_id, url, html, metadata, diagnostics=None):
    page = Page(source_id)
    page.feed(html)
    author_filter = page.author_filter()
    if any(state["excluded"] for state in page._post_author_states):
        if diagnostics is not None:
            diagnostics["reason"] = "excluded_post_author"
        return None
    bodies = page.texts("body")
    extraction = "dcinside.write_div" if source_id == "dcinside" else "orbi.layout-board-read.content-wrap"
    if not bodies:
        return None
    comments = page.texts("comment")
    body = "\n".join(bodies)
    # Comments remain comments; neither usernames nor guessed assistant roles are emitted.
    return {"kind": "abstract_pattern", "source_id": source_id, "source_url": url,
            "metadata": {**metadata, "author_filter": author_filter}, "extraction": extraction,
            "structure": {"body_blocks": len(bodies), "visible_comment_blocks": len(comments),
                          "observed_comment_depths": dict(Counter(str(capture["depth"]) if capture["depth"] is not None else "unknown"
                                                                  for capture in page.captures if capture["role"] == "comment"
                                                                  and id(capture.get("author_node")) not in page._excluded_comment_nodes()[0])),
                          "comment_roles": "unassigned", "comments_are_answers": False,
                          "parent_relationships": "not_verified_from_html",
                          "depth_basis": "explicit_comment_rank_class_when_present"},
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


def collect(sources, max_posts=10, metadata=None, client=None, max_pages=1, exclude_urls=None, progress=None, listing_cursors=None):
    if not 1 <= max_posts <= 50:
        raise ValueError("max-posts must be between one and fifty")
    if not 1 <= max_pages <= 3:
        raise ValueError("max-pages must be between one and three")
    if not sources or any(source not in DEFAULT_SOURCES for source in sources):
        raise ValueError("sources must contain dcinside, orbi, or reddit")
    client, metadata = client or BoundedClient(), metadata or {}
    listing_cursors = listing_cursors or {}
    for source_id, cursor in listing_cursors.items():
        if source_id not in sources or not observed_listing_link(source_id, cursor, DEFAULT_SOURCES[source_id]["seed"]):
            raise ValueError("listing cursor must be a valid observed pagination URL for a selected source")
    # Invalid metadata is rejected before any site is contacted.
    rights_by_source = {source_id: source_metadata(source_id, metadata.get(source_id))
                        for source_id in dict.fromkeys(sources)}
    excluded = set(exclude_urls or [])
    reports, patterns, attempted, seen = [], [], 0, set(excluded)
    def emit(report, candidate=None):
        if progress:
            summary = {"source_id": report["source_id"], "patterns": report["patterns"],
                       "thread_requests": report["thread_requests"], "listing_pages": len(report.get("listing_results", [])),
                       "status": report["status"], "total_patterns": len(patterns),
                       "qa_candidate_count": len(report.get("qa_candidates", [])),
                       "transport_failure_count": sum(report.get("transport_failures", {}).values()),
                       "consecutive_transport_failures": report.get("consecutive_transport_failures", 0)}
            if report.get("reason"):
                summary["reason"] = report["reason"]
            summary["checkpoint"] = {"created_at": datetime.now(timezone.utc).isoformat(),
                                     "checkpoint_contains_full_abstract_patterns": True,
                                     "training_performed": False, "raw_content_saved": False,
                                     "pattern_records": len(patterns), "sources": reports,
                                     "patterns": list(patterns),
                                     "source_hashes": [{"source_id": record["source_id"], "url": record["source_url"],
                                                        "content_sha256": record["body"]["content_sha256"]}
                                                       for record in patterns]}
            if candidate:
                summary["new_qa_candidate"] = candidate
            progress(summary)
    for source_id in dict.fromkeys(sources):
        source = DEFAULT_SOURCES[source_id]
        initial_listing = listing_cursors.get(source_id, source["seed"])
        rights = rights_by_source[source_id]
        report = {"source_id": source_id, "seed_url": source["seed"], "permission": rights,
                  "initial_listing_url": initial_listing,
                  "patterns": 0, "thread_requests": 0, "status": "not_started",
                  "listing_results": [], "thread_results": [], "discovered_thread_urls": [],
                  "excluded_or_duplicate_links": 0, "qa_candidates": []}
        report["skipped_thread_failures"] = {}
        report["transport_failures"] = {}
        report["consecutive_transport_failures"] = 0
        report["skipped_listing_promotions"] = 0
        report["skipped_other_board_links"] = 0
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
            emit(report)
            continue
        decision = robots_decision(robots_text, initial_listing)
        report["robots"].update(decision)
        if not decision["allowed"]:
            report["status"], report["reason"] = "blocked_robots", decision["reason"]
            report["listing_http_status"] = None
            emit(report)
            continue
        queue, visited, discovered = [initial_listing], set(), set()
        while queue and len(visited) < max_pages and report["thread_requests"] < max_posts and not report.get("reason"):
            listing_url = queue.pop(0)
            if listing_url in visited:
                continue
            visited.add(listing_url)
            listing, reason = fetch_public(client, listing_url, source, robots_text)
            report["listing_http_status"] = listing.status if listing else None
            listing_result = {"url": listing_url, "http_status": report["listing_http_status"]}
            report["listing_results"].append(listing_result)
            if reason:
                report["reason"] = reason
                listing_result["status"] = reason
                break
            page = Page(source_id)
            page.feed(listing.text())
            links, skipped, outside_board = prioritized_threads(page, source_id, listing.url)
            report["skipped_listing_promotions"] += skipped
            report["skipped_other_board_links"] += outside_board
            pagination = list(dict.fromkeys(url for href in page.links
                                           if (url := observed_listing_link(source_id, href, listing.url))))
            pagination.sort(key=lambda url: (int(parse.parse_qs(parse.urlsplit(url).query)["page"][0]), url))
            listing_result.update({"status": "read", "discovered_thread_count": len(links),
                                   "observed_pagination_urls": pagination[:20]})
            queue.extend(url for url in pagination if url not in visited and url not in queue)
            for url in links:
                if url not in discovered:
                    report["discovered_thread_urls"].append(url)
                    discovered.add(url)
                if report["thread_requests"] >= max_posts:
                    break
                if url in seen:
                    report["excluded_or_duplicate_links"] += 1
                    continue
                seen.add(url)
                decision = robots_decision(robots_text, url)
                if not decision["allowed"]:
                    report["thread_results"].append({"url": url, "status": decision["reason"]})
                    report["reason"] = decision["reason"]
                    break
                attempted += 1
                report["thread_requests"] += 1
                response, reason = fetch_public(client, url, source, robots_text)
                if reason:
                    report["thread_results"].append({"url": url, "status": reason})
                    if reason in TRANSPORT_THREAD_FAILURES:
                        report["transport_failures"][reason] = report["transport_failures"].get(reason, 0) + 1
                        report["consecutive_transport_failures"] += 1
                        if report["consecutive_transport_failures"] >= 3:
                            report["reason"] = "transport_circuit_breaker"
                            report["last_transport_failure"] = reason
                            break
                        report["status"] = "collecting_after_discarded_transport_response"
                        emit(report)
                        continue
                    report["consecutive_transport_failures"] = 0
                    if reason in SKIPPABLE_THREAD_FAILURES:
                        report["skipped_thread_failures"][reason] = report["skipped_thread_failures"].get(reason, 0) + 1
                        report["status"] = "collecting_after_skipped_thread"
                        emit(report)
                        continue
                    report["reason"] = reason
                    break
                report["consecutive_transport_failures"] = 0
                diagnostics = {}
                record = extract_pattern(source_id, url, response.text(), rights, diagnostics)
                if record:
                    patterns.append(record)
                    report["patterns"] += 1
                candidate = None
                if (record and record["structure"]["visible_comment_blocks"] > 0 and
                        2 <= record["body"]["character_count"] <= 6000):
                    candidate = {"url": url, "body_character_count": record["body"]["character_count"],
                                 "content_sha256": record["body"]["content_sha256"],
                                 "visible_comment_blocks": record["structure"]["visible_comment_blocks"],
                                 "question_types": record["body"]["question_types"],
                                 "candidate_kind": ("discussion_with_visible_comments" if record["body"]["question_types"] == ["other"] else "question_with_visible_comments"),
                                 "reply_relevance_review_required": True, "assistant_roles_assigned": False}
                    report["qa_candidates"].append(candidate)
                report["thread_results"].append({"url": url, "status": "pattern_extracted" if record else
                                                  diagnostics.get("reason", "no_body_selector")})
                report["status"] = "collecting"
                emit(report, candidate)
        report["discovered_thread_count"] = len(discovered)
        report["resume_observed_listing_urls"] = [url for url in queue if url not in visited]
        report["status"] = ("partial_patterns_source_stopped" if report["patterns"] and report.get("reason") else
                            "patterns_collected" if report["patterns"] else
                            "source_stopped" if report.get("reason") else
                            "empty_listing" if not discovered else
                            "post_budget_exhausted" if report["thread_requests"] >= max_posts else "no_usable_patterns")
        emit(report)
    return {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
            "purpose": "abstract_pattern_extraction_for_ai_development",
            "collection_status": "patterns_collected" if patterns else "no_records",
            "raw_content_saved": False, "training_performed": False,
            "training_status": "not_started", "train_export_records": 0,
            "pattern_records": len(patterns), "max_posts_per_source": max_posts,
            "max_listing_pages_per_source": max_pages, "excluded_url_count": len(excluded),
            "thread_requests": attempted, "sources": reports,
            "requests": client.requests, "patterns": patterns}


def write_results(result, output_dir):
    output = private_output_path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    patterns = result["patterns"]
    payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in patterns)
    # Hash the exact bytes written, including on Windows (no LF->CRLF rewrite).
    (output / "patterns.jsonl").write_bytes(payload.encode("utf-8"))
    report = {key: value for key, value in result.items() if key != "patterns"}
    report["files"] = {"patterns.jsonl": {"records": len(patterns), "sha256": sha256(payload)}}
    (output / "collection-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def progress_writer(path):
    """Write safe partial status separately so final output stays overwrite-safe."""
    path = Path(path)
    if path.exists():
        raise ValueError("progress file already exists; choose a new output directory")
    path.parent.mkdir(parents=True, exist_ok=True)
    def update(status):
        summary = dict(status)
        snapshot = summary.pop("checkpoint")
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_bytes(json.dumps(snapshot, ensure_ascii=False, indent=2).encode("utf-8"))
        temporary.replace(path)
        print(json.dumps({"event": "collection_progress", **summary}, ensure_ascii=False), flush=True)
    return update


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", default="dcinside,orbi,reddit", help="comma-separated source IDs")
    parser.add_argument("--output-dir", required=True, help="new private directory outside every Git checkout")
    parser.add_argument("--max-posts", type=int, default=10, help="thread request cap PER SOURCE, 1..50; default 10")
    parser.add_argument("--max-pages", type=int, default=1, help="observed listing page cap per source, 1..3")
    parser.add_argument("--exclude-urls", action="append", default=[], help="prior report/pattern JSONL or URL list; repeatable")
    parser.add_argument("--listing-cursor", action="append", default=[], help="SOURCE=URL previously observed in an exclusion report")
    parser.add_argument("--source-metadata", help="optional private JSON source permission metadata; unknown by default")
    parser.add_argument("--max-response-bytes", type=int, default=524288)
    args = parser.parse_args(argv)
    try:
        output = private_output_path(args.output_dir)
        metadata = json.loads(Path(args.source_metadata).read_text(encoding="utf-8-sig")) if args.source_metadata else {}
        if not isinstance(metadata, dict):
            raise ValueError("source metadata must be an object keyed by source ID")
        source_ids = [source.strip() for source in args.sources.split(",") if source.strip()]
        exclusions = load_excluded_urls(args.exclude_urls)
        cursor_proof = observed_cursors(args.exclude_urls)
        cursors = {}
        for item in args.listing_cursor:
            source_id, separator, url = item.partition("=")
            if not separator or source_id not in source_ids or url not in cursor_proof.get(source_id, set()):
                raise ValueError("listing cursor lacks an observed URL in the supplied prior reports")
            cursors[source_id] = url
        checkpoint = progress_writer(output.with_name(output.name + ".progress.json"))
        result = collect(source_ids, args.max_posts, metadata, BoundedClient(max_bytes=args.max_response_bytes),
                         args.max_pages, exclusions, checkpoint, cursors)
        report = write_results(result, output)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({"output_dir": str(output), "pattern_records": report["pattern_records"],
                      "collection_status": report["collection_status"], "training_performed": False,
                      "sources": {row["source_id"]: row["status"] for row in report["sources"]}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
