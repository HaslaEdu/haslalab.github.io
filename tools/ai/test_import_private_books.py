"""Local fixtures only: source integrity, extraction gates, and review boundaries."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from import_private_books import prepare, quality, read_source_index


class PrivateBooksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source_dir = self.root / "originals"
        self.source_dir.mkdir()
        self.pdf = self.source_dir / "book001.pdf"
        self.pdf.write_bytes(b"fixture PDF bytes; no parser or network needed")
        self.pdf_hash = hashlib.sha256(self.pdf.read_bytes()).hexdigest()
        self.pages = ["A complete, readable synthetic mechanics page. " * 4,
                      {"page": 2, "text": ""},
                      {"page": 3, "text": "\ufffd" * 120}]
        self.cache = self.pdf.with_suffix(".text.json")
        self.cache.write_text(json.dumps({"pages": self.pages}), encoding="utf-8")
        self.source = {
            "id": "src_fixture", "drive_id": "book001", "title": "Synthetic mechanics",
            "revision": "v1", "sha256": self.pdf_hash, "page_count": 3,
            "source_language": "en", "subjects": ["physics"], "level": "undergraduate",
            "origin": {"license_identifier": "CC-BY-NC-SA-4.0", "kind": "url",
                       "url": "https://example.test/book"},
        }
        self.index = self.root / "index.json"
        self.write_index()
        self.output = self.root / "new-private-output"

    def tearDown(self):
        self.temp.cleanup()

    def write_index(self, sources=None):
        self.index.write_text(json.dumps({"normalized_sources": sources or [self.source]}), encoding="utf-8")

    def run_prepare(self):
        return prepare(self.source_dir, self.index, self.output, "test user local processing request")

    def test_keeps_book_identity_preserves_text_and_never_approves(self):
        before = self.pdf.read_bytes(), self.cache.read_bytes(), self.index.read_bytes()
        report = self.run_prepare()
        records = [json.loads(line) for line in (self.output / "pages.jsonl").read_text(encoding="utf-8").splitlines()]
        sources = json.loads((self.output / "sources.json").read_text(encoding="utf-8"))
        self.assertEqual(len(records), 3)
        self.assertEqual(len({r["document_id"] for r in records}), 1)
        self.assertEqual(len({r["id"] for r in records}), 3)
        self.assertEqual(records[0]["text"], self.pages[0])
        self.assertEqual(records[1]["metadata"]["cached_page_label"], 2)
        self.assertEqual(report["quality_counts"], {"ready_for_review": 1, "pending_extraction": 2})
        for record in records:
            self.assertEqual(record["review_status"], "pending")
            self.assertEqual(record["metadata"]["rights_review"], "pending")
            self.assertFalse(record["metadata"]["training_eligible"])
        self.assertEqual(sources[0]["origin"], self.source["origin"])
        self.assertEqual(sources[0]["license_identifier"], "CC-BY-NC-SA-4.0")
        self.assertFalse(sources[0]["processing_authorization"]["model_training_license_asserted"])
        self.assertEqual(report["external_uploads"], 0)
        self.assertEqual(before, (self.pdf.read_bytes(), self.cache.read_bytes(), self.index.read_bytes()))

    def test_pointer_hash_is_verified_before_writing(self):
        pointer = self.root / "pointer.json"
        pointer.write_text(json.dumps({"source_index": {"path": "index.json", "sha256": "0" * 64}}))
        with self.assertRaisesRegex(ValueError, "pointer hash"):
            prepare(self.source_dir, pointer, self.output, "test authorization")
        self.assertFalse(self.output.exists())
        pointer.write_text(json.dumps({"source_index": {"path": "index.json",
                           "sha256": hashlib.sha256(self.index.read_bytes()).hexdigest()}}))
        self.assertEqual(read_source_index(pointer)[0][0]["id"], "src_fixture")

    def test_registered_page_count_mismatch_holds_every_page(self):
        self.source["page_count"] = 10
        self.write_index()
        report = self.run_prepare()
        self.assertEqual(report["quality_counts"], {"pending_extraction": 3})
        self.assertEqual(report["quality_issue_counts"]["registered_page_count_mismatch"], 3)

    def test_hash_mismatch_is_not_matched_by_filename(self):
        self.pdf.write_bytes(b"different and unregistered content")
        report = self.run_prepare()
        self.assertEqual(report["matched_book_count"], 0)
        self.assertEqual(report["skipped"][0]["reason"], "unmatched_pdf_hash")
        self.assertEqual((self.output / "pages.jsonl").read_bytes(), b"")

    def test_existing_outputs_and_original_directory_are_protected(self):
        self.output.mkdir()
        sentinel = self.output / "keep.txt"
        sentinel.write_text("existing result")
        with self.assertRaises(FileExistsError):
            self.run_prepare()
        self.assertEqual(sentinel.read_text(), "existing result")
        with self.assertRaisesRegex(ValueError, "separate"):
            prepare(self.source_dir, self.index, self.source_dir / "new", "test")

    def test_malformed_page_does_not_leave_partial_output(self):
        self.cache.write_text(json.dumps({"pages": ["good text", {"page": 2}]}))
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_unstated_license_is_not_inferred_from_private_request(self):
        self.source.pop("origin")
        self.write_index()
        self.run_prepare()
        source = json.loads((self.output / "sources.json").read_text(encoding="utf-8"))[0]
        self.assertIsNone(source["license_identifier"])
        self.assertEqual(source["rights_review"], "pending")
        self.assertFalse(source["processing_authorization"]["copyright_ownership_asserted"])

    def test_native_text_quality_is_independent_of_license(self):
        self.assertEqual(quality("x" * 120)["status"], "ready_for_review")
        self.assertEqual(quality(" \n")["issues"], ["empty_native_text"])
        self.assertIn("unexpected_control_ratio", quality("a" * 100 + "\x00" * 10)["issues"])


if __name__ == "__main__":
    unittest.main()
