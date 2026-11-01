"""IPhO 2017 Korean papers, answer sheets and working sheet: the top-left header stays in English.

    python3 -I tools/ko/ipho2017_header_fix.py SRC_DIR pdfx/ipho

The official translations keep «Theory» / «Experiment» in English at the top left (as IPhO 2025's do); these Korean
editions had it translated («이론» / «실험»).  The word is removed (redaction of its own box only) and the English one
is set where the English original has it — DejaVu Sans Bold 16 pt, baseline (51, 55) — nothing else changes.
"""
import os, sys
import pymupdf

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FILES = ["IPhO_2017_T1_KO.pdf", "IPhO_2017_T2_KO.pdf", "IPhO_2017_T3_KO.pdf",
         "IPhO_2017_T1_A_KO.pdf", "IPhO_2017_T2_A_KO.pdf", "IPhO_2017_T3_A_KO.pdf",
         "IPhO_2017_T_W_KO.pdf", "IPhO_2017_E1_KO.pdf", "IPhO_2017_E2_KO.pdf"]
WORDS = {"이론": "Theory", "실험": "Experiment"}


def fix(src, out):
    doc = pymupdf.open(src)
    changed = 0
    for page in doc:
        found = []
        for b in page.get_text("dict")["blocks"]:
            for line in b.get("lines", []):
                text = "".join(s["text"] for s in line["spans"]).strip()
                x0, y0, x1, y1 = line["bbox"]
                if text in WORDS and y0 < 60 and x0 < 60 and abs(line["spans"][0]["size"] - 16) < 0.5:
                    found.append((pymupdf.Rect(x0 - 1, y0 - 1, x1 + 1, y1 + 1), WORDS[text]))
        assert len(found) == 1, (src, page.number, found)
        rect, word = found[0]
        page.add_redact_annot(rect, fill=(1, 1, 1))
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
        page.insert_text((51.0, 55.0), word, fontsize=16, fontname="DejaVuSans-Bold", fontfile=FONT, color=(0, 0, 0))
        changed += 1
    doc.save(out, garbage=3, deflate=True)
    return changed


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    for name in FILES:
        print(name, fix(os.path.join(src, name), os.path.join(dst, name)), "pages")
