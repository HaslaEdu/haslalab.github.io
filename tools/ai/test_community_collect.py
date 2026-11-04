"""Offline fixture tests; these tests must never contact community websites."""
import io
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from urllib import error

import community_collect as collector


def response(url, html, status=200, headers=None):
    return collector.Response(url, status, html.encode("utf-8"), headers or {"content-type": "text/html; charset=utf-8"})


def orbi_post(body, comments=""):
    return '<div class="layout-board-read"><div class="panel"><div class="content-wrap">' + body + '</div><div class="comment-wrap">' + comments + '</div></div></div>'


class FakeClient:
    def __init__(self, routes):
        self.routes, self.requests = routes, []

    def get(self, url):
        if url not in self.routes:
            raise AssertionError("unexpected request: " + url)
        self.requests.append({"url": url, "status": self.routes[url].status})
        return self.routes[url]


class CommunityCollectorTests(unittest.TestCase):
    def test_other_named_bot_exclusion_is_observed_without_applying_it_to_our_agent(self):
        text = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
        decision = collector.robots_decision(text, "https://orbi.kr/list")
        self.assertTrue(decision["allowed"])
        self.assertEqual(decision["reason"], "robots_allowed")
        self.assertEqual(decision["observed_exclusions"], ["GPTBot"])
        self.assertFalse(decision["robots_is_site_permission"])
        self.assertIn("purpose=", collector.USER_AGENT)

    def test_our_explicit_agent_rules_and_global_denial_are_enforced(self):
        rules = "User-agent: HaslaPatternResearch\nDisallow: /private\n\nUser-agent: *\nAllow: /\n"
        self.assertFalse(collector.robots_decision(rules, "https://orbi.kr/private")["allowed"])
        self.assertTrue(collector.robots_decision(rules, "https://orbi.kr/list")["allowed"])

    def test_reddit_global_denial_prevents_listing_request(self):
        url = "https://www.reddit.com/robots.txt"
        client = FakeClient({url: response(url, "User-agent: *\nDisallow: /\n")})
        result = collector.collect(["reddit"], client=client)
        self.assertEqual(len(client.requests), 1)
        self.assertEqual(result["sources"][0]["status"], "blocked_robots")
        self.assertEqual(result["collection_status"], "no_records")
        self.assertFalse(result["training_performed"])
        self.assertEqual(result["train_export_records"], 0)

    def test_unknown_rights_are_not_promoted_to_training_permission(self):
        metadata = collector.source_metadata("orbi", {"rights_status": "licensed", "allowed_uses": ["train"]})
        self.assertFalse(metadata["source_training_authorized"])
        self.assertEqual(collector.source_metadata("orbi")["rights_status"], "unknown")
        metadata = collector.source_metadata("orbi", {"rights_status": "licensed", "allowed_uses": ["train"],
                                                       "permission_reference": "signed-contract-42"})
        self.assertTrue(metadata["source_training_authorized"])

    def test_canonical_urls_deduplicate_without_api_or_cross_origin_links(self):
        canonical = collector.canonical_thread("dcinside", "/mgallery/board/view/?id=physics&no=398&t=cv&page=2", "https://gall.dcinside.com/")
        self.assertEqual(canonical, "https://gall.dcinside.com/mgallery/board/view/?id=physics&no=398")
        self.assertEqual(collector.canonical_thread("orbi", "/0006658324/title?x=y", "https://orbi.kr/list"), "https://orbi.kr/0006658324")
        self.assertIsNone(collector.canonical_thread("orbi", "https://evil.example/0006658324", "https://orbi.kr/list"))
        self.assertIsNone(collector.canonical_thread("orbi", "/api/0006658324", "https://orbi.kr/list"))

    def test_only_observed_same_listing_pagination_is_accepted(self):
        self.assertEqual(collector.observed_listing_link("orbi", "/list?page=2", "https://orbi.kr/list"), "https://orbi.kr/list?page=2")
        self.assertIsNone(collector.observed_listing_link("orbi", "/list?page=1", "https://orbi.kr/list"))
        self.assertIsNone(collector.observed_listing_link("orbi", "/list?page=2&tag=private", "https://orbi.kr/list"))
        self.assertIsNone(collector.observed_listing_link("dcinside", "/mgallery/board/lists/?id=other&page=2", collector.DEFAULT_SOURCES["dcinside"]["seed"]))
        self.assertIsNone(collector.observed_listing_link("orbi", "https://evil.example/list?page=2", "https://orbi.kr/list"))

    def test_exclusion_report_does_not_exclude_unfetched_discoveries(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "prior.json"
            path.write_text(json.dumps({"sources": [{"thread_results": [{"url": "https://orbi.kr/0006658324"}],
                                                    "discovered_thread_urls": ["https://orbi.kr/0006658325"]}]}), encoding="utf-8")
            self.assertEqual(collector.load_excluded_urls([path]), {"https://orbi.kr/0006658324"})

    def test_observed_cursor_resumes_without_replaying_seed_listing(self):
        with tempfile.TemporaryDirectory() as root:
            prior = Path(root) / "prior.json"
            url = "https://orbi.kr/list?page=2"
            prior.write_text(json.dumps({"sources": [{"source_id": "orbi", "listing_results": [{"observed_pagination_urls": [url]}]}]}), encoding="utf-8")
            self.assertEqual(collector.observed_cursors([prior])["orbi"], {url})
            robot = "https://orbi.kr/robots.txt"
            client = FakeClient({robot: response(robot, "User-agent: *\nAllow: /\n"), url: response(url, "<p>No posts</p>")})
            result = collector.collect(["orbi"], client=client, listing_cursors={"orbi": url})
            self.assertEqual([r["url"] for r in client.requests], [robot, url])
            self.assertEqual(result["sources"][0]["initial_listing_url"], url)

    def test_pagination_is_bounded_and_excluded_threads_are_not_requested(self):
        origin, seed = "https://orbi.kr", "https://orbi.kr/list"
        routes = {origin + "/robots.txt": response(origin + "/robots.txt", "User-agent: *\nAllow: /\n"),
                  seed: response(seed, '<a href="/0006658324">old</a><a href="/list?page=2">2</a>'),
                  seed + "?page=2": response(seed + "?page=2", '<a href="/0006658325">new</a><a href="/list?page=3">3</a>'),
                  origin + "/0006658325": response(origin + "/0006658325", orbi_post('왜 맞나요?', '<div class="comment-content">설명합니다.</div>'))}
        updates = []
        result = collector.collect(["orbi"], max_posts=50, max_pages=2, exclude_urls={origin + "/0006658324"},
                                   client=FakeClient(routes), progress=updates.append)
        self.assertEqual(result["thread_requests"], 1)
        self.assertEqual(len(result["sources"][0]["listing_results"]), 2)
        self.assertEqual(result["sources"][0]["excluded_or_duplicate_links"], 1)
        self.assertTrue(updates)
        self.assertEqual(updates[-1]["checkpoint"]["source_hashes"][0]["url"], origin + "/0006658325")
        self.assertEqual(len(updates[-1]["checkpoint"]["source_hashes"][0]["content_sha256"]), 64)
        self.assertNotIn(seed + "?page=3", [row["url"] for row in result["requests"]])

    def test_invalid_limits_fail_before_network(self):
        for kwargs in ({"max_posts": 51}, {"max_posts": 0}, {"max_pages": 4}, {"max_pages": 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                collector.collect(["orbi"], client=FakeClient({}), **kwargs)

    def test_question_titles_are_prioritized_and_promotions_are_skipped_without_copying_titles(self):
        page = collector.Page("orbi")
        page.feed('<a href="/0006658324">오늘 점심</a><a href="/0006658325">프리패스 할인 이벤트</a><a href="/0006658326">왜 이 풀이가 틀렸나요? 질문</a>')
        links, skipped, other_boards = collector.prioritized_threads(page, "orbi", "https://orbi.kr/list")
        self.assertEqual(links, ["https://orbi.kr/0006658326", "https://orbi.kr/0006658324"])
        self.assertEqual(skipped, 1)
        self.assertEqual(other_boards, 0)

    def test_dc_sidebar_links_from_other_boards_are_not_collected(self):
        page = collector.Page("dcinside")
        page.feed('<a href="/mgallery/board/view/?id=physics&no=398">질문</a><a href="/board/view/?id=dcbest&no=12345">왜 그런가요?</a>')
        links, _, outside = collector.prioritized_threads(page, "dcinside", collector.DEFAULT_SOURCES["dcinside"]["seed"])
        self.assertEqual(links, ["https://gall.dcinside.com/mgallery/board/view/?id=physics&no=398"])
        self.assertEqual(outside, 1)

    def test_features_store_no_raw_content_or_personal_identifiers(self):
        html = '<h1>PRIVATE TITLE</h1>' + orbi_post('왜 x = 2 인지 설명해주세요? secret@example.com 010-1234-5678', '<div class="comment-text">이유는 계산하면 됩니다.</div>') + '<script>SECRET SCRIPT</script>'
        pattern = collector.extract_pattern("orbi", "https://orbi.kr/0006658324", html, collector.source_metadata("orbi"))
        serialized = json.dumps(pattern, ensure_ascii=False)
        for secret in ("PRIVATE TITLE", "secret@example.com", "010-1234-5678", "설명해주세요", "SECRET SCRIPT"):
            self.assertNotIn(secret, serialized)
        self.assertIn("explanation", pattern["body"]["question_types"])
        self.assertTrue(pattern["body"]["has_math"])
        self.assertFalse(pattern["training_eligible"])
        self.assertEqual(pattern["structure"]["visible_comment_blocks"], 1)
        self.assertFalse(pattern["structure"]["comments_are_answers"])

    def test_per_source_post_budget_and_duplicate_links(self):
        origin = "https://orbi.kr"
        listing = origin + "/list"
        routes = {origin + "/robots.txt": response(origin + "/robots.txt", "User-agent: *\nAllow: /\n"),
                  listing: response(listing, ''.join('<a href="/000%d/title">post</a>' % i for i in (6658324, 6658324, 6658325, 6658326)))}
        for number in (6658324, 6658325):
            url = origin + "/000" + str(number)
            routes[url] = response(url, orbi_post('왜 맞나요? x = 2'))
        result = collector.collect(["orbi"], max_posts=2, client=FakeClient(routes))
        self.assertEqual(result["thread_requests"], 2)
        self.assertEqual(result["pattern_records"], 2)
        self.assertEqual(len(result["requests"]), 4)

    def test_two_sources_each_get_their_own_bounded_post_budget(self):
        routes = {}
        for sid in ("orbi", "dcinside"):
            source = collector.DEFAULT_SOURCES[sid]
            origin, seed = source["origin"], source["seed"]
            routes[origin + "/robots.txt"] = response(origin + "/robots.txt", "User-agent: *\nAllow: /\n")
            links = [origin + "/0006658324", origin + "/0006658325"] if sid == "orbi" else [origin + "/mgallery/board/view/?id=physics&no=398", origin + "/mgallery/board/view/?id=physics&no=399"]
            routes[seed] = response(seed, ''.join('<a href="' + url + '">post</a>' for url in links))
            for url in links:
                routes[url] = response(url, orbi_post('설명해 주세요.') if sid == "orbi" else '<div class="write_div">설명해 주세요.</div>')
        result = collector.collect(["orbi", "dcinside"], max_posts=2, client=FakeClient(routes))
        self.assertEqual(result["thread_requests"], 4)
        self.assertEqual([source["thread_requests"] for source in result["sources"]], [2, 2])
        self.assertEqual(result["pattern_records"], 4)
        self.assertEqual(result["sources"][0]["permission"]["site_terms_permission_status"], "unknown")

    def test_orbi_wrapper_and_unrelated_article_are_not_body_content(self):
        meta = collector.source_metadata("orbi")
        html = '<div class="content-body">PRIVATE AUTHOR <div class="layout-board-list">UNRELATED POSTS</div>' + orbi_post('진짜 본문입니다.') + '</div>'
        record = collector.extract_pattern("orbi", "https://orbi.kr/0006658324", html, meta)
        self.assertEqual(record["body"]["character_count"], len('진짜 본문입니다.'))
        self.assertIsNone(collector.extract_pattern("orbi", "https://orbi.kr/0006658324", '<article>UNRELATED POSTS</article>', meta))
        self.assertIsNone(collector.extract_pattern("orbi", "https://orbi.kr/0006658324", '<div class="content-wrap">OUTSIDE READ AREA</div>', meta))

    def test_public_post_delete_password_does_not_become_a_login_wall(self):
        public = response("https://gall.dcinside.com/mgallery/board/view/?id=physics&no=398", '<div class="write_div">질문입니다.</div><input type="password" name="delete_password">')
        self.assertIsNone(collector.response_block_reason(public))
        self.assertEqual(collector.response_block_reason(response("https://orbi.kr/login", '<input type="password">')), "login_required")

    def test_comment_counts_and_generic_ending_markers_do_not_copy_phrases(self):
        html = orbi_post('<p>질문이에요.</p><p>맞나요?</p>', '<li class="comment comment-rank-0"><div class="comment-content">네.</div></li><li class="comment comment-rank-1"><div class="comment-content">네.</div></li>')
        record = collector.extract_pattern("orbi", "https://orbi.kr/0006658324", html, collector.source_metadata("orbi"))
        self.assertEqual(record["structure"]["visible_comment_blocks"], 2)
        self.assertEqual(record["structure"]["observed_comment_depths"], {"0": 1, "1": 1})
        self.assertEqual(record["body"]["ending_markers"], {"요": 2})
        self.assertNotIn('질문이에요', json.dumps(record, ensure_ascii=False))

    def test_nested_comment_selectors_count_one_reply_but_identical_separate_replies_count_two(self):
        comments = ''.join('<li class="comment comment-rank-0"><div class="comment-content"><p class="comment-text">네.</p></div></li>' for _ in range(2))
        html = orbi_post('이 설명 맞나요?', comments)
        record = collector.extract_pattern("orbi", "https://orbi.kr/0006658324", html, collector.source_metadata("orbi"))
        self.assertEqual(record["structure"]["visible_comment_blocks"], 2)
        self.assertEqual(len(record["comment_features"]), 2)

    def test_403_stops_source_without_requesting_next_thread(self):
        origin = "https://orbi.kr"
        routes = {origin + "/robots.txt": response(origin + "/robots.txt", "User-agent: *\nAllow: /\n"),
                  origin + "/list": response(origin + "/list", '<a href="/0006658324">one</a><a href="/0006658325">two</a>'),
                  origin + "/0006658324": response(origin + "/0006658324", "", 403)}
        result = collector.collect(["orbi"], client=FakeClient(routes))
        self.assertEqual(result["thread_requests"], 1)
        self.assertEqual(result["sources"][0]["status"], "source_stopped")
        self.assertEqual(result["sources"][0]["reason"], "http_403")

    def test_challenge_login_and_oversized_pages_are_never_parsed(self):
        for html, expected in (("<title>Just a moment...</title>", "challenge_or_access_block"),
                               ('<form><input type="password"></form>', "login_required")):
            self.assertEqual(collector.response_block_reason(response("https://orbi.kr/list", html)), expected)
        oversized = response("https://orbi.kr/list", "safe")
        oversized.oversized = True
        self.assertEqual(collector.response_block_reason(oversized), "response_size_limit")

    def test_unavailable_or_html_robots_fail_closed_without_listing(self):
        url = "https://orbi.kr/robots.txt"
        for html, status in (("", 404), ("", 429), ("<html>home page</html>", 200)):
            client = FakeClient({url: response(url, html, status)})
            result = collector.collect(["orbi"], client=client)
            self.assertEqual(result["sources"][0]["status"], "robots_unavailable")
            self.assertEqual(len(client.requests), 1)

    def test_redirect_rechecks_robots_and_does_not_follow_disallowed_path(self):
        url = "https://orbi.kr/list"
        client = FakeClient({url: response(url, "", 302, {"location": "/private"})})
        _, reason = collector.fetch_public(client, url, collector.DEFAULT_SOURCES["orbi"],
                                           "User-agent: *\nDisallow: /private\nAllow: /\n")
        self.assertEqual(reason, "robots_denied")
        self.assertEqual(len(client.requests), 1)

    def test_redirect_to_login_or_other_origin_is_not_followed(self):
        for location in ("/login", "https://other.example/page"):
            url = "https://orbi.kr/list"
            client = FakeClient({url: response(url, "", 302, {"location": location})})
            _, reason = collector.fetch_public(client, url, collector.DEFAULT_SOURCES["orbi"], "User-agent: *\nAllow: /\n")
            self.assertEqual(reason, "redirect_outside_public_source")
            self.assertEqual(len(client.requests), 1)

    def test_spacing_and_byte_limit_in_transport(self):
        class HTTPResponse(io.BytesIO):
            status, headers = 200, {"Content-Type": "text/plain"}
        class Opener:
            def open(self, req, timeout):
                return HTTPResponse(b"x" * 1026)
        current, sleeps = [0.0], []
        def sleep(seconds):
            sleeps.append(seconds)
            current[0] += seconds
        client = collector.BoundedClient(max_bytes=1024, opener=Opener(), clock=lambda: current[0], sleep=sleep)
        first = client.get("https://orbi.kr/robots.txt")
        client.get("https://orbi.kr/list")
        self.assertEqual(sleeps, [5.0])
        self.assertTrue(first.oversized)
        self.assertEqual(len(first.body), 1024)

    def test_output_validation_and_zero_record_report(self):
        with self.assertRaises(ValueError):
            collector.private_output_path(collector.REPO_ROOT / "tmp" / "community-output")
        with tempfile.TemporaryDirectory() as root:
            checkout = Path(root) / "checkout"
            checkout.mkdir()
            (checkout / ".git").write_text("gitdir: elsewhere")
            with self.assertRaises(ValueError):
                collector.private_output_path(checkout / "private")
            out = Path(root) / "private"
            url = "https://www.reddit.com/robots.txt"
            result = collector.collect(["reddit"], client=FakeClient({url: response(url, "User-agent: *\nDisallow: /\n")}))
            report = collector.write_results(result, out)
            self.assertEqual((out / "patterns.jsonl").read_text(), "")
            self.assertEqual(hashlib.sha256((out / "patterns.jsonl").read_bytes()).hexdigest(), report["files"]["patterns.jsonl"]["sha256"])
            self.assertFalse(report["training_performed"])
            self.assertEqual(report["pattern_records"], 0)
            with self.assertRaises(ValueError):
                collector.write_results(result, out)

    def test_nonempty_file_checksum_matches_physical_bytes_on_windows(self):
        with tempfile.TemporaryDirectory() as root:
            result = {"patterns": [{"kind": "abstract_pattern", "source_url": "https://orbi.kr/0006658324"}],
                      "training_performed": False, "pattern_records": 1}
            output = Path(root) / "output"
            report = collector.write_results(result, output)
            raw = (output / "patterns.jsonl").read_bytes()
            self.assertNotIn(b"\r\n", raw)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), report["files"]["patterns.jsonl"]["sha256"])


if __name__ == "__main__":
    unittest.main()
