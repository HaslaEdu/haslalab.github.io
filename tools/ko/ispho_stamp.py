"""The ISPhO header on every page of a paper rendered with tools/ko/ispho_template.html — as the competition's own
Korean papers have it: «이론» (or «실험»), the ISPhO logo, the page code «Q1-2» (problem 1, page 2) and the language «Korean (Korea (Republic of))», set as the official
English paper sets «English (Official)» (Noto Sans 10 pt, right-aligned, over a 2 pt rule).

    python3 tools/ko/ispho_stamp.py <in.pdf> <out.pdf> <problem number> [이론|실험]
"""
import os, sys
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(HERE, "fonts", n)
LABEL = "Korean (Korea (Republic of))"      # as IPhO and APhO label their Korean papers

def stamp(src, dst, q, kind="이론"):
    doc = pymupdf.open(src)
    for k, page in enumerate(doc, 1):
        page.insert_font(fontname="kr", fontfile=F("NotoSansKR-Regular.ttf"))
        page.insert_font(fontname="nb", fontfile=F("NotoSans-Bold.ttf"))
        page.insert_text((57, 104), kind, fontname="kr", fontsize=13.5)
        page.insert_image(pymupdf.Rect(56.7, 110.5, 226.8, 143.0), filename=os.path.join(HERE, "ispho_logo.png"))
        code = f"Q{q}-{k}"
        w = pymupdf.Font(fontfile=F("NotoSans-Bold.ttf")).text_length(code, fontsize=56.7)
        page.insert_text((538.6 - w, 124), code, fontname="nb", fontsize=56.7)
        page.insert_font(fontname="nr", fontfile=F("NotoSans-Regular.ttf"))
        w2 = pymupdf.Font(fontfile=F("NotoSans-Regular.ttf")).text_length(LABEL, fontsize=10)
        page.insert_text((536 - w2, 143.0), LABEL, fontname="nr", fontsize=10)
        page.draw_line((56.7, 147.5), (538.6, 147.5), color=(0, 0, 0), width=1.9925)
    doc.save(dst, garbage=3, deflate=True)

if __name__ == "__main__":
    stamp(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "이론")
