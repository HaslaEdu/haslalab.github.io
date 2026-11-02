"""ISPhO Korean papers: the top-left «이론» / «실험» back to «Theory» / «Experiment», as the official translations of
IPhO and ISPhO keep it (the papers were stamped by tools/ko/ispho_stamp.py, which now writes the English word).

    python3 -I tools/ko/ispho_theory_header.py pdfx/ispho/ISPhO_2023_T1_KO.pdf …

On every page the word (a span «이론» or «실험» above y = 130 and left of x = 80, over 12 pt) is redacted, its box only,
and the English word set at its own origin and size in Noto Sans Bold; nothing else changes.  Files without the
word are left as they are.
"""
import os, sys
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
BOLD = os.path.join(HERE, "fonts", "NotoSans-Bold.ttf")
WORDS = {"이론": "Theory", "실험": "Experiment"}


def fix(path):
    doc, n = pymupdf.open(path), 0
    for page in doc:
        found = [s for b in page.get_text("dict")["blocks"] for line in b.get("lines", []) for s in line["spans"]
                 if s["text"].strip() in WORDS and s["bbox"][1] < 130 and s["bbox"][0] < 80 and s["size"] > 12]
        for s in found:
            page.add_redact_annot(pymupdf.Rect(s["bbox"]), fill=(1, 1, 1))
        if not found:
            continue
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
        for s in found:
            page.insert_text(s["origin"], WORDS[s["text"].strip()], fontsize=s["size"], fontname="nsb", fontfile=BOLD)
            n += 1
    if n:
        doc.subset_fonts()
        doc.save(path + ".tmp", garbage=3, deflate=True)
        doc.close()
        os.replace(path + ".tmp", path)
    return n


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p, fix(p), "headers")
