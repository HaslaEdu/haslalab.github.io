"""Offline public-reader/author/nonce/stop fixtures; no network or paid APIs."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import community_collect as community
import dc_public_comments as dc


SCRIPT_URL = dc.ORIGIN + "/_js/comment.js?v=fixture"
SCRIPT = "var viewComments = function(nPage, sType, bScroll) { $.ajax({type:'POST',url:'/board/comment/',success:function(data){var comments = data.comments;}}); }"
SCRIPT_HASH = hashlib.sha256(SCRIPT.encode()).hexdigest()
POST = dc.ORIGIN + "/board/view/?id=exam_new2&no=7"


def response(url, text, status=200):
    return community.Response(url, status, text.encode(), {"content-type": "text/html; charset=utf-8"})


def post_html(author="fixture-source-author", *, nonce="private-nonce-never-log", secret="", script=SCRIPT_URL, extra=""):
    return (f'<div class="gallview_head"><div class="gall_writer ub-writer" data-nick="{author}"></div></div>'
            '<span class="title_subject">source title</span><div class="write_div">source question</div>'
            f'<input id="id" value="exam_new2"><input id="no" value="7"><input id="e_s_n_o" value="{nonce}">'
            f'<input id="secret_article_key" value="{secret}"><input id="_GALLTYPE_" value="G">'
            f'<script src="{script}"></script><script>{extra}</script>')


def comment(number=11, *, name="fixture-comment-author", depth=0, parent=0, memo="A visible response", **extra):
    return {"no": number, "c_no": parent, "depth": depth, "name": name, "memo": memo,
            "del_yn": "N", "nicktype": "NICK", "voice": "", "vr_player": "", **extra}


class FakeClient:
    def __init__(self, *, html=None, comments=None, robots_status=200, script=SCRIPT, post_status=200):
        self.routes = {dc.ORIGIN + "/robots.txt": response(dc.ORIGIN + "/robots.txt", "User-agent: *\nAllow: /\n", robots_status),
                       POST: response(POST, html or post_html()), SCRIPT_URL: response(SCRIPT_URL, script)}
        self.comments = [comment()] if comments is None else comments
        self.post_status, self.requests, self.post_calls = post_status, [], []

    def get(self, url):
        self.requests.append({"url": url, "method": "GET"})
        if url not in self.routes:
            raise AssertionError("unexpected fixture request")
        return self.routes[url]

    def post_read_fixture(self, endpoint, payload, referer):
        self.post_calls.append({"endpoint": endpoint, "payload": dict(payload), "referer": referer})
        return response(endpoint, json.dumps({"comments": self.comments, "total_cnt": len(self.comments)}), self.post_status)


class PublicReaderTests(unittest.TestCase):
    def reader(self, client=None, **kwargs):
        client = client or FakeClient()
        return dc.PublicReader(client=client, expected_script_sha256=SCRIPT_HASH, **kwargs), client

    def test_official_read_uses_only_fixed_endpoint_and_never_persists_nonce_or_names(self):
        reader, client = self.reader()
        metadata, preview = reader.read_post(POST, "exam_new2")
        self.assertEqual(len(client.post_calls), 1)
        call = client.post_calls[0]
        self.assertEqual(call["endpoint"], dc.ORIGIN + "/board/comment/")
        self.assertEqual(call["payload"]["e_s_n_o"], "private-nonce-never-log")
        self.assertEqual(call["payload"]["comment_page"], "1")
        self.assertEqual(call["payload"]["secret_article_key"], "")
        self.assertFalse(metadata["training_eligible"])
        self.assertFalse(metadata["raw_content_saved"])
        encoded = json.dumps(metadata)
        for private_value in ("private-nonce-never-log", "fixture-source-author", "fixture-comment-author", "A visible response"):
            self.assertNotIn(private_value, encoded)
        self.assertEqual(metadata["author_filter"], {"policy_version": "exclude-bugiu-v1", "post_author_checked": True,
            "selected_reply_authors_checked": True, "reply_branch_checked": True, "excluded_author_present": False})
        self.assertEqual(preview["root_comments"][0]["text"], "A visible response")

    def test_changed_script_or_non_read_semantics_stops_before_post(self):
        for script, expected in ((SCRIPT + "changed", "official_script_changed_requires_review"),
                                 ("var unrelated = 1", "official_read_semantics_unverified")):
            client = FakeClient(script=script)
            digest = SCRIPT_HASH if expected.startswith("official_script_changed") else hashlib.sha256(script.encode()).hexdigest()
            reader = dc.PublicReader(client=client, expected_script_sha256=digest)
            with self.assertRaises(dc.ReadError) as raised:
                reader.read_post(POST, "exam_new2")
            self.assertEqual(str(raised.exception), expected)
            self.assertEqual(client.post_calls, [])

    def test_read_payload_cannot_target_an_unbound_or_previously_denied_thread(self):
        reader, client = self.reader()
        reader.read_post(POST, "exam_new2")
        valid = client.post_calls[0]["payload"]
        cases = [(valid | {"no": "8"}, POST), (valid | {"cmt_id": "other"}, POST),
                 (valid | {"secret_article_key": "private"}, POST),
                 (valid | {"memo": "must never submit content"}, POST),
                 (valid, "https://outside.invalid/board/view/?id=exam_new2&no=7"),
                 (valid | {"id": "physics", "no": "391", "cmt_id": "physics", "cmt_no": "391"},
                  dc.ORIGIN + "/mgallery/board/view/?id=physics&no=391")]
        for payload, referer in cases:
            with self.assertRaises(dc.ReadError): reader._read_comment_json(payload, referer)
        self.assertEqual(len(client.post_calls), 1)

    def test_post_identity_is_redacted_from_transient_preview_too(self):
        client = FakeClient(html=post_html().replace("source question", "fixture-source-author asks a question"))
        reader, _ = self.reader(client)
        metadata, preview = reader.read_post(POST, "exam_new2")
        for value in (metadata, preview):
            self.assertNotIn("fixture-source-author", json.dumps(value))

    def test_secret_article_missing_nonce_and_excluded_author_never_issue_read_post(self):
        cases = [(post_html(secret="private-key"), "secret_article_not_supported"),
                 (post_html(nonce=""), "public_read_parameters_unavailable"),
                 (post_html(author=" 부 기 우 (127.0.0.1) "), "excluded_post_author")]
        for html, expected in cases:
            client = FakeClient(html=html)
            reader, _ = self.reader(client)
            with self.assertRaises(dc.ReadError) as raised:
                reader.read_post(POST, "exam_new2")
            self.assertEqual(str(raised.exception), expected)
            self.assertEqual(client.post_calls, [])

    def test_private_or_outside_scripts_and_gallery_bindings_are_not_followed(self):
        client = FakeClient(html=post_html(script="https://outside.invalid/_js/comment.js"))
        reader, _ = self.reader(client)
        with self.assertRaises(dc.ReadError):
            reader.read_post(POST, "exam_new2")
        self.assertFalse(any("outside.invalid" in row["url"] for row in client.requests))
        self.assertEqual(client.post_calls, [])
        for url, gallery in ((dc.ORIGIN + "/board/view/?id=physicalscience&no=1", "physicalscience"),
                             (dc.ORIGIN + "/mgallery/board/view/?id=physics&no=391", "physics"),
                             (dc.ORIGIN + "/mgallery/board/view/?id=physics&no=380", "physics")):
            with self.assertRaises(dc.ReadError): dc.gallery_url(url, "post", gallery)
        allowed = dc.ORIGIN + "/mgallery/board/view/?id=physics&no=398"
        self.assertEqual(dc.gallery_url(allowed, "post", "physics"), allowed)
        with self.assertRaises(dc.ReadError):
            dc.gallery_url(dc.ORIGIN + "/board/lists/?id=physicalscience", "listing", "physicalscience")

    def test_public_alias_is_validated_instead_of_reading_an_unrelated_comment_thread(self):
        for extra, permitted in (("$(document).data('comment_id', 'other');", False),
                                  ("$(document).data('article_no', 7);", True),
                                  ("$(document).data('comment_no', dynamicValue);", False)):
            client = FakeClient(html=post_html(extra=extra))
            reader, _ = self.reader(client)
            if permitted:
                reader.read_post(POST, "exam_new2")
                self.assertEqual(len(client.post_calls), 1)
            else:
                with self.assertRaises(dc.ReadError) as raised: reader.read_post(POST, "exam_new2")
                self.assertEqual(str(raised.exception), "public_comment_alias_not_supported")
                self.assertEqual(client.post_calls, [])

    def test_403_stops_source_and_persistent_state_prevents_restart(self):
        with tempfile.TemporaryDirectory() as temporary:
            stop = Path(temporary) / "access-stop.json"
            reader, client = self.reader(FakeClient(post_status=403), access_stop_file=stop)
            with self.assertRaises(dc.ReadError) as raised: reader.read_post(POST, "exam_new2")
            self.assertEqual(str(raised.exception), "http_403")
            requests_before = len(client.requests)
            with self.assertRaises(dc.ReadError): reader.read_post(POST, "exam_new2")
            self.assertEqual(len(client.requests), requests_before)
            other = FakeClient()
            with self.assertRaises(dc.ReadError): self.reader(other, access_stop_file=stop)
            self.assertEqual(other.requests, [])

    def test_stop_file_prevents_even_the_first_robots_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            stop = Path(temporary) / "training-finished"
            stop.touch()
            client = FakeClient()
            with self.assertRaises(dc.ReadError): self.reader(client, stop_file=stop)
            self.assertEqual(client.requests, [])

    def test_robots_404_is_absence_but_403_and_500_fail_closed(self):
        reader, client = self.reader(FakeClient(robots_status=404))
        reader.read_post(POST, "exam_new2")
        self.assertEqual(len(client.post_calls), 1)
        for status in (403, 429, 500):
            with self.assertRaises(dc.ReadError): self.reader(FakeClient(robots_status=status))

    def test_redirect_to_denied_gallery_is_rejected_before_following(self):
        client = FakeClient()
        client.routes[POST] = community.Response(POST, 302, headers={"location": "/board/view/?id=physicalscience&no=2"})
        reader, _ = self.reader(client)
        with self.assertRaises(dc.ReadError): reader.read_post(POST, "exam_new2")
        self.assertEqual([row["url"] for row in client.requests], [dc.ORIGIN + "/robots.txt", POST])

    def test_excluded_author_branch_and_unknown_parent_are_never_retained(self):
        rows = [comment(1, name="부기우"), comment(11, depth=1, parent=1), comment(2),
                comment(3), comment(31, name="부 기 우", depth=1, parent=3),
                comment(4, name=""), comment(91, depth=1, parent=99),
                comment(5), comment(51, name=" \u1107\u116e \u1100\u1175 \u110b\u116e (123.45) ", depth=1, parent=5)]
        retained, counts, _ = dc.visible_comments(rows)
        self.assertEqual([row["comment_id"] for row in retained], ["2"])
        self.assertEqual(counts["excluded_author_branches"], 3)
        self.assertEqual(counts["unknown_author_or_parent_branches"], 2)

    def test_deleted_bot_and_media_text_are_not_conversation_text(self):
        rows = [comment(1, del_yn="Y", memo="deleted private text"),
                comment(2, nicktype="COMMENT_BOY", memo="bot promotion"),
                comment(3, memo='<img src="private-url">'), comment(4, memo="first<br>second")]
        retained, counts, _ = dc.visible_comments(rows)
        self.assertEqual([row["comment_id"] for row in retained], ["3", "4"])
        self.assertEqual(retained[0]["text"], "")
        self.assertEqual(retained[1]["text"], "first\nsecond")
        self.assertNotIn("deleted private text", json.dumps(retained))

    def test_bad_relationship_or_visibility_schema_fails(self):
        for row in (comment(depth=2), comment(depth=1,parent=None), comment(del_yn="?"), comment(memo=None)):
            with self.assertRaises(dc.ReadError): dc.visible_comments([row])

    def test_duplicate_comment_ids_cannot_supply_ambiguous_parentage(self):
        with self.assertRaises(dc.ReadError) as raised:
            dc.visible_comments([comment(1), comment(1, depth=1, parent=1)])
        self.assertEqual(str(raised.exception), "duplicate_comment_id")

    def test_actual_listing_rows_skip_notices_and_excluded_author_before_get(self):
        html = '<table>'
        for number, name in (("공지", "safe"), ("7", "부기우"), ("8", "safe")):
            html += f'<tr class="ub-content"><td class="gall_num">{number}</td><td><a href="/board/view/?id=exam_new2&no=8">title<span class="reply_num">[2]</span></a></td><td class="gall_writer" data-nick="{name}"></td></tr>'
        page = dc.Listing(dc.ORIGIN + "/board/lists/?id=exam_new2", "exam_new2")
        page.feed(html + '</table>')
        self.assertEqual(page.candidates(), [dc.ORIGIN + "/board/view/?id=exam_new2&no=8"])

    def test_atomic_checkpoint_preserves_prior_complete_file_when_replace_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "observations.jsonl"
            path.write_bytes(b'{"complete":1}\n')
            with patch.object(dc.os, "replace", side_effect=OSError("fixture full disk")):
                with self.assertRaises(OSError): dc.write_atomic(path, b'{"complete":2}\n')
            self.assertEqual(path.read_bytes(), b'{"complete":1}\n')
            self.assertFalse(path.with_name(path.name + ".partial").exists())

    def test_private_output_rejects_repository_and_onedrive(self):
        with self.assertRaises(dc.ReadError): dc.private_path(Path(dc.__file__).resolve().parent)
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(dc.ReadError): dc.private_path(Path(temporary) / "OneDrive - Personal" / "output")


if __name__ == "__main__":
    unittest.main()
