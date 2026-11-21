# Private textbook viewer pack

Use Python 3.11 or later with PyMuPDF, Pillow and WebP support. Keep intake, overlays and output outside the source checkout. The intake provides `verified-sources.json` for PDF receipts and `verified-records.json` for the catalogue, per-book records and Savchenko diagram archive. The packer checks their recorded byte lengths and SHA-256 digests. Store each pack in a new directory.

```powershell
python tools/problem-bank/pack-private-textbook-viewer.py `
  --intake $Intake `
  --overlay $BilingualSnapshot `
  --output $NewPack
```

An overlay row supplies `id`, `source_sha256`, `text_ko`, optional `text_en` and `review_status`. A comparison uses `source_image_checked: true`. For Savchenko structured English and Russian comparison, set `review_basis` to `structured_english_russian` and `statement_sha256` to the digest of the archived English statement. A row can link additional original pages through `figures[].source_page` or `figure_spans[].page`. Editorial source comparisons take priority over model source comparisons and machine drafts. The viewer retains the review labels.

Use a prior pack and its pinned manifest digest to reuse verified raster media. The packer checks archived record digests, question order, page and crop slots, media offsets and pack hashes. It renders source pages that are missing from the prior media. Releases built before `media_inputs` was recorded require `--trust-legacy-media-inputs` and independent confirmation that their archived inputs match the current receipts.

```powershell
python tools/problem-bank/pack-private-textbook-viewer.py `
  --intake $Intake `
  --overlay $BilingualSnapshot `
  --output $NewPack `
  --reuse-media-from $PriorPack `
  --reuse-release $PriorManifestSha256
```

`viewer-object-manifest.json` is a local upload ledger. Its `objects` list names each R2 object key, byte length and SHA-256. Its optional `local_reused_media` map resolves specific content-addressed media keys to local backing files. Keep those files through upload and verification. Upload the listed objects and verify their bytes by reading them back. For a reused key already staged in the private bucket, verify the existing object against its digest. Local wrapper metadata stays local.

After private storage verification, the Worker uses `BANK_TEXTBOOK_RELEASE` to select the manifest digest and `BANK_TEXTBOOK_OWNER_IDS` for the explicit allowed account IDs. A server-confirmed admin session and a matching account ID are both required. The owner viewer is under `#/archive/books/phys?view=private-textbooks` in the HaslaLab frontend. Keep the R2 bucket private.
