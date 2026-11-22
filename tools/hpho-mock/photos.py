"""Puts the openly licensed photos into the Korean papers, where the author's photos (licence unknown) were taken out,
with a credit line in the place and style of the author's source note (7.6 pt, grey, centred).

  python3 -I tools/hpho-mock/photos.py

T1 keeps the author's caption (copied from the original page); T2 and E2 get captions that describe the new photos,
set like the originals' captions (9 pt, "그림 2." in bold, centred, 11 pt lines)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pymupdf
from hpho_pdf import FONTS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / 'hpho/samples/mock-1/ko'
CSS = """@font-face{font-family:K;src:url(NotoSansCJKkr-Regular.otf)}
@font-face{font-family:K;src:url(NotoSansCJKkr-Bold.otf);font-weight:bold}
body{font-family:K;font-size:9pt;line-height:11pt;text-align:center;margin:0}"""

PHOTOS = {
    # id: (photo, photo box, caption: 'original' or (box, html), credit, credit baseline y)
    'T1': ('T1-2.jpg', (245.6, 442.4, 349.6, 581.0), 'original', 'Photo: S Sepp, Wikimedia Commons, CC BY-SA 3.0 (크기 조정)', 663.0),
    'T2': ('T2-2.jpg', (142.6, 384.0, 452.6, 558.0), ((59.1, 562.0, 536.2, 600.0),
           '<b>그림 2.</b> 실제 홀 추력기(SPT-140, 같은 원리의 더 큰 기종). 왼쪽: 점화 시험. 푸르게 빛나는 고리가 그림 1의 방전실 출구이다. '
           '오른쪽: 꺼진 상태. 흰 세라믹 고리 사이의 어두운 홈이 방전실이고, 자기 코일은 몸체 안에 들어 있다. 위쪽의 원통들이 중화기이다.'),
           'Photo: NASA/JPL-Caltech (public domain)', 612.0),
    'E2': ('E2-2.jpg', (168.6, 394.5, 426.6, 566.4), ((56.7, 591.0, 538.6, 640.0),
           '<b>그림 2.</b> 서로 수직인 두 편광판 사이에 놓은 투명 플라스틱 각도기. 아무 하중도 걸지 않았는데 등색선이 나타난다. '
           '사출 성형으로 굳는 과정에서 남은 잔류 응력 때문이다. A.2에서 무하중 무늬를 N₀로 기록해 두라는 이유가 이것이다. '
           '모서리와 눈금 근처의 촘촘한 무늬는 모양이 급히 바뀌는 곳에 응력이 몰린 결과이다.'),
           'Photo: Nevit Dilmen, Wikimedia Commons, CC BY-SA 3.0 (크기 조정)', 659.5),
}


def main():
    arch = pymupdf.Archive(str(FONTS))
    reg = pymupdf.Font(fontfile=str(FONTS / 'NotoSansCJKkr-Regular.otf'))
    for pid, (photo, box, caption, credit, y) in PHOTOS.items():
        path = OUT / f'{pid}-question.pdf'
        doc = pymupdf.open(str(path))
        page = doc[1]
        page.insert_image(pymupdf.Rect(box), filename=str(HERE / 'mock-1/fig' / photo), keep_proportion=True)
        if caption == 'original':
            src = pymupdf.open(str(HERE / f'original/{pid}.pdf'))
            clip = pymupdf.Rect(56.0, 604.0, 540.0, 631.0)
            page.show_pdf_page(clip, src, 1, clip=clip)
        else:
            rect, html = caption
            spare, _ = page.insert_htmlbox(pymupdf.Rect(rect), html, css=CSS, archive=arch)
            if spare < 0:
                sys.exit(f'{pid}: caption does not fit')
        w = reg.text_length(credit, fontsize=7.6)
        page.insert_text((297.6 - w / 2, y), credit, fontsize=7.6, fontname='credit', fontfile=str(FONTS / 'NotoSansCJKkr-Regular.otf'),
                         color=(0x55 / 255,) * 3)
        doc.save(str(path) + '.tmp', garbage=3, deflate=True)
        doc.close()
        Path(str(path) + '.tmp').replace(path)
        print(path.relative_to(ROOT))


if __name__ == '__main__':
    main()
