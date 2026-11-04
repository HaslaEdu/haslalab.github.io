"""Offline fixture tests; these tests must never contact community websites."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from urllib import error

import community_collect as collector


def response(url, html, status=200, headers=None):
    return collector.Response(url, status, html.encode("utf-8"), headers or {"content-type": "text/html; charset=utf-8"})


class FakeClient:
    def __init__(self, routes):
        self.routes, self.requests = routes, []

    def get(self, url):
        if url not in self.routes:
            raise AssertionError("unexpected request: " + url)
        self.requests.append({"url": url, "status": self.routes[url].status})
        return self.routes[url]


class CommunityCollectorTests(unittest.TestCase):
    def test_ai_training_group_blocks_without_disguising_user_agent(self):
        text = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
        decision = collector.robots_decision(text, "https://orbi.kr/list")
        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["reason"], "ai_training_crawler_excluded")
        self.assertIn("purpose=", collector.USER_AGENT)

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

    def test_features_store_no_raw_content_or_personal_identifiers(self):
        html = '<h1>PRIVATE TITLE</h1><div class="content-text">왜 x = 2 인지 설명해주세요? secret@example.com 010-1234-5678</div><div class="comment-text">이유는 계산하면 됩니다.</div><script>SECRET SCRIPT</script>'
        pattern = collector.extract_pattern("orbi", "https://orbi.kr/0006658324", html, collector.source_metadata("orbi"))
        serialized = json.dumps(pattern, ensure_ascii=False)
        for secret in ("PRIVATE TITLE", "secret@example.com", "010-1234-5678", "설명해주세요", "SECRET SCRIPT"):
            self.assertNotIn(secret, serialized)
        self.assertIn("explanation", pattern["body"]["question_types"])
        self.assertTrue(pattern["body"]["has_math"])
        self.assertFalse(pattern["training_eligible"])
        self.assertEqual(pattern["structure"]["visible_comment_blocks"], 1)
        self.assertFalse(pattern["structure"]["comments_are_answers"])

    def test_global_post_budget_and_duplicate_links(self):
        origin = "https://orbi.kr"
        listing = origin + "/list"
        routes = {origin + "/robots.txt": response(origin + "/robots.txt", "User-agent: *\nAllow: /\n"),
                  listing: response(listing, ''.join('<a href="/000%d/title">post</a>' % i for i in (6658324, 6658324, 6658325, 6658326)))}
        for number in (6658324, 6658325):
            url = origin + "/000" + str(number)
            routes[url] = response(url, '<article><div class="content-text">왜 맞나요? x = 2</div></article>')
        result = collector.collect(["orbi"], max_posts=2, client=FakeClient(routes))
        self.assertEqual(result["thread_requests"], 2)
        self.assertEqual(result["pattern_records"], 2)
        self.assertEqual(len(result["requests"]), 4)

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
            self.assertFalse(report["training_performed"])
            self.assertEqual(report["pattern_records"], 0)
            with self.assertRaises(ValueError):
                collector.write_results(result, out)


if __name__ == "__main__":
    unittest.main()
