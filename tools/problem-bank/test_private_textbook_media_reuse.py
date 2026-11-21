from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import pymupdf


SPEC = spec_from_file_location("textbook_packer", Path(__file__).with_name("pack-private-textbook-viewer.py"))
packer = module_from_spec(SPEC)
SPEC.loader.exec_module(packer)


class PrivateTextbookMediaReuse(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.intake = self.root / "intake"
        for folder in ("sources", "records", "savchenko"):
            (self.intake / folder).mkdir(parents=True)
        pdf = self.intake / "sources/sample.pdf"
        with pymupdf.open() as doc:
            for n in range(1, 4):
                page = doc.new_page()
                page.insert_text((72, 72), f"Synthetic source page {n}")
            doc.save(pdf)
        self.sha = packer.file_sha256(pdf)
        key = f"sources/{self.sha}.pdf"
        packer.write_json(self.intake / "verified-sources.json", {"sources": [{
            "id": "sample", "sha256": self.sha, "key": key, "byte_length": pdf.stat().st_size,
        }]})
        materials = [{"id": "sample", "title": "Synthetic book", "records": "records/sample.jsonl", "problem_count": 2}]
        packer.write_json(self.intake / "records/catalog.json", {"materials": materials})
        self.rows = [{"id": f"sample:{n}", "source_object": key, "source_sha256": self.sha,
                      "original_number": str(n), "spans": [{"page": n}],
                      "versions": [{"language": "en", "role": "original", "text": f"Synthetic question {n}."}]}
                     for n in (1, 2)]
        with zipfile.ZipFile(self.intake / "savchenko/figures.zip", "w"):
            pass
        self.write_receipts()
        self.base = self.root / "base"
        self.base.mkdir()
        self.release = packer.build(self.intake, self.base, {})
        packer.write_json(self.base / "viewer-object-manifest.json", {"release": self.release})
        self.output = self.root / "output"
        self.output.mkdir()

    def write_receipts(self):
        records = self.intake / "records/sample.jsonl"
        records.write_bytes(b"".join(packer.json_data(row) for row in self.rows))
        files = (records, self.intake / "records/catalog.json", self.intake / "savchenko/figures.zip")
        receipts = [{"key": (packer.INTAKE_PREFIX / file.relative_to(self.intake)).as_posix(),
                     "byte_length": file.stat().st_size, "verified": True, "sha256": packer.file_sha256(file)}
                    for file in files]
        packer.write_json(self.intake / "verified-records.json", receipts)

    def test_reuses_existing_page_links_and_renders_only_missing_source_page(self):
        prior = packer.PriorMedia(self.base, self.release)
        overlays = {"sample:1": {"id": "sample:1", "source_sha256": self.sha,
                                 "review_status": "model_source_reviewed", "text_ko": "예시 문제입니다.",
                                 "figures": [{"source_page": 2}, {"source_page": 3}]}}
        release = packer.build(self.intake, self.output, overlays, prior)
        inherited, = prior.used.values()
        delta, = (self.output / packer.PREFIX / "media").glob("*.bin")
        self.assertNotEqual(inherited[1], delta.stem)
        base = self.output / packer.PREFIX / "releases" / release
        one, two = packer.read_json(base / "sample/batches/0.json")
        self.assertEqual(one["ko"]["text"], "예시 문제입니다.")
        self.assertEqual([m["page"] for m in one["media"]], [1, 2, 3])
        self.assertEqual(one["media"][1]["sha256"], two["media"][0]["sha256"])
        self.assertEqual([m["pack_sha256"] for m in one["media"]], [inherited[1], inherited[1], delta.stem])

    def test_rejects_changed_source_records_even_with_a_valid_new_receipt(self):
        self.rows[0]["versions"][0]["text"] = "A different extraction."
        self.write_receipts()
        prior = packer.PriorMedia(self.base, self.release)
        with self.assertRaisesRegex(ValueError, "different or unverified media inputs"):
            packer.build(self.intake, self.output, {}, prior)

    def test_rejects_inconsistent_page_slot_in_a_pinned_prior_manifest(self):
        base = self.base / packer.PREFIX / "releases" / self.release
        batch = base / "sample/batches/0.json"
        rows = packer.read_json(batch)
        rows[0]["media"][0]["page"] = 2
        manifest = packer.read_json(base / "manifest.json")
        manifest["books"][0]["batches"][0] = packer.write_json(batch, rows)
        bad_release = packer.write_json(base / "manifest.json", manifest)
        base.rename(base.with_name(bad_release))
        packer.write_json(self.base / "viewer-object-manifest.json", {"release": bad_release})
        prior = packer.PriorMedia(self.base, bad_release)
        with self.assertRaisesRegex(ValueError, "Prior viewer media layout differs"):
            packer.build(self.intake, self.output, {}, prior)


if __name__ == "__main__":
    unittest.main()
