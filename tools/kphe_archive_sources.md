# KPHE archive source audit

Checked 2026-10-30 (Asia/Seoul).

## Current Physics League

The public KPS archive has six sittings, from 2024-1 through 2026-2. Each sitting
has four original problem PDFs and four answer-key PDFs. These are answer keys,
not worked solutions or blank answer sheets.

| Sitting | Official archive page | Questions: beginner / intermediate / advanced / expert |
| --- | --- | --- |
| 2026-2 | https://kphe.kps.or.kr/board/board_detail/43 | 25 / 18 / 18 / 12 |
| 2026-1 | https://kphe.kps.or.kr/board/board_detail/12 | 25 / 18 / 18 / 12 |
| 2025-2 | https://kphe.kps.or.kr/board/board_detail/11 | 25 / 18 / 18 / 18 |
| 2025-1 | https://kphe.kps.or.kr/board/board_detail/10 | 25 / 18 / 18 / 18 |
| 2024-2 | https://kphe.kps.or.kr/board/board_detail/9 | 25 / 18 / 18 / 18 |
| 2024-1 | https://kphe.kps.or.kr/board/board_detail/8 | 25 / 18 / 18 / 18 |

The previous manifest contained advanced and expert only. It also labelled answer
keys as `solution`, exposing them as worked solutions. The refreshed manifest
uses `key` and the filename suffix `K.pdf`; the generated archive uses the
corresponding `key` slot. Blank answer sheets retain `answer` and worked solutions
retain `solution`.

The key parser uses the printed question number, so two-column PDF extraction
order does not reorder answers. For an explicit correction such as `③ → ②`, the
last choice is used. Parsed keys are contiguous and contain values 1–5. The 12
previously stored advanced/expert keys match the newly downloaded sources exactly.

`kphe_archive_downloads.json` records all 48 source URLs, original attachment names,
byte lengths and SHA-256 hashes. `kphe_archive_import.py` downloads and extracts
these sources to `tmp/kphe_archive/originals` and writes a candidate manifest at
`tmp/kphe_archive/manifest.pending.json`; it does not overwrite the live manifest.

## Korean Middle-School Physics Competition

https://olimpicos.net/kphc/ preserves ten original Korean papers covering 2015
through 2022. These ten PDFs were downloaded, opened as PDFs, and their cover
titles checked. The source archive identifies KPS and phoXiv as its collection
sources. The original KPS download locations are not supplied there.

The two files previously labelled simply 2015 are explicitly **2015년 제2차** on
their covers, with separate first and second periods. Their manifest titles now
state the sitting. These historical papers are not relabelled as the current four
levels, because those are different exam systems.

Official answer keys or worked solutions were not found for these preserved
papers. No fabricated answer keys were added. Public originals for 2011–2014 and
the first 2015 sitting were not found in the checked sources. The manifest
records this limitation.

## Former physics certification examination

The KPS notice confirms a final special expert examination on 2023-07-22:
https://kphe.kps.or.kr/notice/notice_detail/32

The official former website `http://kphc.kps.or.kr/` and its HTTPS equivalent
timed out during this audit. The current public archive contains 2024 onwards,
not former certification PDFs. No verifiable official certification question PDF
was obtained.

An unofficial 2019-1 university-level reconstruction is publicly linked at
https://orbi.kr/00023718349 . Its author explicitly says in a comment that it was
reconstructed from memory and that numbers may be inaccurate. It is therefore
not entered as an official past paper. Another third-party HWP collection at
https://www.iteach4u.kr/2014/exammaterials/?no=6939 is not a verified official
original and has not been added.

## Provenance and publication wording

The KPS public pages carry KPS copyright notices. A separate open redistribution
licence or permission statement was not found in the checked archive pages.
Public access is recorded as source availability, not as an assertion of an open
licence. Generated practice formatting should credit KPS, preserve source links,
and be identified as HaslaLab formatting rather than an official KPS publication.


## Historical recollections added at the user’s request

- 2019 first sitting, university level (grades 1/2): Orbi author 물리개꿀잼, 22-page personal recollection. The author explicitly warns that numerical values may be inaccurate. Published separately as unofficial; duplicate original number 3 is preserved. https://orbi.kr/00023718349
- 2021 grade 1, sitting unknown: one hydrogen probability question attributed in 雀(Suzume)’s 정적분 100題 ver.20220629. Only that question is republished as an attributed fragment, with a separately derived solution. The source book’s number 16 is not an original exam number. https://orbi.kr/00057373007 ; Scribd mirror: https://www.scribd.com/document/1005314514/정적분-100題
- tools/kphe_legacy_found.json records further searches and unavailable or incomplete sources. Neither recollection has an official grading key.
