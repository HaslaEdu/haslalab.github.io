"""Offline fixture tests; these tests must never contact community websites."""
import io
import hashlib
import contextlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib import error
from http.client import IncompleteRead
import ssl

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
    def test_author_normalization_is_exact_and_removes_display_ip_only(self):
        self.assertEqual(collector.normalized_author('  부 기 우 (１２７.０.０.１) '), '부기우')
        self.assertEqual(collector.normalized_author('부기우(123.45)'), '부기우')
        self.assertNotIn(collector.normalized_author('부기우님'), collector.EXCLUDED_AUTHORS)

    def test_excluded_post_author_is_not_a_feature_record(self):
        html = '<div class="layout-board-read"><div class="author-wrap"><a class="nickname"> 부 기 우 </a></div><div class="content-wrap">plain post</div></div>'
        self.assertIsNone(collector.extract_pattern('orbi', 'https://orbi.kr/000123', html, {}))
        dc = '<div class="gallview_head"><div class="gall_writer ub-writer" data-nick="부기우"></div></div><div class="write_div">body</div>'
        self.assertIsNone(collector.extract_pattern('dcinside', 'https://gall.dcinside.com/mgallery/board/view/?id=physics&no=398', dc, {}))

    def test_collector_reports_author_exclusion_instead_of_missing_content(self):
        robots='https://orbi.kr/robots.txt';listing='https://orbi.kr/list';post='https://orbi.kr/00079999123'
        html='<div class="layout-board-read"><div class="author-wrap"><a class="nickname">부기우</a></div><div class="content-wrap">body that must not become a feature</div></div>'
        client=FakeClient({robots:response(robots,'User-agent: *\nAllow: /\n'),listing:response(listing,'<a href="/00079999123">question</a>'),post:response(post,html)})
        result=collector.collect(['orbi'],client=client)
        self.assertEqual(result['pattern_records'],0)
        self.assertEqual(result['sources'][0]['thread_results'][0]['status'],'excluded_post_author')

    def test_body_mention_is_not_an_author_match_and_names_are_not_saved(self):
        html = '<div class="layout-board-read"><div class="author-wrap"><a class="nickname">safe-author-private</a></div><div class="content-wrap">부기우라는 이름을 언급한 글</div><div class="comment-wrap"><ul><li class="comment comment-rank-0"><div class="meta-wrap"><a class="nickname">reply-author-private</a></div><div class="comment-content">relevant reply</div></li></ul></div></div>'
        record = collector.extract_pattern('orbi', 'https://orbi.kr/000123', html, {})
        self.assertIsNotNone(record)
        policy = record['metadata']['author_filter']
        self.assertEqual(policy, {'policy_version':'exclude-bugiu-v1','post_author_checked':True,
                                 'selected_reply_authors_checked':True,'reply_branch_checked':True,
                                 'excluded_author_present':False})
        self.assertNotIn('safe-author-private', json.dumps(record))
        self.assertNotIn('reply-author-private', json.dumps(record))
        self.assertFalse(record['training_eligible'])

    def test_excluded_comment_and_descendant_branch_are_removed(self):
        def comment(name, text, depth):
            return f'<li class="comment comment-rank-{depth}"><div class="meta-wrap"><a class="nickname">{name}</a></div><div class="comment-content">{text}</div></li>'
        excluded_parent = '<li class="comment comment-rank-0"><div class="meta-wrap"><a class="nickname">부기우</a></div><div class="comment-content">excluded text</div><ul>' + comment('safe child','excluded branch reply',1) + '</ul></li>'
        html = '<div class="layout-board-read"><div class="author-wrap"><a class="nickname">safe</a></div><div class="content-wrap">post</div><div class="comment-wrap"><ul>' + excluded_parent + comment('safe sibling','retained reply',0) + '</ul></div></div>'
        page = collector.Page('orbi'); page.feed(html)
        self.assertEqual(page.texts('comment'), ['retained reply'])
        self.assertTrue(page.author_filter([0])['excluded_author_present'])
        self.assertTrue(page.author_filter([1])['excluded_author_present'])
        self.assertEqual(page.author_filter([2]), {'policy_version':'exclude-bugiu-v1','post_author_checked':True,
                                                  'selected_reply_authors_checked':True,'reply_branch_checked':True,
                                                  'excluded_author_present':False})
        record = collector.extract_pattern('orbi','https://orbi.kr/000123',html,{})
        self.assertEqual(len(record['comment_features']),1)

    def test_unknown_identity_or_parent_structure_never_claims_filter_checked(self):
        html = orbi_post('body','<li class="comment"><div class="meta-wrap"><a class="nickname">부기우</a></div><div class="comment-content">blocked</div></li><li class="comment"><div class="meta-wrap"><a class="nickname">safe</a></div><div class="comment-content">uncertain reply branch</div></li>')
        page=collector.Page('orbi'); page.feed(html)
        self.assertEqual(page.texts('comment'),[])
        policy=page.author_filter([1])
        self.assertFalse(policy['post_author_checked'])
        self.assertFalse(policy['reply_branch_checked'])
        self.assertTrue(policy['excluded_author_present'])
        missing=collector.extract_pattern('orbi','https://orbi.kr/000123',orbi_post('body','<div class="comment-content">reply</div>'),{})
        self.assertFalse(missing['metadata']['author_filter']['selected_reply_authors_checked'])
        self.assertFalse(missing['training_eligible'])

    def test_sidebar_identity_does_not_authorize_the_post(self):
        html='<aside><div class="author-wrap"><a class="nickname">safe</a></div></aside>'+orbi_post('post')
        page=collector.Page('orbi'); page.feed(html)
        self.assertFalse(page.author_filter()['post_author_checked'])

    def test_flat_css_ranks_do_not_prove_an_excluded_comment_has_no_replies(self):
        html=orbi_post('body','<li class="comment comment-rank-0"><div class="meta-wrap"><a class="nickname">부기우</a></div><div class="comment-content">blocked</div></li><li class="comment comment-rank-0"><div class="meta-wrap"><a class="nickname">safe</a></div><div class="comment-content">possibly related reply</div></li>')
        page=collector.Page('orbi');page.feed(html)
        self.assertEqual(page.texts('comment'),[])
        self.assertFalse(page.author_filter([1])['reply_branch_checked'])

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

    def test_missing_gone_and_external_redirect_threads_are_skipped_without_retry_or_follow(self):
        origin = "https://orbi.kr"
        for status, headers, reason in ((404, {}, "http_404"), (410, {}, "http_410"),
                                        (302, {"location": "https://other.example/private"}, "redirect_outside_public_source")):
            with self.subTest(status=status):
                routes = {origin + "/robots.txt": response(origin + "/robots.txt", "User-agent: *\nAllow: /\n"),
                          origin + "/list": response(origin + "/list", '<a href="/0006658324">old</a><a href="/0006658325">next</a>'),
                          origin + "/0006658324": response(origin + "/0006658324", "", status, headers),
                          origin + "/0006658325": response(origin + "/0006658325", orbi_post("정상 본문입니다."))}
                client = FakeClient(routes)
                result = collector.collect(["orbi"], client=client)
                self.assertEqual(result["pattern_records"], 1)
                self.assertEqual(result["sources"][0]["skipped_thread_failures"], {reason: 1})
                self.assertNotIn("reason", result["sources"][0])
                self.assertEqual(len(client.requests), 4)

    def test_rate_limit_challenge_login_and_robots_stop_entire_source(self):
        origin = "https://orbi.kr"
        cases = [(429, "", "User-agent: *\nAllow: /\n", "http_429"),
                 (200, "<title>Just a moment</title>", "User-agent: *\nAllow: /\n", "challenge_or_access_block"),
                 (200, '<input type="password">', "User-agent: *\nAllow: /\n", "login_required"),
                 (200, "unused", "User-agent: *\nDisallow: /0006658324\nAllow: /\n", "robots_denied")]
        for status, body, robots, reason in cases:
            with self.subTest(reason=reason):
                routes = {origin + "/robots.txt": response(origin + "/robots.txt", robots),
                          origin + "/list": response(origin + "/list", '<a href="/0006658324">first</a><a href="/0006658325">never</a>'),
                          origin + "/0006658324": response(origin + "/0006658324", body, status)}
                client = FakeClient(routes)
                result = collector.collect(["orbi"], client=client)
                self.assertEqual(result["sources"][0]["reason"], reason)
                self.assertNotIn(origin + "/0006658325", [row["url"] for row in client.requests])

    def test_three_different_consecutive_transport_failures_stop_without_retrying_any_url(self):
        origin = "https://orbi.kr"
        links = [origin + "/000" + str(n) for n in range(6658324, 6658328)]
        routes = {origin + "/robots.txt": response(origin + "/robots.txt", "User-agent: *\nAllow: /\n"),
                  origin + "/list": response(origin + "/list", ''.join('<a href="' + url + '">post</a>' for url in links))}
        for url, failure in zip(links, ("network_incomplete_response", "network_timeout", "network_error")):
            routes[url] = collector.Response(url, failure=failure)
        client = FakeClient(routes)
        result = collector.collect(["orbi"], client=client)
        self.assertEqual(result["sources"][0]["reason"], "transport_circuit_breaker")
        self.assertEqual(result["sources"][0]["consecutive_transport_failures"], 3)
        actual = [row["url"] for row in client.requests]
        self.assertEqual(actual[-3:], links[:3])
        self.assertNotIn(links[3], actual)
        self.assertEqual(len(actual), len(set(actual)))

    def test_success_resets_transport_streak_and_single_failed_urls_are_discarded(self):
        origin = "https://orbi.kr"
        links = [origin + "/000" + str(n) for n in range(6658324, 6658329)]
        routes = {origin + "/robots.txt": response(origin + "/robots.txt", "User-agent: *\nAllow: /\n"),
                  origin + "/list": response(origin + "/list", ''.join('<a href="' + url + '">post</a>' for url in links))}
        for i, url in enumerate(links):
            routes[url] = response(url, orbi_post("정상 본문입니다.")) if i in (1, 4) else collector.Response(url, failure="network_timeout")
        client = FakeClient(routes)
        result = collector.collect(["orbi"], client=client)
        self.assertEqual(result["pattern_records"], 2)
        self.assertEqual(result["sources"][0]["transport_failures"], {"network_timeout": 3})
        self.assertEqual(result["sources"][0]["consecutive_transport_failures"], 0)
        self.assertNotIn("reason", result["sources"][0])
        self.assertEqual(len(client.requests), len({row["url"] for row in client.requests}))

    def test_certificate_failure_is_not_treated_as_an_ordinary_transient_timeout(self):
        class Opener:
            def open(self, req, timeout):
                raise error.URLError(ssl.SSLCertVerificationError("certificate rejected"))
        client = collector.BoundedClient(opener=Opener())
        result = client.get("https://orbi.kr/list")
        self.assertEqual(result.failure, "network_certificate_error")
        self.assertNotIn(result.failure, collector.TRANSPORT_THREAD_FAILURES)

    def test_atomic_checkpoint_retains_full_abstract_rows_after_later_disk_failure(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "progress.json"
            writer = collector.progress_writer(target)
            row = collector.extract_pattern("orbi", "https://orbi.kr/0006658324", orbi_post("왜 맞나요?"), collector.source_metadata("orbi"))
            status = {"source_id": "orbi", "checkpoint": {"patterns": [row], "pattern_records": 1,
                        "raw_content_saved": False, "checkpoint_contains_full_abstract_patterns": True}}
            with contextlib.redirect_stdout(io.StringIO()):
                writer(status)
            previous = target.read_bytes()
            with patch.object(Path, "write_bytes", side_effect=OSError(28, "No space left")), self.assertRaises(OSError):
                writer({"checkpoint": {"patterns": [row, row], "pattern_records": 2}})
            self.assertEqual(target.read_bytes(), previous)
            restored = json.loads(previous)
            self.assertEqual(restored["patterns"][0]["body"]["content_sha256"], row["body"]["content_sha256"])
            self.assertIsInstance(restored["patterns"][0]["body"], dict)

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

    def test_truncated_chunked_response_is_discarded_recorded_and_not_retried(self):
        class Truncated(io.BytesIO):
            status, headers = 200, {"Content-Type": "text/html"}
            def read(self, size=-1):
                raise IncompleteRead(b"PRIVATE PARTIAL HTML", 100)
        class Opener:
            calls = 0
            def open(self, req, timeout):
                self.calls += 1
                return Truncated()
        opener = Opener()
        client = collector.BoundedClient(opener=opener)
        result = client.get("https://orbi.kr/list")
        self.assertEqual(result.failure, "network_incomplete_response")
        self.assertEqual(result.body, b"")
        self.assertEqual(opener.calls, 1)
        self.assertNotIn("PRIVATE PARTIAL HTML", json.dumps(client.requests))

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
