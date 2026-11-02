from pathlib import Path
import pymupdf as fitz
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2020-complete-solutions')
with fitz.open(B/'2020/source/IZhO_2020_TS.pdf')as doc:doc[0].get_pixmap(matrix=fitz.Matrix(2,2),clip=fitz.Rect(63,354,550,501),colorspace=fitz.csRGB,alpha=False).save(B/'2020/inspection/page01-source-figures-2x.png')
