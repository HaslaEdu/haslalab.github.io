"""Synthetic, offline checks for corpus lineage and leakage prevention."""
import json
import hashlib
from pathlib import Path
import tempfile
import unittest

import corpus_prepare as cp


def source(key, **values):
    return {"id": key, "source": "local_fixture", "rights_status": "user_authorized", "allowed_uses": ["train"], **values}


def chat(key, source_id, **values):
    return {"id": key, "source_id": source_id, "review_status": "approved", "question": "어떤 순서로 풀까요? " + key,
            "answer": "조건을 먼저 적고 계산해 봐. " + key, **values}


class CorpusTests(unittest.TestCase):
    def test_unknown_rights_and_pending_are_retained_but_not_exported(self):
        records = [chat("a", "owned"), chat("b", "unknown"), chat("c", "owned", review_status="pending")]
        result = cp.prepare_corpus(records, [source("owned"), source("unknown", rights_status="unknown")], "v1")
        self.assertEqual(len(result["records"]), 3)
        self.assertEqual(sum(map(len, result["exports"].values())), 1)
        self.assertEqual(result["manifest"]["exclusions"], {"review_pending": 1, "rights_unknown": 1})

    def test_textbook_chunks_remain_text_and_one_split(self):
        text = "가상의 역학 교재 문단입니다. 힘과 운동을 설명하는 합성 자료입니다.\n\n" * 20
        result = cp.prepare_corpus([{"id": "book", "source_id": "book-source", "review_status": "approved", "text": text}],
                                   [source("book-source")], "v1", chunk_chars=200, overlap=20)
        self.assertGreater(len(result["records"]), 2)
        self.assertEqual(len({r["metadata"]["split"] for r in result["records"]}), 1)
        for row in result["records"]:
            self.assertIn("text", row)
            self.assertNotIn("messages", row)
            self.assertEqual(row["metadata"]["document_id"], "book")
            start, end = row["metadata"]["char_start"], row["metadata"]["char_end"]
            self.assertEqual(row["text"], text.strip()[start:end])

    def test_thread_and_conversation_links_group_multiple_documents(self):
        rows = [chat("a", "a", thread_id="thread-one"), chat("b", "b", thread_id="thread-one"),
                chat("c", "c", conversation_id="conversation-one"), chat("d", "d", conversation_id="conversation-one")]
        result = cp.prepare_corpus(rows, [source(k) for k in "abcd"], "v1")
        by_id = {r["id"]: r for r in result["records"]}
        self.assertEqual(by_id["a"]["metadata"]["group_id"], by_id["b"]["metadata"]["group_id"])
        self.assertEqual(by_id["c"]["metadata"]["group_id"], by_id["d"]["metadata"]["group_id"])

    def test_same_numeric_thread_on_different_sites_is_not_a_link(self):
        result = cp.prepare_corpus([chat("a", "a", thread_id="42", source="site_a"),
                                    chat("b", "b", thread_id="42", source="site_b")], [source("a"), source("b")], "v1")
        self.assertEqual(result["manifest"]["groups"], 2)

    def test_exact_duplicate_prefers_train_eligible_lineage(self):
        rows = [chat("a", "unknown", question="왜 그런가요?", answer="이것은 합성 설명입니다."),
                chat("b", "known", question="왜 그런가요?", answer="이것은 합성 설명입니다.")]
        result = cp.prepare_corpus(rows, [source("unknown", rights_status="unknown"), source("known")], "v1")
        exported = [r for group in result["exports"].values() for r in group]
        self.assertEqual([r["id"] for r in exported], ["b"])
        self.assertEqual(result["records"][0]["metadata"]["duplicate_of"], "b")
        self.assertEqual(result["manifest"]["groups"], 1)

    def test_near_duplicates_are_grouped_without_content_replacement(self):
        text = "".join("가상의문장번호" + str(i) + "이다." for i in range(80))
        rows = [{"id": "a", "source_id": "a", "text": text, "review_status": "approved"},
                {"id": "b", "source_id": "b", "text": text.replace("번호20", "번호21", 1), "review_status": "approved"}]
        result = cp.prepare_corpus(rows, [source("a"), source("b")], "v1")
        self.assertEqual(result["manifest"]["groups"], 1)
        self.assertEqual(len(result["records"]), 2)
        self.assertFalse(any(r["metadata"].get("duplicate_of") for r in result["records"]))

    def test_input_order_does_not_change_assignments_or_exports(self):
        rows = [chat(str(i), "s" + str(i)) for i in range(40)]
        sources = [source("s" + str(i)) for i in range(40)]
        a = cp.prepare_corpus(rows, sources, "v1")
        b = cp.prepare_corpus(list(reversed(rows)), list(reversed(sources)), "v1")
        self.assertEqual(a, b)

    def test_thread_roles_must_be_explicit_and_alternate(self):
        with self.assertRaisesRegex(ValueError, "string"):
            cp.prepare_corpus([{"source_id": "s", "comments": [{"text": "untyped"}]}], [source("s")], "v1")
        with self.assertRaisesRegex(ValueError, "same role"):
            cp.prepare_corpus([{"source_id": "s", "messages": [{"role": "user", "content": "one"},
                              {"role": "user", "content": "two"}, {"role": "assistant", "content": "three"}]}], [source("s")], "v1")
        with self.assertRaisesRegex(ValueError, "start with user"):
            cp.prepare_corpus([{"source_id": "s", "messages": [{"role": "assistant", "content": "invented answer"}]}], [source("s")], "v1")

    def test_text_quality_exclusions_do_not_reject_equations_by_symbol_ratio(self):
        rows = [{"id": "short", "source_id": "s", "text": "짧은 자료", "review_status": "approved"},
                {"id": "broken", "source_id": "s", "text": "a\ufffd" * 80, "review_status": "approved"},
                {"id": "math", "source_id": "s", "text": r"F=ma; E=mc^2; \frac{a}{b}=3.14; " * 10, "review_status": "approved"}]
        result = cp.prepare_corpus(rows, [source("s")], "v1")
        exported = [r for group in result["exports"].values() for r in group]
        self.assertEqual([r["id"] for r in exported], ["math"])
        self.assertEqual(result["manifest"]["exclusions"], {"text_encoding_damage": 1, "text_too_short": 1})

    def test_removed_sources_and_missing_training_scope_are_excluded(self):
        result = cp.prepare_corpus([chat("a", "a"), chat("b", "b")],
                                   [source("a", deleted_at="2026-11-04"), source("b", allowed_uses=["inventory"])], "v1")
        self.assertEqual(result["manifest"]["exclusions"], {"source_removed": 1, "training_not_in_allowed_uses": 1})

    def test_pattern_report_contains_aggregates_only(self):
        secret = "ONLY_FOR_PRIVATE_FIXTURE_9988"
        result = cp.prepare_corpus([chat("a", "a", answer=secret + " 조건부터 보면 됨 ㅋㅋ")], [source("a")], "v1")
        self.assertNotIn(secret, json.dumps(result["patterns"], ensure_ascii=False))
        self.assertEqual(result["patterns"]["assistant_features"]["laughter"], 1)

    def test_private_output_boundary_and_no_overwrite(self):
        prepared = cp.prepare_corpus([chat("a", "a")], [source("a")], "v1")
        with self.assertRaisesRegex(ValueError, "outside"):
            cp.write_corpus(prepared, cp.REPO_ROOT / "corpus-fixture")
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "v1"
            manifest = cp.write_corpus(prepared, target)
            self.assertTrue((target / "normalized.jsonl").is_file())
            self.assertEqual(manifest["files"]["normalized.jsonl"]["records"], 1)
            self.assertEqual(manifest["files"]["normalized.jsonl"]["sha256"],
                             hashlib.sha256((target / "normalized.jsonl").read_bytes()).hexdigest())
            with self.assertRaisesRegex(ValueError, "empty"):
                cp.write_corpus(prepared, target)


if __name__ == "__main__":
    unittest.main()
